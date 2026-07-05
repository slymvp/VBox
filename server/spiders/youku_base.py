"""
优酷视频爬虫基类
通过频道页SSR获取列表，通过详情页SSR获取分集信息
数据来源：
1. 列表页：频道页 __INITIAL_DATA__
2. 详情页：播放页 __INITIAL_DATA__
"""
import requests
import json
import re
import time
from core.base_spider import BaseSpider
from core.logger import setup_logger
from core.retry import RetryHelper
from spiders.keywords import load_keywords

logger = setup_logger('vbox.youku')


class YoukuBaseSpider(BaseSpider):
    """优酷视频爬虫基类"""

    # 频道页URL模板
    CHANNEL_URL_MAP = {
        'tv': 'https://www.youku.com/ku/webtv',
        'movie': 'https://www.youku.com/ku/webmovie',
        'variety': 'https://www.youku.com/ku/webvariety',
        'cartoon': 'https://www.youku.com/ku/webcomic',
        'child': 'https://www.youku.com/ku/webchild',
    }

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.youku.com/',
    }

    # 每页获取的最大item数（频道页SSR一次返回所有，需截断）
    PAGE_SIZE = 20

    # 关键词 fallback：DB 不可用时使用（参见任务 #34 seed_keywords.py 将数据写入 DB）
    _TRAILER_FALLBACK = [
        '预告', 'trailer', 'teaser', '先导', '前瞻', '片花',
        '抢先看', '抢先版', '预告片',
    ]
    _VIP_FALLBACK = [
        'vip', '会员', '独播', '限免', '用券', '付费', '乐学',
    ]
    _BTS_FALLBACK = [
        '花絮', '特辑', '独家', '幕后', '制作',
        '精彩片段', '精彩看点', '加更', '纯享', '尊享',
        '未删减', '加长版', '导演版', '彩蛋',
        '购物车', '小剧场', '番外', '探班', '片场',
        'NG', 'ng', '路透', '采访', '发布会',
        '见面会', '开机', '杀青', '剧照', 'MV',
        '主题曲', '片尾曲', '插曲', '高能', '看点',
        '策划', '企划', '陪看',
    ]
    _SKIP_MODULE_FALLBACK = [
        '猜你喜欢', '推荐', '热门排行', '排行榜', '大家都在看',
    ]

    def __init__(self, platform_name, channel_config, category_key='tv'):
        super().__init__(platform_name, channel_config)
        self.category_key = category_key
        self.channel_url = self.CHANNEL_URL_MAP.get(category_key, 'https://www.youku.com/ku/webtv')
        self.timeout = 30
        # sort: 'hot' = 热门列表, 'new' = 最新列表, ''/None = 默认（不刷标记）
        self._list_type = str(channel_config.get('sort', '') or '')
        self._page_fetched = False  # 频道页SSR只请求一次

        # 反爬：动态构建完整请求头（带代理轮换）
        from core.anti_crawl import build_headers
        self.session = self.create_session()
        self.HEADERS = build_headers(
            referer='https://www.youku.com/',
            ua=self.get_user_agent(),
        )
        self.session.headers.update(self.HEADERS)

        # 从 AdminPlatform 配置加载关键词（fallback 到硬编码）
        self._trailer_keywords = load_keywords('youku', 'trailer', self._TRAILER_FALLBACK)
        self._vip_keywords = load_keywords('youku', 'vip', self._VIP_FALLBACK)
        self._bts_keywords = load_keywords('youku', 'bts', self._BTS_FALLBACK)

    def _request_get_with_retry(self, url, params=None, timeout=None):
        """带重试的GET请求封装"""
        timeout = timeout or self.timeout

        def _do_request():
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp

        return RetryHelper.with_retry(
            _do_request, max_retries=3, base_delay=1, max_delay=8,
            exceptions=(Exception,)
        )

    def _request_page_with_retry(self, url, timeout=None):
        """带重试的页面请求，返回原始HTML"""
        timeout = timeout or self.timeout

        def _do_request():
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text

        return RetryHelper.with_retry(
            _do_request, max_retries=3, base_delay=1, max_delay=8,
            exceptions=(Exception,)
        )

    # ==================== 列表页 ====================

    def fetch_list_page(self, page=1, **kwargs):
        """通过频道页SSR获取剧集列表"""
        try:
            # 频道页SSR一次返回所有数据，第1页之后返回None终止翻页
            if page > 1:
                return None

            logger.info(f"请求频道页: {self.channel_url}")
            resp = self._request_get_with_retry(self.channel_url)
            html = resp.text

            # 提取 __INITIAL_DATA__
            start = html.find('__INITIAL_DATA__')
            if start < 0:
                logger.warning("频道页无__INITIAL_DATA__")
                return None

            end = html.find(';</script>', start)
            if end < 0:
                logger.warning("频道页__INITIAL_DATA__解析失败")
                return None

            raw = html[start:end]
            eq = raw.find('=')
            data_str = raw[eq + 1:].replace('undefined', 'null')
            data = json.loads(data_str)

            return data

        except Exception as e:
            logger.error(f"频道页请求失败: {e}")
            return None

    def extract_items(self, api_data):
        """从频道页SSR数据中提取剧集列表"""
        if not api_data:
            return []

        results = []
        seen = set()

        try:
            module_list = api_data.get('moduleList', [])
            for module_idx, module in enumerate(module_list):
                components = module.get('components', [])
                for comp in components:
                    # 优酷频道页SSR结构：module[0]是频道主推内容（最准确），
                    # module[1+]是"正在热播""专题推荐"等，容易混入其他类型内容。
                    # 综艺/动漫/少儿频道只取module[0]，避免分类错误；
                    # 电视剧/电影频道可取前2个模块以获取更多数据。
                    comp_title = str(comp.get('title', '') or '').lower()
                    if self.category_key in ('variety', 'cartoon', 'child'):
                        if module_idx > 0:
                            continue
                    else:
                        # 电视剧/电影：跳过明显的推荐模块
                        if any(kw in comp_title for kw in self._SKIP_MODULE_FALLBACK):
                            continue
                        if module_idx > 1:
                            continue

                    item_list = comp.get('itemList', [])
                    for it in item_list:
                        try:
                            if not isinstance(it, dict):
                                continue
                            extracted = self._extract_item(it)
                            if extracted and extracted['cid'] not in seen:
                                seen.add(extracted['cid'])
                                results.append(extracted)
                        except Exception as e:
                            logger.warning(f"提取单个项目失败: {e}")
                            continue

            logger.info(f"提取到 {len(results)} 个剧集")
            return results

        except Exception as e:
            logger.error(f"提取剧集失败: {e}", exc_info=True)
            return []



    def _extract_item(self, item):
        """从频道页SSR的单个item中提取信息"""
        # action_value: JUMP_TO_SHOW时为showId，JUMP_TO_VIDEO时为vid
        action_value = item.get('action_value', '')
        title = item.get('title', '')

        if not action_value or not title:
            return None

        # 处理 JUMP_TO_SHOW 和 JUMP_TO_VIDEO 两种类型
        action_type = item.get('action_type', '')
        if action_type == 'JUMP_TO_SHOW':
            show_id = action_value
            # JUMP_TO_SHOW时不立即解析vid，留到详情获取阶段
            # previewInfo.videoId是预告片vid，仅作为回退
            preview_info = item.get('previewInfo', {}) or {}
            first_vid = preview_info.get('videoId', '') or ''
        elif action_type == 'JUMP_TO_VIDEO':
            show_id = ''
            first_vid = action_value  # vid格式如 XNjUyODY3NTc1Ng==
        else:
            return None

        # 封面图
        img_url = item.get('img', '') or ''
        h_img = item.get('hImg', '') or ''  # 横版大图

        # 高清封面
        cover_url = self._upgrade_youku_image(h_img) if h_img else self._upgrade_youku_image(img_url)

        # VIP标识：mark.text 在 ('VIP', '会员', '独播', '限免中', '用券', '付费', '乐学VIP')
        is_vip = 0
        mark = item.get('mark', {}) or {}
        if isinstance(mark, dict):
            mark_text = str(mark.get('text', '') or '')
            if self._is_vip_mark(mark_text):
                is_vip = 1

        # titleIcon中含vip也视为VIP标识
        if not is_vip:
            title_icon = item.get('titleIcon', {}) or {}
            icon_url = str(title_icon.get('url', '') or '')
            if 'vip' in icon_url.lower():
                is_vip = 1

        # 标签：从tags字段提取
        tags = []
        raw_tags = item.get('tags', []) or []
        for t in raw_tags:
            if isinstance(t, dict):
                text_obj = t.get('text', {}) or {}
                tag_title = text_obj.get('title', '') if isinstance(text_obj, dict) else str(text_obj)
                if tag_title:
                    tags.append(tag_title)
            elif isinstance(t, str):
                tags.append(t)

        # 集数/完结状态（如 "29集全"、"更新至6集"、"限免16-18集"）
        lb_texts = item.get('lbTexts', '') or ''
        total_episodes, is_finished = self._parse_lb_texts(str(lb_texts))

        # 电影回退：无lbTexts但有有效标记 → 已上线即完结
        if is_finished == 0 and self.category_key == 'movie':
            mark_text = str((item.get('mark', {}) or {}).get('text', '') or '')
            if self._is_vip_mark(mark_text) or mark_text == '首播':
                is_finished = 1
            elif mark_text == '预告':
                is_finished = -1

        # 描述 (含演员信息，格式: "演员A 演员B｜剧情简介")
        desc = item.get('desc', '') or ''

        # 从描述中提取演员
        actors = self._extract_actors_from_desc(str(desc))

        # 评分：从 topLeftMark 提取（格式: "豆瓣 9.4分"）
        score = ''
        top_left_mark = item.get('topLeftMark', {}) or {}
        if isinstance(top_left_mark, dict):
            tl_text = (top_left_mark.get('text', {}) or {}).get('subTitle', '') or ''
            m_score = re.search(r'([\d.]+)分', str(tl_text))
            if m_score:
                score = m_score.group(1)

        # previewInfo 中的 videoId（仅当之前未从action_type获取到first_vid时使用）
        preview_info = item.get('previewInfo', {}) or {}
        if not first_vid:
            first_vid = preview_info.get('videoId', '') or ''

        # cid: 优先用showId，JUMP_TO_VIDEO时用vid
        cid = show_id or first_vid

        # 播放URL（必须用vid格式，showId格式会404）
        play_url = f'https://v.youku.com/v_show/id_{first_vid}.html' if first_vid else ''

        return {
            'platform': 'youku',
            'cid': cid,
            'title': title,
            'category_key': self.category_key,
            'first_vid': first_vid,
            'area': '',
            'year': '',
            'score': score,
            'tags': tags,
            'actors': actors,
            'director': '',
            'thumbnail': img_url,
            'cover_url': cover_url,
            'play_url': play_url,
            'is_vip': is_vip,
            'is_finished': is_finished,
            'is_hot': 1 if self._list_type == 'hot' else 0,
            'is_new': 1 if self._list_type == 'new' else 0,
            'total_episodes': total_episodes,
            'description': desc,
        }

    def _parse_lb_texts(self, lb_texts):
        """解析 lbTexts 获取总集数和完结状态

        返回 (total_episodes, is_finished)

        lbTexts 格式示例:
        - 电视剧: "28集全" / "更新至6集" / "限免16-18集"
        - 少儿/动画: "11期全" / "更新至13期" / "52期全"
        - 动漫/番剧: "26话全" / "更新至144话" / "12话全"
        - 电影: 通常为空字符串
        """
        if not lb_texts:
            return 0, 0

        total_episodes = 0

        # 先提取总集数
        # 模式1: "XX[集期话]全" / "全XX[集期话]"
        m = re.search(r'(\d+)\s*[集期话]\s*全', lb_texts)
        if not m:
            m = re.search(r'全\s*(\d+)\s*[集期话]', lb_texts)
        if m:
            total_episodes = int(m.group(1))

        # 模式2: "更新至XX[集期话]"
        if not total_episodes:
            m = re.search(r'更新至\s*(\d+)\s*[集期话]', lb_texts)
            if m:
                total_episodes = int(m.group(1))

        # 模式3: 限免 → 连载中
        if '限免' in lb_texts:
            return total_episodes, -1

        # 模式4: 单集 "1[集期话]" / "1[集期话]全"
        if not total_episodes:
            m = re.search(r'(\d+)\s*[集期话]', lb_texts)
            if m:
                total_episodes = int(m.group(1))

        # 统一完结判断
        from core.finished_judge import judge
        is_finished = judge(
            text=lb_texts,
            total_episodes=total_episodes,
            main_count=total_episodes,  # 列表页只有总集数，详情页会更新
            category_key=self.category_key,
        )
        return total_episodes, is_finished

    # 以下方法保留用于详情页的额外判断
    def _parse_lb_texts_detail(self, lb_texts, main_count):
        """详情页用的 lbTexts 解析，结合实际正片数判断"""
        if not lb_texts:
            return 0, 0

        total_episodes = 0

        m = re.search(r'(\d+)\s*[集期话]\s*全', lb_texts)
        if not m:
            m = re.search(r'全\s*(\d+)\s*[集期话]', lb_texts)
        if m:
            total_episodes = int(m.group(1))

        if not total_episodes:
            m = re.search(r'更新至\s*(\d+)\s*[集期话]', lb_texts)
            if m:
                total_episodes = int(m.group(1))

        if '限免' in lb_texts:
            return total_episodes, -1

        if not total_episodes:
            m = re.search(r'(\d+)\s*[集期话]', lb_texts)
            if m:
                total_episodes = int(m.group(1))

        from core.finished_judge import judge
        is_finished = judge(
            text=lb_texts,
            total_episodes=total_episodes,
            main_count=main_count,
            category_key=self.category_key,
        )
        return total_episodes, is_finished

    def _parse_lb_texts_legacy(self, lb_texts):
        """保留旧逻辑用于兼容"""
        if not lb_texts:
            return 0, 0

        total_episodes = 0
        is_finished = 0

        m = re.search(r'(\d+)\s*[集期话]\s*全', lb_texts)
        if not m:
            m = re.search(r'全\s*(\d+)\s*[集期话]', lb_texts)
        if m:
            total_episodes = int(m.group(1))
            is_finished = 1
            return total_episodes, is_finished

        m = re.search(r'更新至\s*(\d+)\s*[集期话]', lb_texts)
        if m:
            total_episodes = int(m.group(1))
            is_finished = -1
            return total_episodes, is_finished

        if '限免' in lb_texts:
            is_finished = -1
            return total_episodes, is_finished

        m = re.search(r'(\d+)\s*[集期话]', lb_texts)
        if m:
            count = int(m.group(1))
            if count == 1:
                total_episodes = 1
                is_finished = 1
            else:
                total_episodes = count
                is_finished = -1
            return total_episodes, is_finished

        return total_episodes, is_finished

    @staticmethod
    def _is_recommendation_list(items):
        """判断itemList是真分集还是推荐视频

        真分集特征: 标题短且含数字/集号（如 "第1集"、"01"）
        推荐视频特征: 标题长且是描述性语句（如 "小轩在烟花下给七月戴上戒指！"）
        """
        if not items:
            return True

        ep_like = 0
        promo_like = 0
        for it in items[:20]:  # 只检查前20个
            if not isinstance(it, dict):
                continue
            title = str(it.get('title', '') or '')
            if not title:
                continue
            # 真分集标题：短，含数字/集号
            if re.search(r'第\s*\d+\s*集', title):
                ep_like += 1
            elif re.match(r'^\d+$', title) or re.match(r'^\d{1,2}$', title):
                ep_like += 1
            elif len(title) <= 6 and re.search(r'\d', title):
                ep_like += 1
            elif len(title) > 8 and any(kw in title for kw in ('！', '？', '。', '…', '，', '~')):
                promo_like += 1
            elif len(title) > 15:
                promo_like += 1

        # 如果超过一半是推荐视频，判定为推荐列表
        return promo_like > ep_like

    @staticmethod
    def _extract_actors_from_desc(desc):
        """从描述文本中提取演员（描述格式: "演员A 演员B｜剧情简介"）

        过滤掉非演员文本：
        - "适合X岁观看" (少儿频道)
        - 剧情关键词
        """
        if not desc:
            return ''

        # 用 "｜"（全角竖线）分割，第一部分是演员名单
        parts = desc.split('｜', 1)
        if not parts:
            return ''

        actor_text = parts[0].strip()

        # 跳过明显的非演员文本
        if not actor_text:
            return ''
        # 如 "适合3-9岁观看"
        if re.match(r'适合[\d\-]+岁', actor_text):
            return ''

        # 过滤剧情描述性文字
        if any(kw in actor_text for kw in ('改编', '讲述', '故事', '根据', '原著', '小说',
                                             '主演', '导演', '编剧', '出品', '播出',
                                             '益智', '冒险', '动画', '神话', '传统文化',
                                             '启蒙', '无对白', '脑力')):
            return ''

        names = actor_text.split()
        actors = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            if len(name) > 12:
                continue
            actors.append(name)

        return ' / '.join(actors) if actors else ''

    @staticmethod
    def _upgrade_youku_image(url, width=1080, height=608):
        """将优酷图片URL升级为更高清的尺寸"""
        if not url:
            return url
        return re.sub(r'@\d+w_\d+h', f'@{width}w_{height}h', url)

    # ==================== 详情页 ====================

    def fetch_detail(self, item):
        """获取详情和分集信息"""
        try:
            show_id = item.get('cid', '')
            title = item.get('title', '')

            if not show_id:
                logger.warning(f"缺少showId: {title}")
                return

            logger.info(f"获取详情: {title} - showId: {show_id}")

            # 获取分集列表（传完整item，而非仅show_id）
            episodes, detail = self._fetch_episodes(item)

            # 补充详情信息
            if detail.get('description'):
                item['description'] = detail['description']
            if detail.get('actors') and not item.get('actors'):
                item['actors'] = detail['actors']
            if detail.get('director') and not item.get('director'):
                item['director'] = detail['director']
            if detail.get('cover_url') and not item.get('cover_url'):
                item['cover_url'] = detail['cover_url']
            if detail.get('score') and not item.get('score'):
                item['score'] = detail['score']
            if detail.get('area') and not item.get('area'):
                item['area'] = detail['area']
            if detail.get('year') and not item.get('year'):
                item['year'] = detail['year']

            if episodes:
                def _ep_sort_key(ep):
                    num = str(ep.get('episode_num', '') or '')
                    return int(num) if num.isdigit() else 9999

                episodes.sort(key=_ep_sort_key)

                # 整剧VIP标识：列表页判断优先，其次从分集聚合判断
                series_is_vip = item.get('is_vip', 0)  # 优先保留列表页判断
                if not series_is_vip:
                    series_is_vip = detail.get('series_is_vip', 0)
                if not series_is_vip:
                    for ep in episodes:
                        if ep.get('episode_type') == 0 and ep.get('is_vip', 0) > 0:
                            series_is_vip = 1
                            break

                # 根据整剧VIP状态统一设置分集is_vip
                for ep in episodes:
                    ep['is_vip'] = series_is_vip

                # VIP前2集免费规则：非电影的电视剧，正片前2集强制is_vip=0
                if series_is_vip > 0 and self.category_key != 'movie':
                    main_eps_free_count = 0
                    for ep in episodes:
                        if ep.get('episode_type') == 0:
                            main_eps_free_count += 1
                            if main_eps_free_count <= 2:
                                ep['is_vip'] = 0

                # 预告和花絮强制免费
                for ep in episodes:
                    if ep.get('episode_type') != 0:
                        ep['is_vip'] = 0

                item['episodes'] = episodes
                main_eps = [ep for ep in episodes if ep.get('episode_type') == 0]
                trailer_eps = [ep for ep in episodes if ep.get('episode_type') == 1]
                bts_eps = [ep for ep in episodes if ep.get('episode_type') == 2]
                main_count = len(main_eps)

                if not item.get('total_episodes'):
                    item['total_episodes'] = main_count
                item['updated_episodes'] = main_count
                item['has_episodes'] = True
                item['is_vip'] = series_is_vip

                logger.info(
                    f"提取到 {len(episodes)} 集（正片{main_count}集，预告{len(trailer_eps)}集，"
                    f"花絮{len(bts_eps)}集），VIP={series_is_vip}"
                )
            else:
                # 无分集数据：使用列表页已有的数据
                item['has_episodes'] = False
                if not item.get('total_episodes'):
                    item['total_episodes'] = 0
                item['updated_episodes'] = item.get('updated_episodes', 0) or 0
                # 保留列表页VIP判断，detail只补充
                if not item.get('is_vip') and detail.get('series_is_vip'):
                    item['is_vip'] = detail['series_is_vip']
                logger.info(f"无分集数据，使用列表页信息: total={item.get('total_episodes',0)}, is_finished={item.get('is_finished',0)}, vip={item.get('is_vip',0)}")

        except Exception as e:
            logger.error(f"详情获取失败: {item.get('title', '未知')}, 错误: {e}", exc_info=True)

    def _resolve_first_vid_from_show(self, show_id, title=''):
        """当 first_vid 为空时，通过 showId 页面获取 first_vid

        优酷的 showId 页面格式: https://www.youku.com/show_page/id_{showId}.html
        该页面会302重定向到 vid 格式的播放页，或者页面中包含 vid 信息
        """
        try:
            show_url = f'https://www.youku.com/show_page/id_{show_id}.html'
            headers = dict(self.HEADERS)
            headers['AllowRedirect'] = 'true'

            resp = requests.get(show_url, headers=headers, timeout=self.timeout, allow_redirects=True)

            # 方式1：从重定向后的URL中提取vid
            final_url = resp.url
            vid_match = re.search(r'id_([a-zA-Z0-9=]+)', final_url)
            if vid_match:
                return vid_match.group(1)

            # 方式2：从页面HTML中提取vid
            html = resp.text

            # 从 __INITIAL_DATA__ 中提取
            start = html.find('__INITIAL_DATA__')
            if start >= 0:
                end = html.find(';</script>', start)
                if end >= 0:
                    raw = html[start:end]
                    eq = raw.find('=')
                    data_str = raw[eq + 1:].replace('undefined', 'null')
                    data = json.loads(data_str)
                    # 尝试从多种路径提取 vid
                    for path in [
                        lambda d: d.get('videoId', ''),
                        lambda d: d.get('show', {}).get('videoId', ''),
                        lambda d: d.get('show', {}).get('firstVid', ''),
                        lambda d: (d.get('show', {}).get('videos', []) or [{}])[0].get('vid', ''),
                        lambda d: (d.get('show', {}).get('videoList', []) or [{}])[0].get('vid', ''),
                    ]:
                        try:
                            vid = path(data)
                            if vid:
                                return vid
                        except (IndexError, KeyError, TypeError):
                            continue

            # 方式3：从HTML中正则提取vid
            vid_match = re.search(r'v_show/id_([a-zA-Z0-9=]+)', html)
            if vid_match:
                return vid_match.group(1)

            # 方式4：从 meta 标签或链接中提取
            vid_match = re.search(r'"videoId"\s*:\s*"([a-zA-Z0-9=]+)"', html)
            if vid_match:
                return vid_match.group(1)

            logger.warning(f'从showId页面未能获取vid: {title} ({show_id})')
            return ''

        except Exception as e:
            logger.error(f'从showId页面获取vid失败: {title} ({show_id}), 错误: {e}')
            return ''

    def _fetch_episodes(self, item):
        """从详情页SSR数据中提取分集信息和详情元数据

        注意：优酷详情页__INITIAL_DATA__的moduleList中通常是推荐视频（非正片分集），
        需要尝试多种字段路径获取真正的分集列表。
        """
        episodes = []
        series_detail = {}
        show_id = item.get('cid', '')
        title = item.get('title', '')

        # 电影不需要分集（电影就是1集完整内容）
        if self.category_key == 'movie':
            logger.debug(f'电影跳过分集获取: {title}')
            return episodes, series_detail

        # 预先从列表页数据补充 is_finished（详情页SSR通常没有此字段）
        if item.get('is_finished') is not None:
            series_detail['list_is_finished'] = item.get('is_finished')

        try:
            # 详情页必须用vid格式URL（showId格式会404）
            first_vid = item.get('first_vid', '')

            # 优先通过showId获取正片vid（列表页的previewInfo.videoId是预告片vid）
            if show_id:
                real_vid = self._resolve_first_vid_from_show(show_id, title)
                if real_vid:
                    if real_vid != first_vid:
                        logger.info(f'用showId解析到正片vid: {title} {first_vid} -> {real_vid}')
                    first_vid = real_vid
                    item['first_vid'] = first_vid
                    item['play_url'] = f'https://v.youku.com/v_show/id_{first_vid}.html'
            elif not first_vid:
                logger.warning(f'缺少showId和first_vid: {title}')
                return episodes, series_detail

            if not first_vid:
                logger.warning(f'缺少first_vid，无法获取详情: {title}')
                return episodes, series_detail

            url = f'https://v.youku.com/v_show/id_{first_vid}.html'
            html = self._request_page_with_retry(url)

            # 提取 __INITIAL_DATA__
            start = html.find('__INITIAL_DATA__')
            if start < 0:
                logger.warning(f"详情页无__INITIAL_DATA__: {show_id}")
                # 尝试用showId获取正片vid后重试
                if show_id and show_id != first_vid:
                    real_vid = self._resolve_first_vid_from_show(show_id, title)
                    if real_vid and real_vid != first_vid:
                        logger.info(f'用showId解析到正片vid，重试: {title} -> {real_vid}')
                        first_vid = real_vid
                        item['first_vid'] = first_vid
                        item['play_url'] = f'https://v.youku.com/v_show/id_{first_vid}.html'
                        url = f'https://v.youku.com/v_show/id_{first_vid}.html'
                        html = self._request_page_with_retry(url)
                        start = html.find('__INITIAL_DATA__')
                if start < 0:
                    return episodes, series_detail

            end = html.find(';</script>', start)
            if end < 0:
                logger.warning(f"详情页__INITIAL_DATA__解析失败: {show_id}")
                return episodes, series_detail

            raw = html[start:end]
            eq = raw.find('=')
            data_str = raw[eq + 1:].replace('undefined', 'null')
            data = json.loads(data_str)

            # __INITIAL_DATA__ 为空对象时，尝试用showId获取正片vid重试
            if not data:
                logger.warning(f"详情页__INITIAL_DATA__为空: {title} (vid={first_vid})")
                if show_id and show_id != first_vid:
                    real_vid = self._resolve_first_vid_from_show(show_id, title)
                    if real_vid and real_vid != first_vid:
                        logger.info(f'用showId解析到正片vid，重试: {title} -> {real_vid}')
                        first_vid = real_vid
                        item['first_vid'] = first_vid
                        item['play_url'] = f'https://v.youku.com/v_show/id_{first_vid}.html'
                        url = f'https://v.youku.com/v_show/id_{first_vid}.html'
                        html = self._request_page_with_retry(url)
                        start2 = html.find('__INITIAL_DATA__')
                        if start2 >= 0:
                            end2 = html.find(';</script>', start2)
                            if end2 >= 0:
                                raw2 = html[start2:end2]
                                eq2 = raw2.find('=')
                                data_str2 = raw2[eq2 + 1:].replace('undefined', 'null')
                                data = json.loads(data_str2)
                if not data:
                    return episodes, series_detail

            # 方式1：从moduleList中提取分集和详情
            module_list = data.get('moduleList', [])
            for module in module_list:
                components = module.get('components', [])
                for comp in components:
                    item_list = comp.get('itemList', [])

                    # 判断comp是否是视频推荐（非真分集）
                    comp_title = str(comp.get('title', '') or '')
                    # 已知的真分集组件标题白名单（直接信任，不做推荐判断）
                    episode_titles = {'选集', '分集', '正片', '剧集', '节目'}
                    # 已知的推荐组件标题黑名单（这些组件里的itemList是推荐视频而非真分集）
                    recommend_titles = {'视频', '系列电影', '相关推荐', '猜你喜欢', '为你推荐', '热门推荐', '大家都在看'}
                    if comp_title in recommend_titles:
                        continue
                    # 白名单组件直接信任为真分集
                    if comp_title not in episode_titles:
                        # 非白名单组件用内容特征判断
                        if item_list and self._is_recommendation_list(item_list):
                            continue

                    for it in item_list:
                        if not isinstance(it, dict):
                            continue
                        ep = self._parse_episode_item(it, show_id)
                        if ep:
                            episodes.append(ep)

                    # 提取详情信息
                    self._extract_detail_from_component(comp, series_detail)

            # 方式2：从data.nodes提取（优酷新版SSR结构）
            if not episodes:
                nodes = data.get('nodes', []) or []
                for node in nodes:
                    node_items = node.get('items', []) or node.get('itemList', []) or []
                    for it in node_items:
                        ep = self._parse_episode_item(it, show_id)
                        if ep:
                            episodes.append(ep)

            # 方式3：从data.videoList / data.videos提取
            if not episodes:
                episodes = self._extract_episodes_from_data(data, show_id)

            # 方式4：从data.show提取分集信息
            if not episodes:
                show_data = data.get('show', {}) or {}
                video_list = show_data.get('videos', []) or show_data.get('videoList', []) or []
                for v in video_list:
                    if isinstance(v, dict):
                        vid = v.get('vid', '') or v.get('videoId', '') or v.get('encodeVid', '')
                        title = v.get('title', '') or v.get('name', '') or v.get('seq', '')
                        if vid:
                            episode_type = self._get_episode_type(title)
                            episodes.append({
                                'episode_num': self._extract_episode_num(title),
                                'vid': vid,
                                'play_title': title,
                                'union_title': '',
                                'episode_type': episode_type,
                                'is_trailer': episode_type == 1,
                                'duration': v.get('duration', ''),
                                'video_subtitle': '',
                                'publish_date': '',
                                'is_vip': 1 if v.get('isVip') else 0,
                                'play_url': 'https://v.youku.com/v_show/id_' + vid + '.html',
                            })

        except json.JSONDecodeError as e:
            logger.error(f"详情页JSON解析失败: {show_id}, 错误: {e}")
        except Exception as e:
            logger.error(f"获取分集失败: {show_id}, 错误: {e}")

        return episodes, series_detail

    def _parse_episode_item(self, item, show_id):
        """解析单个分集项"""
        if not isinstance(item, dict):
            return None

        action_value = item.get('action_value', '')
        title = item.get('title', '') or item.get('subTitle', '')

        if not action_value:
            return None

        # 过滤非视频格式的action_value
        # 1. youku://协议、http链接（演员卡片、页面跳转等）
        if action_value.startswith('youku://') or action_value.startswith('http://') or action_value.startswith('https://'):
            return None
        # 2. showId是16位hex字符（0-9a-f），vid包含大写字母和=号
        if re.match(r'^[0-9a-f]{16,}$', action_value):
            return None
        # 3. 纯数字ID（如10005、10050），不是有效vid
        if re.match(r'^\d+$', action_value):
            return None

        vid = action_value

        # 判断分集类型
        play_title = title
        episode_type = self._get_episode_type(play_title)

        # VIP标识
        is_vip = 0
        mark = item.get('mark', {}) or {}
        if isinstance(mark, dict):
            tag_text = str(mark.get('text', '') or '')
            if self._is_vip_mark(tag_text):
                is_vip = 1
        elif isinstance(mark, str) and self._is_vip_mark(mark):
            is_vip = 1

        # 集号
        episode_num = self._extract_episode_num(title)

        return {
            'episode_num': episode_num,
            'vid': vid,
            'play_title': play_title,
            'union_title': '',
            'episode_type': episode_type,
            'is_trailer': episode_type == 1,
            'duration': '',
            'video_subtitle': '',
            'publish_date': '',
            'is_vip': is_vip,
            'play_url': f'https://v.youku.com/v_show/id_{vid}.html',
        }

    def _extract_episodes_from_data(self, data, show_id):
        """从其他数据结构中提取分集（兜底）"""
        episodes = []

        # 尝试从videoList提取
        video_list = data.get('videoList', []) or data.get('videos', [])
        for v in video_list:
            if isinstance(v, dict):
                vid = v.get('vid', '') or v.get('videoId', '')
                title = v.get('title', '') or v.get('name', '')
                if vid:
                    episode_type = self._get_episode_type(title)
                    episodes.append({
                        'episode_num': self._extract_episode_num(title),
                        'vid': vid,
                        'play_title': title,
                        'union_title': '',
                        'episode_type': episode_type,
                        'is_trailer': episode_type == 1,
                        'duration': v.get('duration', ''),
                        'video_subtitle': '',
                        'publish_date': '',
                        'is_vip': 1 if v.get('isVip') else 0,
                        'play_url': f'https://v.youku.com/v_show/id_{vid}.html',
                    })

        return episodes

    def _extract_detail_from_component(self, comp, series_detail):
        """从组件数据中提取详情信息（演员/导演/评分/地区/年份等）"""
        # 从itemList中的第一个item提取详情
        items = comp.get('itemList', [])
        if not items:
            return

        it = items[0]

        # 描述
        if not series_detail.get('description'):
            desc = it.get('desc', '') or it.get('summary', '')
            if desc:
                series_detail['description'] = desc

        # VIP标识
        if not series_detail.get('series_is_vip'):
            mark = it.get('mark', {})
            if isinstance(mark, dict):
                tag_text = str(mark.get('text', '') or '')
                if self._is_vip_mark(tag_text):
                    series_detail['series_is_vip'] = 1
            # 从titleIcon判断
            title_icon = it.get('titleIcon', {}) or {}
            icon_url = str(title_icon.get('url', '') or '')
            if 'vip' in icon_url.lower():
                series_detail['series_is_vip'] = 1

        # 演员（从item自身或子item提取）
        if not series_detail.get('actors'):
            actors = it.get('actors', '') or it.get('starrings', '')
            if not actors and 'desc' in it:
                actors = self._extract_actors_from_desc(str(it.get('desc', '') or ''))
            if actors:
                series_detail['actors'] = actors

        # 导演
        if not series_detail.get('director'):
            directors = it.get('directors', '') or it.get('director', '')
            if directors:
                series_detail['director'] = directors

        # 评分
        if not series_detail.get('score'):
            score = it.get('score', '') or it.get('rating', '')
            if not score:
                top_left = it.get('topLeftMark', {}) or {}
                tl_text = (top_left.get('text', {}) or {}).get('subTitle', '') or ''
                m_score = re.search(r'([\d.]+)分', str(tl_text))
                if m_score:
                    score = m_score.group(1)
            if score:
                series_detail['score'] = score

        # 地区
        if not series_detail.get('area'):
            area = it.get('area', '') or it.get('region', '')
            if area:
                series_detail['area'] = area

        # 年份
        if not series_detail.get('year'):
            year = it.get('year', '') or it.get('publishDate', '')
            if not year:
                # 从 publishDate 提取年份 (如 "2025-01-01")
                pub_date = str(it.get('publishDate', '') or '')
                m = re.match(r'(\d{4})', pub_date)
                if m:
                    year = m.group(1)
            if year:
                series_detail['year'] = str(year)[:4]

    def _is_vip_mark(self, mark_text: str) -> bool:
        """判断mark文本是否表示VIP/付费（包含匹配，不区分大小写）"""
        if not mark_text:
            return False
        text_lower = mark_text.lower()
        return any(kw in text_lower for kw in self._vip_keywords)

    @staticmethod
    def _extract_episode_num(title: str) -> int:
        """从标题提取集号：'第5集'→5, '01'→1, '精选片段'→0"""
        if not title:
            return 0
        # 优先匹配 "第N集/期/话"
        m = re.search(r'第\s*(\d+)\s*[集期话]', title)
        if m:
            return int(m.group(1))
        # 纯数字标题（如 "01", "12"）
        if re.match(r'^\d{1,4}$', title.strip()):
            return int(title.strip())
        # 短标题中含数字（如 "1.精彩看点"）
        if len(title) <= 8:
            m = re.search(r'^(\d+)[\s\.\-\|]', title.strip())
            if m:
                return int(m.group(1))
        return 0

    def _get_episode_type(self, play_title):
        """判断分集类型：0=正片, 1=预告, 2=花絮"""
        title_lower = play_title.lower()
        for kw in self._trailer_keywords:
            if kw in title_lower:
                return 1
        for kw in self._bts_keywords:
            if kw in title_lower:
                return 2
        return 0

    # ==================== crawl流程 ====================

    def crawl(self, max_items=10):
        """优酷爬取流程：串行获取列表，并发获取详情"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print(f'[{self.platform_name}] 开始爬取...')

        all_items = []
        seen_ids = set()

        # 第一阶段：串行翻页获取列表
        page = 1
        while max_items is None or len(all_items) < max_items:
            print(f'正在获取第 {page} 页...')
            data = self.fetch_list_page(page)
            if not data:
                print(f'第 {page} 页请求失败，停止爬取')
                break

            items = self.extract_items(data)

            new_count = 0
            for item in items:
                item_id = self._get_item_id(item)
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    all_items.append(item)
                    new_count += 1
                    if max_items is not None and len(all_items) >= max_items:
                        break

            print(f'本次获取 {len(items)} 条，新增 {new_count} 条，总计 {len(all_items)} 条')

            if new_count == 0 and len(items) == 0:
                break

            page += 1
            time.sleep(0.5)

        # 截断
        if max_items is not None and len(all_items) > max_items:
            all_items = all_items[:max_items]

        print(f'列表获取完成，共 {len(all_items)} 条')

        # 第二阶段：增量过滤
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
        print(f'开始获取详情，共 {len(all_items)} 条（并发数={self.max_workers}）')

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

        print(f'完成！共 {len(all_items)} 条数据')
        return all_items

    def _fetch_detail_safe(self, item):
        """线程安全的详情获取"""
        try:
            self.fetch_detail(item)
        except Exception as e:
            logger.error(f"获取详情异常: {item.get('title')}, 错误: {e}")
            raise
        finally:
            time.sleep(0.5)  # 限流
