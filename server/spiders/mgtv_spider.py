"""
芒果TV爬虫
使用 pianku.api.mgtv.com 获取频道列表，pcweb.api.mgtv.com 获取分集详情
"""
import re
import requests
from typing import Dict, List, Optional

from core.base_spider import BaseSpider
from core.retry import RetryHelper
from core.logger import setup_logger

logger = setup_logger('vbox.mgtv')

# 频道 key → API channelId 映射
CHANNEL_ID_MAP = {
    'tv': 2,
    'movie': 3,
    'variety': 1,
    'cartoon': 50,
    'child': 10,
}

# 平台 UA
PLATFORM_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)

HEADERS = {
    'User-Agent': PLATFORM_UA,
    'Referer': 'https://www.mgtv.com/',
    'Origin': 'https://www.mgtv.com',
    'Accept': 'application/json, text/plain, */*',
}

# 列表 API
LIST_API = 'https://pianku.api.mgtv.com/rider/list/pcweb/v3'

# 剧集分集 API（pcweb domain）
EPISODE_API = 'https://pcweb.api.mgtv.com/list/master'

# 每页数量
PAGE_SIZE = 30

# 分集 API 每页上限（实测 ps=200 也只返回100条）
PS_PER_PAGE = 100


class MgtvSpider(BaseSpider):
    """芒果TV爬虫类"""

    def __init__(self, channel_config):
        super().__init__('芒果TV', channel_config)
        self.category_key = channel_config.get('category_key') or channel_config.get('channel_key') or 'tv'
        self.channel_id = CHANNEL_ID_MAP.get(self.category_key)
        if self.channel_id is None:
            logger.warning(f'未知频道 "{self.category_key}"，回退为电视剧')
            self.channel_id = 2
            self.category_key = 'tv'
        self.session = self.create_session()
        # 反爬：动态构建完整请求头
        from core.anti_crawl import build_headers
        self.session.headers.update(build_headers(
            referer='https://www.mgtv.com/',
            origin='https://www.mgtv.com',
            accept='application/json, text/plain, */*',
            ua=self.get_user_agent(),
            extra={'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'},
        ))
        self.max_workers = 5
        self.skip_existing = True

    # ---------- 工具方法 ----------

    def _request_with_retry(self, url: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
        """带重试的 JSON API 请求"""
        def _do():
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            # 检查响应是否为 JSON（芒果TV 反爬可能返回 HTML）
            content_type = resp.headers.get('Content-Type', '')
            if 'json' not in content_type and 'javascript' not in content_type:
                text_preview = resp.text[:200]
                logger.warning(f'芒果TV返回非JSON响应: Content-Type={content_type}, 内容={text_preview}')
                raise ValueError(f'API返回非JSON: {content_type}')
            return resp.json()

        return RetryHelper.with_retry(_do, max_retries=3, base_delay=2, max_delay=10)

    @staticmethod
    def _extract_total_from_update_info(update_info: str) -> int:
        """从 updateInfo 提取总集数
        "全40集" → 40, "更新至15集" → 15, "更新至277集" → 277
        "2026-06-03日"（日期格式，综艺场景）→ 0
        """
        if not update_info:
            return 0
        info = update_info.strip()
        # 日期格式（如 "2026-06-03"、"2026-06-03日"）→ 非集数信息
        if re.match(r'^\d{4}-\d{2}-\d{2}', info):
            return 0
        m = re.search(r'(\d+)', update_info)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _parse_tags(kind_list: List[str]) -> List[str]:
        """解析 kind 数组为标签列表"""
        if not kind_list:
            return []
        return [k for k in kind_list if k and not k.isdigit()]

    # ---------- 列表页 ----------

    def fetch_list_page(self, page: int = 1, **kwargs) -> Optional[dict]:
        """获取频道列表页"""
        params = {
            'allowedRC': '1',
            'platform': 'pcweb',
            'channelId': self.channel_id,
            'pn': page,
            'pc': PAGE_SIZE,
            'hudong': '1',
            '_support': '10000000',
            'kind': 'a1',
            'edition': 'a1',
            'area': 'a1',
            'year': 'all',
            'chargeInfo': 'a1',
            'sort': 'c2',
        }
        try:
            return self._request_with_retry(LIST_API, params=params)
        except Exception as e:
            logger.error(f'列表页请求失败 (page={page}): {e}')
            return None

    def extract_items(self, data: dict) -> List[dict]:
        """从 API 响应中提取剧集列表"""
        if not data:
            return []

        hit_docs = data.get('data', {}).get('hitDocs', [])
        items = []

        for doc in hit_docs:
            clip_id = str(doc.get('clipId', '')).strip()
            if not clip_id:
                continue

            title = doc.get('title', '')
            if not title:
                continue

            update_info = doc.get('updateInfo', '')

            # VIP 判断
            right_corner = doc.get('rightCorner', {})
            is_vip = 1 if (isinstance(right_corner, dict) and
                           right_corner.get('text', '') == 'VIP') else 0

            item = {
                'cid': clip_id,
                'title': title,
                'url': f'https://www.mgtv.com/b/{clip_id}/',
                'thumbnail': doc.get('img', ''),
                'cover_url': doc.get('imgUrlH', '') or doc.get('img', ''),
                'description': doc.get('story', ''),
                'actors': doc.get('subtitle', ''),
                'year': str(doc.get('year', '')),
                'tags': self._parse_tags(doc.get('kind', [])),
                'score': float(doc.get('zhihuScore', 0) or 0),
                'is_vip': is_vip,
                'update_info': update_info,
                'total_episodes': self._extract_total_from_update_info(update_info),
            }
            items.append(item)

        return items

    def _get_total_pages(self, first_page_data: dict, max_items: int,
                         first_page_count: int) -> int:
        """计算总页数"""
        total_hits = first_page_data.get('data', {}).get('totalHits', 0)
        if not total_hits:
            return 1

        if max_items is not None:
            needed = min(max_items, total_hits)
            return max(1, (needed + PAGE_SIZE - 1) // PAGE_SIZE)

        return max(1, (total_hits + PAGE_SIZE - 1) // PAGE_SIZE)

    # ---------- 详情与分集 ----------

    @staticmethod
    def _extract_episode_num(title: str, category_key: str = '') -> int:
        """从分集标题提取集号
        "第1集" → 1, "第03期" → 3, "2026-03-28"（综艺日期格式）→ 0
        """
        if not title:
            return 0
        title = title.strip()
        # 日期格式（如 "2026-03-28"、"2026-03-28日"、"2026-06-03周二"）
        if re.match(r'^\d{4}-\d{2}-\d{2}', title):
            return 0
        # "第N集/期/话"
        m = re.search(r'^第\s*(\d+)\s*[集期话]', title)
        if m:
            return int(m.group(1))
        return 0

    def _fetch_episodes_for_cid(self, cid: str) -> tuple:
        """
        获取某剧集的全部分集列表（支持翻页）
        :return: (episodes_list, total_count)
        """
        all_episodes = []
        total = 0
        base_params = {
            'src': 'mgtv',  # intelmgtv 对部分剧集(如玉茗茶骨)返回空列表，mgtv 更稳定
            'abroad': '10',
            '_support': '10000000',
            'filterpre': 'true',
            'platform': '4',
            'ps': str(PS_PER_PAGE),
            'cid': cid,
        }

        # 先获取第1页
        params = {**base_params, 'pn': '1'}
        try:
            data = self._request_with_retry(EPISODE_API, params=params)
        except Exception as e:
            logger.warning(f'获取分集失败 (cid={cid}): {e}')
            return [], 0

        if not data or data.get('code') != 200:
            return [], 0

        dd = data.get('data', {})
        ep_list = dd.get('list', [])
        total = int(dd.get('total', 0))
        all_episodes.extend(ep_list)

        # 翻页：API 每页最多返回 PS_PER_PAGE 条
        if total > PS_PER_PAGE:
            total_pages = (total + PS_PER_PAGE - 1) // PS_PER_PAGE
            for page in range(2, total_pages + 1):
                params = {**base_params, 'pn': str(page)}
                try:
                    data = self._request_with_retry(EPISODE_API, params=params)
                    if data and data.get('code') == 200:
                        page_list = data.get('data', {}).get('list', [])
                        all_episodes.extend(page_list)
                except Exception as e:
                    logger.warning(f'获取分集第{page}页失败 (cid={cid}): {e}')

        # 解析分集数据，正确映射字段到 DB 格式
        episodes = []
        for ep in all_episodes:
            content_type = int(ep.get('contentType', 0) or 0)
            title = ep.get('t2', '') or ep.get('t1', '')

            # 类型映射：0=正片, 2=花絮, 其他=预告
            if content_type == 0:
                ep_type = 0
            elif content_type == 2:
                ep_type = 2
            else:
                ep_type = 1

            # 集号
            ep_num = self._extract_episode_num(title, self.category_key)

            # episode_num 统一为纯数字，类型由 episode_type 字段区分
            # 预告/花絮与正片 episode_num 重复时，去重逻辑按 (episode_num, episode_type) 处理

            episodes.append({
                'vid': str(ep.get('video_id', '')),           # DB: vid
                'episode_num': ep_num,                         # DB: episode_num
                'play_title': title,                           # DB: play_title
                'union_title': '',                            # DB: union_title
                'episode_type': ep_type,                       # DB: episode_type
                'is_vip': 1 if str(ep.get('isvip', '0')) == '1' else 0,
                'duration': ep.get('time', ''),
                'publish_date': ep.get('date', '') or '',     # DB: publish_date
                'play_url': f'https://www.mgtv.com{ep.get("url", "")}',  # DB: play_url
            })

        # 按 episode_num + episode_type 去重（同集号只保留第一条）
        seen = set()
        deduped = []
        for ep in episodes:
            key = (ep['episode_num'], ep['episode_type'])
            if key not in seen:
                seen.add(key)
                deduped.append(ep)

        return deduped, total

    def fetch_detail(self, item: dict) -> None:
        """获取剧集详情和分集"""
        cid = item.get('cid', '')
        if not cid:
            return

        # 获取分集列表
        episodes, ep_total = self._fetch_episodes_for_cid(cid)

        main_eps = [e for e in episodes if e.get('episode_type') == 0]
        trailer_eps = [e for e in episodes if e.get('episode_type') == 1]
        bts_eps = [e for e in episodes if e.get('episode_type') == 2]

        # 如果没有 total_episodes，用实际正片数
        if not item.get('total_episodes'):
            total_from_update = self._extract_total_from_update_info(item.get('update_info', ''))
            item['total_episodes'] = max(len(main_eps), total_from_update)
        else:
            # updateInfo 可能比实际正片数更准确（如 "全40集"）
            total_from_update = self._extract_total_from_update_info(item.get('update_info', ''))
            if total_from_update > 0 and total_from_update > item['total_episodes']:
                item['total_episodes'] = total_from_update

        # 更新集数
        item['updated_episodes'] = len(main_eps) if main_eps else item.get('total_episodes', 0)

        # 第一个视频 ID（优先正片，其次预告/花絮，确保总有 first_vid）
        if main_eps:
            item['first_vid'] = main_eps[0].get('vid', '')
            item['vid'] = main_eps[0].get('vid', '')
        elif episodes:
            # 无正片时从所有分集中取第一个
            item['first_vid'] = episodes[0].get('vid', '')
            item['vid'] = episodes[0].get('vid', '')
        # 如果 first_vid 仍为空，尝试从列表页的 vid 字段补充
        if not item.get('first_vid') and item.get('vid'):
            item['first_vid'] = item['vid']

        # 完结状态判断
        from core.finished_judge import judge
        item['is_finished'] = judge(
            text=item.get('update_info', ''),
            total_episodes=item.get('total_episodes', 0),
            main_count=len(main_eps),
            trailer_count=len(trailer_eps),
            category_key=self.category_key,
        )

        item['episodes'] = episodes

        logger.debug(f'  ✓ {item.get("title","?")}: {len(main_eps)}正片+{len(trailer_eps)}预告+{len(bts_eps)}花絮, '
                     f'is_vip={item.get("is_vip",0)}, finished={item.get("is_finished",0)}')
