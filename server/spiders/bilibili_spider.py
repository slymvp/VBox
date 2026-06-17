"""
哔哩哔哩爬虫
API端点：
- 列表: api.bilibili.com/pgc/season/index/result
- 详情(含分集): api.bilibili.com/pgc/view/web/season?season_id=xxx

频道映射 (season_type):
  1=番剧(cartoon)  2=电影(movie)  4=国创(child)
  5=电视剧(tv)     7=综艺(variety)

VIP判断: 分集 badge="会员" → VIP
完结判断: 列表 is_finish 字段 + index_show 关键词
"""
import requests
import json
import re
import time
from core.base_spider import BaseSpider
from core.logger import setup_logger
from core.retry import RetryHelper

logger = setup_logger('vbox.bilibili')

# category_key -> API season_type 映射
SEASON_TYPE_MAP = {
    'tv': 5,       # 电视剧
    'movie': 2,    # 电影
    'variety': 7,  # 综艺
    'cartoon': 1,  # 番剧
    'child': 4,    # 国创（少儿频道用国创替代）
}

ORDER_MAP = {
    'hot': 3,   # 最多播放
    'new': 2,   # 最新发布
}

LIST_API = 'https://api.bilibili.com/pgc/season/index/result'
DETAIL_API = 'https://api.bilibili.com/pgc/view/web/season'
PAGE_SIZE = 30

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Origin': 'https://www.bilibili.com',
}


class BilibiliSpider(BaseSpider):
    """哔哩哔哩爬虫"""

    def __init__(self, channel_config):
        super().__init__('哔哩哔哩', channel_config)
        self.category_key = channel_config.get('channel_key', 'tv')
        self.season_type = SEASON_TYPE_MAP.get(self.category_key)

        if self.season_type is None:
            self.season_type = 5
            self.category_key = 'tv'
            logger.warning(f"未知频道类型，回退到 tv: season_type=5")

        # sort: 'hot' = 热门列表, 'new' = 最新列表, ''/None = 默认（不刷标记）
        sort_val = str(channel_config.get('sort', '') or '')
        self._order = ORDER_MAP.get(sort_val, 3)
        self._list_type = sort_val

        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = channel_config.get('timeout', 20)

    # === 请求工具 ===

    def _request_with_retry(self, url, params=None, timeout=None):
        """GET 请求 + 重试"""
        timeout = timeout or self.timeout

        def _do():
            resp = self.session.get(url, params=params, timeout=timeout)
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError(f"API返回类型异常: {type(data)}")
            code = data.get('code', -1)
            if code != 0:
                raise ValueError(f"API返回错误码: {code}, message={data.get('message', '')}")
            return data

        return RetryHelper.with_retry(
            _do, max_retries=3, base_delay=1, max_delay=8,
            exceptions=(requests.RequestException, ValueError)
        )

    # === 列表页 ===

    def fetch_list_page(self, page=1, **kwargs):
        """获取频道列表页"""
        params = {
            'season_version': -1,
            'spoken_language_type': -1,
            'area': -1,
            'is_finish': -1,
            'copyright': -1,
            'season_status': -1,
            'season_month': -1,
            'year': -1,
            'style_id': -1,
            'order': self._order,
            'sort': 0,
            'page': page,
            'season_type': self.season_type,
            'pagesize': PAGE_SIZE,
            'type': 1,
        }

        try:
            return self._request_with_retry(LIST_API, params=params)
        except Exception as e:
            logger.error(f"列表页请求失败(page={page}): {e}")
            return None

    def _get_total_pages(self, first_page_data, max_items, first_page_count):
        """用 API 返回的 total 计算总页数"""
        total = first_page_data.get('data', {}).get('total', 0)
        if total > 0:
            pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
            return min(pages, 50)  # B站最多约50页
        return 50

    def extract_items(self, data):
        """从列表页提取标准化 item"""
        items = []
        season_list = data.get('data', {}).get('list', [])

        for doc in season_list:
            season_id = doc.get('season_id')
            title = doc.get('title', '')

            if not season_id or not title:
                continue

            # 封面
            cover = doc.get('cover', '')
            thumbnail = cover

            # 简介：用 subTitle 作为副标题/简介
            sub_title = doc.get('subTitle', '')

            # 评分
            score = str(doc.get('score', '') or '')

            # 标签：从 styles 提取
            styles = doc.get('styles', [])
            tags = [s.get('name', s) if isinstance(s, dict) else str(s)
                    for s in (styles if isinstance(styles, list) else [])]

            # 地区
            areas = doc.get('areas', [])
            area = ''
            if isinstance(areas, list) and areas:
                area = areas[0].get('name', areas[0]) if isinstance(areas[0], dict) else str(areas[0])

            # 年份：从 index_show 或 publish 尝试提取
            year = ''
            pub_info = doc.get('publish', {}) or {}
            if pub_info.get('release_date'):
                year = str(pub_info['release_date'])[:4]

            # 播放链接
            link = doc.get('link', '') or f'https://www.bilibili.com/bangumi/play/ss{season_id}'

            # first_ep: 列表页返回的首集信息（详情页episodes为空时的回退）
            first_ep_info = doc.get('first_ep', {}) or {}
            first_ep_id = str(first_ep_info.get('ep_id', '') or '') if isinstance(first_ep_info, dict) else ''

            # 订阅数
            order_text = doc.get('order', '')  # e.g. "383万追剧"

            # VIP: badge="大会员"
            badge = doc.get('badge', '') or ''
            is_vip = 1 if badge == '大会员' else 0

            # 完结状态: is_finish 字段
            is_finish = doc.get('is_finish', 0)

            # index_show: e.g. "全10集", "2021年4月9日上映"
            index_show = doc.get('index_show', '')

            # 热度标记
            is_hot = 1 if self._list_type == 'hot' else 0
            is_new = 1 if self._list_type == 'new' else 0

            item = {
                'cid': str(season_id),
                'title': title,
                'first_vid': first_ep_id,
                'area': area,
                'year': year,
                'score': score,
                'tags': tags,
                'actors': json.dumps([], ensure_ascii=False),
                'thumbnail': thumbnail,
                'cover_url': cover,
                'play_url': link,
                'platform': 'bilibili',
                'category_key': self.category_key,
                'is_vip': is_vip,
                'is_finished': is_finish,
                'is_hot': is_hot,
                'is_new': is_new,
                # 保留原始字段供详情页使用
                '_season_id': season_id,
                '_badge': badge,
                '_index_show': index_show,
                '_order_text': order_text,
                '_sub_title': sub_title,
            }
            items.append(item)

        return items

    # === 详情页 ===

    def _fetch_detail_data(self, season_id):
        """获取剧集详情（含分集）"""
        resp = self._request_with_retry(DETAIL_API, params={'season_id': season_id})
        return resp.get('result', {})

    def _extract_actors(self, detail):
        """从 actor.info 提取演员/声优信息"""
        actors = []

        # B站 API：actor 字段仅在番剧(声优)时有值，电视剧/电影通常为 null
        actor_info = (detail.get('actor', {}) or {}).get('info', '') or ''

        if actor_info:
            # 格式: "声优：xxx、xxx" 或 "演员：xxx、xxx"
            for part in actor_info.split('\n'):
                if '：' in part:
                    _, names = part.split('：', 1)
                    for name in names.split('、'):
                        name = name.strip()
                        if name:
                            actors.append(name)

        # B站 staff 字段只含导演/编剧等幕后人员，不含演员，故不作为演员来源
        return actors

    def _extract_directors(self, detail):
        """从 staff 提取导演"""
        staff = detail.get('staff', '') or ''
        directors = []

        if staff:
            lines = staff.replace('\n', ';').split(';')
            for line in lines:
                line = line.strip()
                if '：' in line:
                    role, name = line.split('：', 1)
                    if '导演' in role.strip():
                        name = name.strip().split('（')[0].strip()
                        if name:
                            directors.append(name)

        return directors

    def fetch_detail(self, item):
        """获取剧集详情和分集"""
        try:
            season_id = item.get('_season_id') or item.get('cid')
            if not season_id:
                logger.warning(f"缺少 season_id: {item.get('title')}")
                return

            logger.info(f"获取详情: {item.get('title')} - season_id: {season_id}")

            detail = self._fetch_detail_data(season_id)
            if not detail:
                logger.warning(f"详情为空: {item.get('title')}")
                return

            # 基本信息补充
            if not item.get('description'):
                item['description'] = detail.get('evaluate', '') or ''

            if not item.get('year'):
                pub_info = detail.get('publish', {}) or {}
                pub_year = pub_info.get('release_date', '')
                if pub_year:
                    item['year'] = str(pub_year)[:4]

            if not item.get('area'):
                areas = detail.get('areas', [])
                if isinstance(areas, list) and areas:
                    item['area'] = areas[0].get('name', areas[0]) if isinstance(areas[0], dict) else str(areas[0])

            # 评分
            rating = detail.get('rating', {}) or {}
            if rating.get('score') and not item.get('score'):
                item['score'] = str(rating['score'])

            # 演员
            if not item.get('actors') or item.get('actors') == '[]':
                actors = self._extract_actors(detail)
                if actors:
                    item['actors'] = json.dumps(actors, ensure_ascii=False)

            # 导演
            directors = self._extract_directors(detail)
            if directors and not item.get('director'):
                item['director'] = json.dumps(directors, ensure_ascii=False)

            # 封面
            if not item.get('cover_url'):
                item['cover_url'] = detail.get('cover', '') or ''

            # 总集数
            total = detail.get('total', 0) or 0

            # 分集
            episodes_raw = detail.get('episodes', []) or []

            # 先提取所有分集并尝试解析排序键
            episodes_with_key = []
            for ep in episodes_raw:
                ep_badge = ep.get('badge', '') or ''
                title = ep.get('title', '') or ''
                long_title = ep.get('long_title', '') or ''
                show_title = ep.get('show_title', '') or ''
                ep_title = long_title or show_title or title

                # VIP: 分集 badge="会员"
                is_vip = 1 if ep_badge == '会员' else 0

                # 时长：毫秒转 MM:SS
                duration_ms = ep.get('duration', 0) or 0
                duration = self._format_duration(duration_ms)

                ep_data = {
                    'episode_num': str(ep.get('id', '')),
                    'vid': str(ep.get('aid', '') or ''),
                    'ep_id': str(ep.get('ep_id', '') or ep.get('id', '')),
                    'play_title': ep_title or title,
                    'title': title,
                    'long_title': long_title,
                    'episode_type': 0,  # B站分集无预告/花絮区分，全部为正片
                    'is_vip': is_vip,
                    'duration': duration,
                    'cover': ep.get('cover', ''),
                    'play_url': ep.get('link', '') or ep.get('share_url', '') or f'https://www.bilibili.com/bangumi/play/ep{ep.get("ep_id", ep.get("id", ""))}',
                }
                
                # 尝试提取排序键
                sort_key = self._extract_episode_sort_key(ep, title, show_title, long_title)
                episodes_with_key.append((sort_key, ep_data))
            
            # 按排序键排序（升序，第1集在前）
            episodes_with_key.sort(key=lambda x: x[0])
            # 更新 episodes 和 main_eps 为排序后的列表
            episodes = [x[1] for x in episodes_with_key]
            main_eps = episodes.copy()

            # 剧集级 VIP：任何一个分集是 VIP
            series_is_vip = item.get('is_vip', 0)
            if not series_is_vip:
                if any(ep['is_vip'] > 0 for ep in episodes):
                    series_is_vip = 1

            # VIP前2集免费规则（B站也有此规则）
            if series_is_vip > 0 and self.category_key != 'movie':
                free_count = 0
                for ep in episodes:
                    free_count += 1
                    if free_count <= 2:
                        ep['is_vip'] = 0

            item['is_vip'] = series_is_vip
            item['episodes'] = episodes

            # 填充 first_vid 和 play_url（B站列表页不返回vid，需从详情页分集提取）
            if episodes and not item.get('first_vid'):
                first_ep = episodes[0]
                item['first_vid'] = first_ep.get('ep_id', '') or first_ep.get('vid', '')
                ep_id = item['first_vid']
                if ep_id:
                    item['play_url'] = f'https://www.bilibili.com/bangumi/play/ep{ep_id}'
                    logger.debug(f'填充first_vid: {item.get("title")} -> ep{ep_id}')

            # 集数统计
            main_count = len(episodes)
            item['total_episodes'] = total or main_count
            item['updated_episodes'] = main_count
            item['has_episodes'] = True

            # 完结状态判断
            new_ep = detail.get('new_ep', {}) or {}
            new_ep_desc = new_ep.get('desc', '') or ''  # e.g. "已完结, 全10集"
            pub_is_finish = (detail.get('publish', {}) or {}).get('is_finish', 0) or 0

            item['is_finished'] = self._judge_finished(
                is_finish_list=item.get('_is_finish_list', pub_is_finish),
                index_show=item.get('_index_show', '') or '',
                new_ep_desc=new_ep_desc,
                total=total,
                main_count=main_count,
                category_key=self.category_key,
            )

            # 清理临时字段
            for key in ['_season_id', '_badge', '_index_show', '_order_text', '_sub_title', '_is_finish_list']:
                item.pop(key, None)

            logger.info(
                f"提取到 {len(episodes)} 集，"
                f"总{total}集，"
                f"VIP={series_is_vip}，"
                f"完结={item['is_finished']}"
            )

        except Exception as e:
            logger.error(f"详情获取失败: {item.get('title', '未知')}, 错误: {e}", exc_info=True)

    # === 完结判断 ===

    @classmethod
    def _judge_finished(cls, is_finish_list, index_show, new_ep_desc,
                        total, main_count, category_key):
        """
        多信号完结判断。
        返回: 1=已完结, -1=连载中, 0=未知
        """
        # 信号1：列表页 is_finish 字段（最可靠）
        if is_finish_list == 1:
            return 1

        # 信号2：index_show / new_ep_desc 含"全"
        combined = f'{index_show} {new_ep_desc}'
        if '全' in combined and '更新' not in combined:
            return 1

        # 信号3：含"更新至" → 连载中
        if '更新至' in combined or '更新到' in combined:
            return -1

        # 信号4：电影（1集=完结）
        if category_key == 'movie':
            if main_count >= 1:
                return 1
            return 0

        # 信号5：总集数 > 正片数 → 连载中
        if total > 0 and main_count < total:
            return -1

        # 信号6：总集数 == 正片数 → 已完结
        if total > 0 and main_count >= total:
            return 1

        return 0

    # === 工具 ===

    @staticmethod
    def _extract_episode_sort_key(ep, title, show_title, long_title):
        """
        从分集排序键提取（优先级从高到低）
        """
        # 1. 优先尝试 B站 API 可能提供的 index/sort/order 字段
        for field in ['index', 'sort', 'order', 'sort_index', 'order_index']:
            val = ep.get(field)
            if val is not None and val != '':
                try:
                    return int(val)
                except (ValueError, TypeError):
                    continue
        
        # 2. 尝试从标题里提取数字（比如“第1集”、“第2话”等）
        all_texts = [str(title), str(show_title), str(long_title)]
        for text in all_texts:
            if not text:
                continue
            # 匹配“第X集”、“第X话”、“第X期”等格式
            match = re.search(r'第[^\d]*(\d+)[集话期SP]', text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, TypeError):
                    continue
            # 直接匹配数字
            match = re.search(r'(\d+)', text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, TypeError):
                    continue
        
        # 3. 尝试用 ep_id 或 id 排序
        for field in ['ep_id', 'id']:
            val = ep.get(field)
            if val is not None and val != '':
                try:
                    return int(val)
                except (ValueError, TypeError):
                    continue
        
        # 4. 最后用列表里的索引作为 fallback
        return 0

    @staticmethod
    def _format_duration(duration_ms):
        """毫秒转 MM:SS 格式"""
        if not duration_ms:
            return ''
        try:
            total_sec = int(duration_ms) // 1000
            minutes = total_sec // 60
            seconds = total_sec % 60
            return f'{minutes:02d}:{seconds:02d}'
        except (ValueError, TypeError):
            return str(duration_ms)
