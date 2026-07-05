
from abc import ABC, abstractmethod
import time
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import Config
from core.anti_crawl import build_headers, random_delay, ProxySession, rate_limited


class BaseSpider(ABC):
    def __init__(self, platform_name, channel_config):
        self.platform_name = platform_name
        self.channel_config = channel_config
        self.max_workers = 5  # 并发线程数
        self.skip_existing = True  # 增量爬取：跳过已存在的剧集

        # 从数据库加载平台配置
        self.config = Config()
        self.platform_config = self.config.get_platform(platform_name)

    def get_user_agent(self):
        """从配置获取 User-Agent，返回随机 UA 如果没有配置"""
        configured_ua = self.platform_config.get('user_agent')
        if configured_ua:
            return configured_ua
        # 使用 UA 池随机选择
        from core.anti_crawl import get_random_ua
        return get_random_ua()

    def create_session(self):
        """创建带代理轮换的 requests Session，所有子类应使用此方法"""
        return ProxySession()
    
    def get_keywords(self, keyword_type):
        """获取指定类型的关键词列表（通过 spiders.keywords.load_keywords 统一加载）"""
        from spiders.keywords import load_keywords
        platform_key = self.platform_config.get('key', 'all')
        return load_keywords(platform_key, keyword_type)

    @abstractmethod
    def fetch_list_page(self, page=1, **kwargs):
        pass

    @abstractmethod
    def extract_items(self, data):
        pass

    @abstractmethod
    def fetch_detail(self, item):
        pass

    def _get_item_id(self, item):
        return item.get('cid', '') or item.get('vid', '') or item.get('id', '')

    def _get_item_title(self, item):
        return item.get('title', '未知')

    def _check_existing_cids(self, cid_list):
        """批量检查cid是否已存在于数据库，返回已存在的cid集合"""
        if not cid_list or not self.skip_existing:
            return set()
        try:
            from core.database import db
            from models import CATEGORY_KEYS, get_video_model, get_session
            existing = set()
            with get_session() as session:
                for cat_key in CATEGORY_KEYS:
                    SeriesModel = get_video_model(cat_key)
                    rows = session.query(SeriesModel.cid).filter(
                        SeriesModel.cid.in_(cid_list)
                    ).all()
                    existing.update(row[0] for row in rows)
            return existing
        except Exception as e:
            print(f'检查已存在数据失败: {e}')
            return set()

    def _fetch_list_page_safe(self, page):
        """线程安全的列表页获取，带令牌桶限流"""
        try:
            rate_limited(self.platform_name, qps=3.0)
            data = self.fetch_list_page(page)
            return page, data
        except Exception as e:
            print(f'第 {page} 页获取异常: {e}')
            return page, None

    def crawl(self, max_items=10):
        print(f'[{self.platform_name}] 开始爬取...\n')

        all_items = []
        seen_ids = set()

        # 第一阶段：获取列表（并发）
        # 先获取第1页，确定总页数
        print('正在获取第 1 页...')
        first_data = self.fetch_list_page(1)
        if not first_data:
            print('第 1 页请求失败，停止爬取')
            return all_items

        first_items = self.extract_items(first_data)
        for item in first_items:
            item_id = self._get_item_id(item)
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                all_items.append(item)

        print(f'第1页获取 {len(first_items)} 条，总计 {len(all_items)} 条')

        # 计算需要获取的总页数
        total_pages = self._get_total_pages(first_data, max_items, len(first_items))

        if total_pages > 1 and (max_items is None or len(all_items) < max_items):
            # 并发获取剩余页
            remaining_pages = list(range(2, total_pages + 1))
            print(f'并发获取第 2~{total_pages} 页（并发数={self.max_workers}）')

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_page = {
                    executor.submit(self._fetch_list_page_safe, page): page
                    for page in remaining_pages
                }
                page_results = {}
                for future in as_completed(future_to_page):
                    page_num, data = future.result()
                    if data:
                        page_results[page_num] = self.extract_items(data)

            # 按页码顺序合并结果
            for page_num in sorted(page_results.keys()):
                items = page_results[page_num]
                new_count = 0
                for item in items:
                    item_id = self._get_item_id(item)
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        all_items.append(item)
                        new_count += 1
                        if (max_items is not None) and (len(all_items) >= max_items):
                            break
                print(f'第{page_num}页获取 {len(items)} 条，新增 {new_count} 条，总计 {len(all_items)} 条')
                if (max_items is not None) and (len(all_items) >= max_items):
                    break

        # 截断到max_items
        if max_items is not None and len(all_items) > max_items:
            all_items = all_items[:max_items]

        print(f'列表获取完成，共 {len(all_items)} 条')

        # 第二阶段：增量过滤（跳过已存在的剧集）
        if self.skip_existing and all_items:
            cid_list = [self._get_item_id(item) for item in all_items if self._get_item_id(item)]
            existing_cids = self._check_existing_cids(cid_list)
            if existing_cids:
                before = len(all_items)
                all_items = [item for item in all_items if self._get_item_id(item) not in existing_cids]
                skipped = before - len(all_items)
                print(f'增量爬取：跳过 {skipped} 条已存在数据，剩余 {len(all_items)} 条待获取详情')

        if not all_items:
            print('所有数据均已存在，无需获取详情')
            return all_items

        # 第三阶段：并发获取详情
        print(f'\n开始获取详情，共 {len(all_items)} 条（并发数={self.max_workers}）\n')

        completed = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self._fetch_detail_safe, item): item
                for item in all_items
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    future.result()
                except Exception as e:
                    print(f'获取详情失败: {self._get_item_title(item)}, 错误: {e}')
                completed += 1
                if completed % 5 == 0 or completed == len(all_items):
                    print(f'详情进度: {completed}/{len(all_items)}')

        print(f'\n完成！共 {len(all_items)} 条数据')
        return all_items

    def _get_total_pages(self, first_page_data, max_items, first_page_count):
        """根据第一页数据计算需要获取的总页数
        子类可重写此方法以支持API返回的总数
        """
        # 默认实现：如果指定了max_items，按每页条数计算
        if max_items is not None and first_page_count > 0:
            return (max_items + first_page_count - 1) // first_page_count
        # 未指定max_items时，默认只取1页（子类可重写）
        return 1

    def _fetch_detail_safe(self, item):
        """线程安全的详情获取，带令牌桶限流"""
        try:
            rate_limited(self.platform_name, qps=3.0)
            self.fetch_detail(item)
        except Exception as e:
            print(f'详情获取异常: {self._get_item_title(item)}, 错误: {e}')
            raise

