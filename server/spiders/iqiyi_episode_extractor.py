"""
爱奇艺分集信息提取器
优先使用官方API获取分集数据，Playwright作为备选方案

核心原则：
1. 直接信任详情页的剧集列表，不做名称过滤
2. 保留原始名称入库，不做格式化处理
3. 只区分正片和预告（is_trailer标记）
"""
import re
import time
import json
import requests
from core.logger import setup_logger
from spiders.keywords import load_keywords

logger = setup_logger('vbox.iqiyi.extractor')

# 尝试导入Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright未安装，Playwright备选方案不可用")

# 预告关键词（数据库 fallback）
_TRAILER_KEYWORDS_DEFAULT = [
    '预告', 'trailer', 'teaser',
    '先导', '前瞻',
    '片花',
]

# 花絮关键词（数据库 fallback）
_BTS_KEYWORDS_DEFAULT = [
    '花絮', '特辑', '独家', '幕后', '制作',
    '专访', '访谈', '纪录片', '特别篇',
    '精彩片段', '精彩内容', '精彩看点',
    '人物特辑', '制作特辑', '幕后花絮',
    '独家揭秘', '独家探班', '独家专访',
    '探班', '片场', 'NG', 'ng',
    '路透', '采访', '发布会', '见面会',
    '开机', '杀青', '剧照', 'OST', 'ost',
    '主题曲', '片尾曲', '插曲', 'MV', 'mv',
    '番外', '彩蛋', '先导片', '宣传片',
    '高能', '看点', '策划', '企划',
]

# ============================================================
# 关键词 fallback：DB 不可用时使用（参见 seed_keywords.py）
# ============================================================


class IQiyiEpisodeExtractor:
    """爱奇艺分集提取器"""

    def __init__(self):
        self.timeout = 8
        # 反爬：动态构建完整请求头
        from core.anti_crawl import build_headers, get_random_ua
        self.headers = build_headers(
            referer='https://www.iqiyi.com/',
            origin='https://www.iqiyi.com',
            ua=get_random_ua(),
        )
        # 从 AdminPlatform 配置加载关键词（fallback 到硬编码）
        self._trailer_keywords = load_keywords('iqiyi', 'trailer', _TRAILER_KEYWORDS_DEFAULT)
        self._bts_keywords = load_keywords('iqiyi', 'bts', _BTS_KEYWORDS_DEFAULT)

    def extract_episodes(self, cid, url='', album_str_id=None, total_episodes=0, updated_episodes=0, item_type=None):
        """
        主入口：提取剧集的分集列表
        优化：API优先，禁用Playwright，避免爬虫长时间运行
        """
        logger.info(f"提取分集: cid={cid}")

        # 方法1: API直接获取分集（最快，优先尝试）
        episodes, latest_order = self._extract_with_api(cid, album_str_id=album_str_id, item_type=item_type)
        if episodes:
            episodes = self._deduplicate_episodes(episodes, latest_order=latest_order, total_episodes=total_episodes)
            logger.info(f"API方式获取到 {len(episodes)} 集")
            return episodes

        # 方法2: 专辑页HTML（备用）
        episodes, latest_order = self._extract_via_album_page(cid, album_str_id=album_str_id, item_type=item_type)
        if episodes:
            is_completed = total_episodes and updated_episodes and total_episodes == updated_episodes
            if not is_completed and item_type != 'movie':
                api_episodes, api_latest_order = self._extract_with_api(cid, album_str_id=album_str_id, item_type=item_type)
                if api_episodes:
                    api_trailers = [ep for ep in api_episodes if ep.get('episode_type', 0) == 1]
                    if api_trailers:
                        existing_vids = {ep.get('vid') for ep in episodes}
                        new_trailers = [ep for ep in api_trailers if ep.get('vid') not in existing_vids]
                        if new_trailers:
                            episodes.extend(new_trailers)

            episodes = self._deduplicate_episodes(episodes, latest_order=latest_order, total_episodes=total_episodes)
            logger.info(f"专辑页方式获取到 {len(episodes)} 集")
            return episodes

        # 方法3: 详情页HTML
        page_url = url or f'https://www.iqiyi.com/v_{cid}.html'
        episodes, latest_order = self._extract_via_detail_page(cid, page_url, item_type=item_type)
        if episodes:
            episodes = self._deduplicate_episodes(episodes, latest_order=latest_order, total_episodes=total_episodes)
            logger.info(f"详情页方式获取到 {len(episodes)} 集")
            return episodes

        logger.warning(f"所有方法均失败，未能获取分集数据: cid={cid}")
        return []

    # ==================== 数据获取方法 ====================

    def _extract_via_album_page(self, cid, album_str_id=None, item_type=None):
        """通过baseinfo API获取专辑页URL，再访问专辑页解析分集HTML"""
        if not cid:
            return [], 0

        try:
            latest_order = 0
            if not album_str_id:
                album_str_id, latest_order = self._get_album_info(cid)
                latest_order = latest_order or 0
            else:
                # 如果已有album_str_id，也获取latestOrder
                _, latest_order = self._get_album_info(cid)
                latest_order = latest_order or 0

            if not album_str_id:
                logger.warning(f"无法获取专辑页ID: albumId={cid}")
                return [], latest_order

            album_page_url = f'https://www.iqiyi.com/a_{album_str_id}.html'
            logger.info(f"访问专辑页: {album_page_url}")
            resp = requests.get(album_page_url, headers=self.headers, timeout=self.timeout)

            if resp.status_code != 200:
                logger.warning(f"专辑页返回非200状态码: {resp.status_code}")
                return [], latest_order

            episodes = self._extract_from_html(resp.text, album_str_id, album_page_url, latest_order=latest_order, item_type=item_type)
            logger.info(f"从专辑页提取到 {len(episodes)} 集")
            return episodes, latest_order

        except Exception as e:
            logger.error(f"专辑页提取分集失败: {e}")
            return [], 0

    def _extract_via_detail_page(self, cid, page_url, item_type=None):
        """从详情页HTML中提取albumId，再尝试专辑页或API"""
        try:
            logger.info(f"从详情页提取albumId: {page_url}")
            resp = requests.get(page_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return [], 0

            html = resp.text
            album_id = ''
            album_str_id = None

            # 从 window.videoInfo 提取
            video_info_match = re.search(r'window\.videoInfo\s*=\s*({.*?});', html, re.DOTALL)
            if video_info_match:
                try:
                    video_info = json.loads(video_info_match.group(1))
                    album_id = str(video_info.get('albumId', '') or video_info.get('album_id', ''))
                    if album_id:
                        logger.info(f"从videoInfo提取到albumId: {album_id}")
                except json.JSONDecodeError:
                    pass

            # 从 window.pageInfo 提取
            if not album_id:
                page_info_match = re.search(r'window\.pageInfo\s*=\s*({.*?});', html, re.DOTALL)
                if page_info_match:
                    try:
                        page_info = json.loads(page_info_match.group(1))
                        album_id = str(page_info.get('albumId', '') or page_info.get('album_id', ''))
                        album_url = page_info.get('albumUrl', '') or page_info.get('url', '')
                        if album_url:
                            url_match = re.search(r'/a_([^.]+)\.html', album_url)
                            if url_match:
                                album_str_id = url_match.group(1)
                        if album_id:
                            logger.info(f"从pageInfo提取到albumId: {album_id}")
                    except json.JSONDecodeError:
                        pass

            # 正则匹配albumId
            if not album_id:
                album_match = re.search(r"""albumId['"]?\s*[:=]\s*['"]?(\d+)""", html)
                if album_match:
                    album_id = album_match.group(1)
                    logger.info(f"从HTML正则提取到albumId: {album_id}")

            # 用提取到的albumId走专辑页或API
            latest_order = 0
            if album_id and album_id != str(cid):
                episodes, latest_order = self._extract_via_album_page(album_id, album_str_id=album_str_id, item_type=item_type)
                if episodes:
                    return episodes, latest_order
                episodes, latest_order = self._extract_with_api(album_id, album_str_id=album_str_id, item_type=item_type)
                if episodes:
                    return episodes, latest_order

            # 最后尝试直接从当前HTML中提取分集链接
            # 这里尝试获取一下latest_order
            if album_id:
                _, latest_order = self._get_album_info(album_id)
            latest_order = latest_order or 0
            return self._extract_from_html(html, cid, page_url, latest_order=latest_order, item_type=item_type), latest_order

        except Exception as e:
            logger.error(f"详情页提取失败: {e}")
            return [], 0

    def _extract_with_api(self, album_id, album_str_id=None, item_type=None):
        """通过avlistinfo API直接获取分集数据"""
        if not album_id:
            return [], 0

        try:
            api_url = 'https://pcw-api.iqiyi.com/albums/album/avlistinfo'
            params = {
                'albumId': album_id,
                'pageSize': 50,
                'pageNum': 1,
            }

            logger.info(f"请求avlistinfo API: albumId={album_id}")
            resp = requests.get(api_url, headers=self.headers, params=params, timeout=self.timeout)

            if resp.status_code != 200:
                logger.warning(f"avlistinfo API返回非200状态码: {resp.status_code}")
                return [], 0

            data = resp.json()
            eps_data = data.get('data', {})
            if not isinstance(eps_data, dict):
                logger.warning(f'avlistinfo API返回异常data字段: type={type(eps_data).__name__}')
                return [], 0

            ep_list = (eps_data.get('episodes', [])
                       or eps_data.get('vodlist', [])
                       or eps_data.get('list', [])
                       or eps_data.get('videos', []))
            if not ep_list:
                logger.info("avlistinfo API返回空分集列表")
                return [], 0

            total = eps_data.get('total', 0) or len(ep_list)

            all_episodes, latest_order = self._parse_api_episodes(data, album_id, item_type=item_type)
            if not all_episodes:
                return [], latest_order

            if total > params['pageSize']:
                remaining = self._fetch_remaining_api_pages(album_id, total, params['pageSize'], start_page=2)
                all_episodes.extend(remaining)

            logger.info(f"API获取到 {len(all_episodes)} 集（共{total}集）")
            return all_episodes, latest_order

        except Exception as e:
            logger.error(f"avlistinfo API请求失败: {e}")
            return [], 0

    def _extract_with_playwright(self, url, cid, item_type=None):
        """使用Playwright渲染获取分集"""
        episodes = []
        latest_order = 0

        # 尝试获取latest_order
        if str(cid).isdigit():
            _, latest_order = self._get_album_info(cid)
            latest_order = latest_order or 0

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ])
                from core.anti_crawl import build_playwright_context_options, get_stealth_scripts
                ctx_opts = build_playwright_context_options()
                context = browser.new_context(**ctx_opts)
                context.add_init_script(get_stealth_scripts())
                page = context.new_page()

                logger.info(f"Playwright访问页面: {url}")
                page.goto(url, timeout=15000, wait_until='domcontentloaded')
                time.sleep(2)

                try:
                    page.wait_for_selector('a[href*="/v_"]', timeout=5000)
                except Exception:
                    pass

                self._scroll_page(page)
                self._scroll_page(page)

                html = page.content()
                episodes = self._extract_from_html(html, cid, url, latest_order=latest_order, item_type=item_type)
                browser.close()

            except Exception as e:
                logger.error(f"Playwright提取失败: {e}")
                try:
                    browser.close()
                except Exception:
                    pass

        return episodes, latest_order

    def extract_cover_url(self, url):
        """
        使用Playwright渲染页面，提取横版（封面）大图URL。
        主要用于电影：电影没有baseinfo，API无法获取headImages横版大图。
        返回 str 或 None。

        提取策略（优先级从高到低）：
        1. 从页面内嵌 JSON（__INITIAL_STATE__）解析完整JSON后递归搜索封面字段，备选正则扫描键值对
        2. og:image meta（爱奇艺电影页通常是专辑横版封面）
        3. 专辑封面专属选择器（含播放器区域poster等）
        4. 页面主视觉区域大图选择器
        注意：不使用"最大宽度img"策略，该策略会误命中播放器截帧图(pv_xxx_em_601.jpg)
        不使用全页面lequ路径扫描，会误命中广告图/推荐位图
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright未安装，无法提取封面图")
            return None
        if not url:
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ])
                from core.anti_crawl import build_playwright_context_options, get_stealth_scripts
                ctx_opts = build_playwright_context_options()
                context = browser.new_context(**ctx_opts)
                context.add_init_script(get_stealth_scripts())
                page = context.new_page()

                logger.info(f"Playwright提取封面图: {url}")
                page.goto(url, timeout=15000, wait_until='domcontentloaded')
                time.sleep(3)

                cover_url = None
                html = page.content()

                # 方法1: 从内嵌 JSON 数据中提取专辑封面（最可靠，字段与专辑强绑定）
                # 爱奇艺页面内嵌 window.__INITIAL_STATE__ 等，解析完整JSON后提取封面字段
                try:
                    HORIZONTAL_KEYS = [
                        'horizontalPic', 'horizontalImageUrl', 'albumHImage',
                        'horizontalImage', 'wideImageUrl', 'coverHorizontalUrl',
                        'movieImage', 'img_url_hz',
                    ]
                    # 尝试提取 __INITIAL_STATE__ 完整JSON并解析
                    # 策略：找到赋值语句起始位置，然后手动匹配大括号找到完整JSON
                    init_start = re.search(r'window\.__INITIAL_STATE__\s*=\s*\{', html)
                    if init_start:
                        # 从第一个 { 开始，手动匹配大括号层级
                        brace_start = init_start.end() - 1  # 指向 {
                        depth = 0
                        brace_end = brace_start
                        for i in range(brace_start, min(brace_start + 500000, len(html))):
                            if html[i] == '{':
                                depth += 1
                            elif html[i] == '}':
                                depth -= 1
                                if depth == 0:
                                    brace_end = i + 1
                                    break
                        raw_json = html[brace_start:brace_end]
                        try:
                            state_data = json.loads(raw_json)
                            # 递归搜索JSON中所有包含封面字段的字典
                            def _find_cover(obj, depth=0):
                                if depth > 8 or not isinstance(obj, dict):
                                    return None
                                for key in HORIZONTAL_KEYS:
                                    val = obj.get(key, '')
                                    if isinstance(val, str) and val.startswith('http') and not re.search(r'_em_\d+\.', val):
                                        return val
                                for v in obj.values():
                                    if isinstance(v, dict):
                                        result = _find_cover(v, depth + 1)
                                        if result:
                                            return result
                                return None
                            cover_url = _find_cover(state_data)
                        except (json.JSONDecodeError, ValueError):
                            pass

                    # 备选：直接从HTML正则扫描横版字段键值对
                    if not cover_url:
                        for key in HORIZONTAL_KEYS:
                            pattern = rf'"{key}"\s*:\s*"(https?://[^"]+\.(?:jpg|png|webp|jpeg)[^"]*)"'
                            matches = re.findall(pattern, html)
                            for m in matches:
                                if re.search(r'_em_\d+\.', m):
                                    continue
                                cover_url = m
                                break
                            if cover_url:
                                break
                except Exception:
                    pass

                # 方法2: og:image meta（爱奇艺电影页通常是正确的专辑封面）
                if not cover_url:
                    try:
                        meta = page.query_selector('meta[property="og:image"]')
                        if meta:
                            og = meta.get_attribute('content') or ''
                            # 处理协议相对URL（//pic...）
                            if og.startswith('//'):
                                og = 'https:' + og
                            # 只排除明确的播放器截帧（pv_xxx_em_601格式）
                            if og and og.startswith('http') and not re.search(r'_em_\d+\.', og):
                                cover_url = og
                                logger.debug(f"og:image封面: {og[:80]}")
                    except Exception:
                        pass

                # 方法3: 专辑封面专属选择器（侧边栏/简介区的封面图）
                if not cover_url:
                    try:
                        COVER_SELECTORS = [
                            '.album-cover img',
                            '.intro-cover img',
                            '.detail-cover img',
                            '[class*="albumCover"] img',
                            '[class*="album-cover"] img',
                            '.m-video-cover img',
                            '.video-info-cover img',
                            '.mod-player-wrap img',
                            '.qy-player-wrap img',
                            '[class*="playerPoster"] img',
                            '[class*="poster"] img',
                        ]
                        for sel in COVER_SELECTORS:
                            el = page.query_selector(sel)
                            if el:
                                src = el.get_attribute('src') or el.get_attribute('data-src') or ''
                                if src and src.startswith('http') and not re.search(r'_em_\d+\.', src):
                                    cover_url = src
                                    break
                    except Exception:
                        pass

                # 方法4: 从页面主视觉区域提取大图（避免扫描全页面lequ图片误命中广告图）
                if not cover_url:
                    try:
                        HERO_SELECTORS = [
                            '.mod-video-info img',
                            '.qy-player-side img',
                            '.header-cover img',
                            '[class*="bannerImg"] img',
                            '[class*="BannerImg"] img',
                        ]
                        for sel in HERO_SELECTORS:
                            el = page.query_selector(sel)
                            if el:
                                src = el.get_attribute('src') or el.get_attribute('data-src') or ''
                                if src and src.startswith('http') and not re.search(r'_em_\d+\.', src):
                                    cover_url = src
                                    break
                    except Exception:
                        pass

                browser.close()
                if cover_url:
                    logger.info(f"Playwright提取到封面图: {cover_url[:100]}")
                else:
                    logger.warning(f"Playwright未能提取封面图: {url}")
                return cover_url

        except Exception as e:
            logger.error(f"Playwright提取封面图失败: {e}")
            return None

    # ==================== 数据解析方法 ====================

    def _get_album_info(self, album_id):
        """通过baseinfo API获取专辑页信息，包括字符串ID和latestOrder"""
        try:
            baseinfo_url = f'https://pcw-api.iqiyi.com/album/album/baseinfo/{album_id}'
            logger.info(f"请求baseinfo API: albumId={album_id}")
            resp = requests.get(baseinfo_url, headers=self.headers, timeout=self.timeout)

            if resp.status_code != 200:
                return None, 0

            data = resp.json()
            if data.get('code') != 'A00000':
                return None, 0

            album_data = data.get('data', {})
            album_url = album_data.get('url', '')

            str_id = None
            if album_url:
                match = re.search(r'/a_([^.]+)\.html', album_url)
                if match:
                    str_id = match.group(1)
                    logger.info(f"获取到专辑页ID: {str_id}")

            # 获取latestOrder
            latest_order = album_data.get('latestOrder', 0)
            if isinstance(latest_order, str):
                latest_order = int(latest_order) if latest_order.isdigit() else 0
            elif not isinstance(latest_order, int):
                latest_order = 0

            logger.info(f"获取到latestOrder: {latest_order}")
            return str_id, latest_order

        except Exception as e:
            logger.error(f"baseinfo API请求失败: {e}")
            return None, 0

    def _parse_api_episodes(self, data, album_id, item_type=None):
        """解析API返回的分集数据，直接信任剧集列表，保留原始名称"""
        episodes = []
        latest_order = 0

        try:
            eps_data = data.get('data', {})
            if not isinstance(eps_data, dict):
                return [], latest_order

            # 获取实际更新到的集数（latestOrder）
            latest_order = eps_data.get('latestOrder', 0)
            if isinstance(latest_order, str):
                latest_order = int(latest_order) if latest_order.isdigit() else 0

            ep_list = (eps_data.get('episodes', [])
                       or eps_data.get('vodlist', [])
                       or eps_data.get('list', [])
                       or eps_data.get('videos', []))
            if not ep_list:
                return [], latest_order

            bts_counter = 0  # 花絮独立计数器
            for idx, ep in enumerate(ep_list):
                vid = (str(ep.get('tvId', ''))
                       or str(ep.get('tv_id', ''))
                       or str(ep.get('vid', ''))
                       or str(ep.get('id', '')))

                # 保留原始名称，不做格式化
                play_title = (ep.get('shortTitle', '')
                              or ep.get('name', '')
                              or ep.get('title', '')
                              or ep.get('playTitle', '')
                              or f'第{idx + 1}集')

                # 获取剧集的order字段（实际集号）
                ep_order = ep.get('order', idx + 1)
                if isinstance(ep_order, str):
                    ep_order = int(ep_order) if ep_order.isdigit() else idx + 1
                elif not isinstance(ep_order, int):
                    ep_order = idx + 1

                # 优先使用 API contentType 字段判断类型，无则靠标题关键词
                # contentType: 1=正片, 3=预告/宣传内容（含访谈专访等）
                api_content_type = ep.get('contentType')
                episode_type = self._get_episode_type(play_title, content_type=api_content_type, item_type=item_type)

                play_url = ep.get('playUrl', '') or ep.get('play_url', '') or ''
                if not play_url and vid:
                    play_url = f'https://www.iqiyi.com/v_{vid}.html'

                duration = ''
                if ep.get('duration', ''):
                    dur = ep.get('duration', '')
                    if isinstance(dur, (int, float)):
                        minutes = int(dur) // 60
                        seconds = int(dur) % 60
                        duration = f'{minutes:02d}:{seconds:02d}'
                    else:
                        duration = str(dur)

                publish_date = ''
                if ep.get('publishTime', ''):
                    publish_date = str(ep.get('publishTime', ''))
                elif ep.get('firstPlayTime', ''):
                    publish_date = str(ep.get('firstPlayTime', ''))

                # 提取集号：全部使用纯数字
                if episode_type == 2:
                    # 花絮使用独立计数器分配纯数字集号
                    bts_counter += 1
                    episode_num = str(bts_counter)
                elif ep_order and ep_order > 0:
                    # 优先用 API 的 order 字段作为集号（避免标题解析错误）
                    episode_num = str(ep_order)
                else:
                    # 回退到标题解析
                    episode_num = self._extract_episode_number(play_title, idx + 1)

                # VIP标识：仅正片判断，预告/花絮强制免费
                if episode_type != 0:
                    is_vip = 0
                else:
                    pay_mark = ep.get('payMark', 0)
                    is_purchase = ep.get('isPurchase', 0)
                    if str(is_purchase) == '1':
                        is_vip = 2  # 点播
                    elif str(pay_mark) == '1':
                        is_vip = 1  # VIP
                    else:
                        is_vip = 0  # 免费

                episode = {
                    'episode_num': episode_num,
                    'vid': vid,
                    'play_title': play_title,
                    'union_title': play_title,
                    'episode_type': episode_type,  # 0=正片，1=预告，2=花絮
                    'duration': duration,
                    'publish_date': publish_date,
                    'play_url': play_url,
                    'is_vip': is_vip,
                }
                episodes.append(episode)

        except Exception as e:
            logger.error(f"解析API分集数据失败: {e}")

        return episodes, latest_order

    def _fetch_remaining_api_pages(self, album_id, total, page_size, start_page=2):
        """翻页获取剩余分集"""
        all_episodes = []
        total_pages = (total + page_size - 1) // page_size

        for page in range(start_page, total_pages + 1):
            try:
                api_url = 'https://pcw-api.iqiyi.com/albums/album/avlistinfo'
                params = {
                    'albumId': album_id,
                    'pageSize': page_size,
                    'pageNum': page,
                }

                resp = requests.get(api_url, headers=self.headers, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    break

                data = resp.json()
                eps = self._parse_api_episodes(data, album_id)
                if not eps:
                    break

                all_episodes.extend(eps)
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"翻页获取分集失败(page={page}): {e}")
                break

        return all_episodes

    def _extract_from_html(self, html, cid, page_url, latest_order=0, item_type=None):
        """从HTML提取分集链接。

        两阶段提取：
        1. 专辑页 JSON 数据源 → 正片 + 预告（contentType 是权威来源）
        2. BeautifulSoup 全页面扫描 → 补充花絮（花絮不在 JSON 数组中）
        """
        all_episodes = []
        seen_vids = set()

        # ========== Step 1: JSON 数据源（正片 + 预告） ==========
        json_episodes = self._extract_from_album_json(html, cid, page_url, latest_order=latest_order, item_type=item_type)
        if json_episodes:
            all_episodes.extend(json_episodes)
            seen_vids.update(ep.get('vid') for ep in json_episodes)
            logger.info(f"从专辑页JSON数据源提取到 {len(json_episodes)} 集（正片+预告）")

        # ========== Step 2: BeautifulSoup 补充花絮 ==========
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            # 没有 BeautifulSoup：如果 JSON 有数据就返回，否则交正则兜底
            if all_episodes:
                return all_episodes
            return self._extract_with_regex(html, cid, page_url, latest_order=latest_order, item_type=item_type)

        soup = BeautifulSoup(html, 'html.parser')

        if not all_episodes:
            # JSON 无数据，走完整 BeautifulSoup 流程
            playlist_links = self._find_all_playlist_links(soup)
            if playlist_links:
                logger.info(f"从分集列表容器中找到 {len(playlist_links)} 个链接")
                for link in playlist_links:
                    ep = self._parse_episode_link(link, cid, seen_vids, latest_order=latest_order, item_type=item_type)
                    if ep:
                        all_episodes.append(ep)
                # movie filter
                if item_type == "movie":
                    all_episodes = self._filter_movie_episodes(all_episodes, page_url)
                # 综艺正片集号修正
                if item_type == "variety":
                    self._renumber_variety_episodes(all_episodes)
                if all_episodes:
                    return all_episodes

            # 容器未找到，从整个页面提取但过滤推荐区域
            logger.info("未找到分集列表容器，从全页面提取并过滤推荐区域")
            for selector in ['.mod-recommend', '.qy-player-side', '.mod-side', '.side-wrap',
                             '.recommend', '.relative', '.hot-rec', '[class*="recommend"]',
                             '[class*="related"]', '[class*="side"]', '.m-slider',
                             '.m-iqycard-wrap', '.qy-mod-li']:
                for tag in soup.select(selector):
                    tag.decompose()
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                ep = self._parse_episode_link(link, cid, seen_vids, latest_order=latest_order, item_type=item_type)
                if ep:
                    all_episodes.append(ep)
            # movie filter
            if item_type == "movie":
                all_episodes = self._filter_movie_episodes(all_episodes, page_url)
            # 综艺正片集号修正
            if item_type == "variety":
                self._renumber_variety_episodes(all_episodes)
            return all_episodes

        # JSON 已有正片+预告 → 全页面扫描只补充花絮和漏网预告
        for selector in ['.mod-recommend', '.qy-player-side', '.mod-side', '.side-wrap',
                         '.recommend', '.relative', '.hot-rec', '[class*="recommend"]',
                         '[class*="related"]', '[class*="side"]', '.m-slider',
                         '.m-iqycard-wrap', '.qy-mod-li']:
            for tag in soup.select(selector):
                tag.decompose()

        all_links = soup.find_all('a', href=True)
        supplement_count = 0
        for link in all_links:
            ep = self._parse_episode_link(link, cid, seen_vids, latest_order=latest_order, item_type=item_type)
            if ep:
                ep_type = ep.get('episode_type', 0)
                if ep_type != 0:  # 只补充花絮和预告（正片 JSON 已覆盖）
                    all_episodes.append(ep)
                    supplement_count += 1

        if supplement_count:
            logger.info(f"从HTML补充了 {supplement_count} 个花絮/预告")

        # 综艺正片集号修正：综艺日期期号格式（如"-08-28期"）无法从标题提取数字期号，
        # _parse_episode_link 会用 seen_vids 长度做集号，导致正片集号不连续。
        # 对综艺正片按出现顺序重新编号为 1, 2, 3...
        if item_type == 'variety':
            self._renumber_variety_episodes(all_episodes)

        # 按实际类型统计
        type_counts = {0: 0, 1: 0, 2: 0}
        for ep in all_episodes:
            t = ep.get('episode_type', 0)
            type_counts[t] = type_counts.get(t, 0) + 1
        logger.info(f"最终提取到 {len(all_episodes)} 集（正片{type_counts.get(0,0)}、预告{type_counts.get(1,0)}、花絮{type_counts.get(2,0)}）")
        return all_episodes

    def _renumber_variety_episodes(self, episodes):
        """综艺正片集号重新编号。

        综艺的日期期号格式（如"-08-28期"、"20250610期"）无法从标题提取数字期号，
        导致 _parse_episode_link 用 seen_vids 长度分配集号，正片集号可能不连续。
        此方法对综艺正片按出现顺序重新编号为 1, 2, 3...
        同时对预告也重新编号（接在正片之后），花絮独立编号。
        """
        if not episodes:
            return

        main_eps = [ep for ep in episodes if ep.get('episode_type') == 0]
        trailer_eps = [ep for ep in episodes if ep.get('episode_type') == 1]
        bts_eps = [ep for ep in episodes if ep.get('episode_type') == 2]

        # 正片：按出现顺序编号 1, 2, 3...
        for i, ep in enumerate(main_eps, 1):
            old_num = ep.get('episode_num', '')
            ep['episode_num'] = str(i)
            if old_num != str(i):
                logger.debug(f"综艺正片集号修正: {old_num} -> {i} ({ep.get('play_title', '')[:30]})")

        # 预告：接在正片之后编号
        next_num = len(main_eps) + 1
        for ep in trailer_eps:
            old_num = ep.get('episode_num', '')
            ep['episode_num'] = str(next_num)
            if old_num != str(next_num):
                logger.debug(f"综艺预告集号修正: {old_num} -> {next_num} ({ep.get('play_title', '')[:30]})")
            next_num += 1

        # 花絮：独立编号 1, 2, 3...
        for i, ep in enumerate(bts_eps, 1):
            ep['episode_num'] = str(i)

        if main_eps or trailer_eps:
            logger.info(f"综艺集号重新编号: 正片{len(main_eps)}集, 预告{len(trailer_eps)}集, 花絮{len(bts_eps)}集")

    def _filter_movie_episodes(self, episodes, page_url):
        """电影分集过滤器：电影只有1集正片，全页面扫描会抓到广告/推荐区链接。

        关键认知：
        - 爱奇艺电影的 page_url vid（专辑主页vid）与正片播放 vid 是两个不同的值，
          不能用 vid 相等来判断"是否是本片正片"。
        - 需要用标题特征过滤广告，保留第1个非广告正片作为电影本体。

        策略：
        1. 丢弃广告链接（标题含"广告"关键词，或含广告后缀格式"xxx广告"）
        2. 丢弃推荐剧集链接（标题为"第N集"且N>1，属于推荐区的连续剧第N集）
        3. 只保留第1个非广告正片（即电影本体）
        4. 预告/花絮全部保留
        """
        if not episodes:
            return episodes

        # 广告标题特征（正则）
        AD_PATTERN = re.compile(
            r'广告|赞助|推广|ad(?:vertis|\s)|sponsor',
            re.IGNORECASE
        )
        # 推荐区连续剧特征："第N集" 且 N >= 2
        SERIES_EP_PATTERN = re.compile(r'^第\s*([2-9]\d*|\d{2,})\s*集$')

        result = []
        kept_main = False
        dropped = 0

        for ep in episodes:
            ep_type = ep.get('episode_type', 0)
            ep_vid = ep.get('vid', '')
            title = ep.get('play_title', '') or ''

            if ep_type == 0:
                # 检查是否是广告
                if AD_PATTERN.search(title):
                    dropped += 1
                    logger.info('Movie filter: DROPPED ad vid=%s title=%s' % (ep_vid, title))
                    continue
                # 检查是否是推荐区连续剧（"第2集"、"第3集"等），这类是页面推荐的其他剧
                if SERIES_EP_PATTERN.match(title.strip()):
                    dropped += 1
                    logger.info('Movie filter: DROPPED series-ep vid=%s title=%s' % (ep_vid, title))
                    continue
                # 第一个非广告正片 = 电影本体
                if not kept_main:
                    result.append(ep)
                    kept_main = True
                    logger.info('Movie filter: KEPT main vid=%s title=%s' % (ep_vid, title))
                else:
                    # 多余正片丢弃
                    dropped += 1
                    logger.info('Movie filter: DROPPED extra-main vid=%s title=%s' % (ep_vid, title))
            else:
                # 预告(1)/花絮(2)：只过滤广告，其余全保留
                if AD_PATTERN.search(title):
                    dropped += 1
                    logger.info('Movie filter: DROPPED ad-trailer vid=%s title=%s' % (ep_vid, title))
                    continue
                result.append(ep)

        main_count = sum(1 for ep in result if ep.get('episode_type') == 0)
        trailer_count = sum(1 for ep in result if ep.get('episode_type') == 1)
        bts_count = sum(1 for ep in result if ep.get('episode_type') == 2)
        logger.info('Movie filter result: main=%d trailer=%d bts=%d dropped=%d' % (
            main_count, trailer_count, bts_count, dropped))
        return result


    def _extract_from_album_json(self, html, cid, page_url, latest_order=0, item_type=None):
        """
        从专辑页 HTML 中的 JSON 数据源解析分集列表。

        爱奇艺专辑页有两个独立的 JSON 数组，是判断正片/预告的权威来源：
        - epsodelist: contentType=1 → 正片（已播出的正片集数）
        - updateprevuelist: contentType=3 → 预告/宣传内容（待播出的预告视频）

        每个条目都有 order 字段表示实际集号，比标题解析更可靠。
        """
        episodes = []
        seen_vids = set()

        # 解析 epsodelist（正片为主，但也可能包含预告/花絮）
        epsodelist = self._parse_json_array(html, 'epsodelist')
        if epsodelist:
            logger.info(f"epsodelist 包含 {len(epsodelist)} 条数据")
            for ep in epsodelist:
                ep_ct = ep.get('contentType')
                # 如果 epsodelist 中的条目 contentType 不是 1，说明可能是预告或花絮
                if ep_ct is not None and ep_ct != 1 and ep_ct != 3:
                    logger.debug(f"epsodelist 中发现非正片/预告条目: contentType={ep_ct}, title={ep.get('shortTitle', ep.get('name', ''))}")
                episode = self._parse_album_json_episode(ep, cid, seen_vids, content_type=ep_ct, latest_order=latest_order, item_type=item_type)
                if episode:
                    episodes.append(episode)
        else:
            logger.debug("未在专辑页中找到 epsodelist")

        # 解析 updateprevuelist（预告/宣传内容为主）
        prevuelist = self._parse_json_array(html, 'updateprevuelist')
        if prevuelist:
            logger.info(f"updateprevuelist 包含 {len(prevuelist)} 条数据")
            for ep in prevuelist:
                # 去重：如果 vid 已在 epsodelist 中出现，跳过
                vid = str(ep.get('tvId', '') or ep.get('vid', '') or ep.get('id', ''))
                play_url = ep.get('playUrl', '') or ''
                if play_url:
                    v_match = re.search(r'v_([^.]+)\.html', play_url)
                    if v_match:
                        vid = vid or v_match.group(1)
                if vid and vid in seen_vids:
                    continue

                ep_ct = ep.get('contentType')
                episode = self._parse_album_json_episode(ep, cid, seen_vids, content_type=ep_ct, latest_order=latest_order, item_type=item_type)
                if episode:
                    episodes.append(episode)
        else:
            logger.debug("未在专辑页中找到 updateprevuelist")

        if episodes:
            # 按 order 排序
            episodes.sort(key=lambda x: self._episode_sort_key(x['episode_num']))
            # 统计类型分布
            type_counts = {0: 0, 1: 0, 2: 0}
            for ep in episodes:
                t = ep.get('episode_type', 0)
                type_counts[t] = type_counts.get(t, 0) + 1
            logger.info(f"从专辑页JSON共提取 {len(episodes)} 集（正片{type_counts.get(0,0)}、预告{type_counts.get(1,0)}、花絮{type_counts.get(2,0)}）")
            return episodes

        return None

    @staticmethod
    def _parse_json_array(html, key):
        """从HTML中解析指定key的JSON数组"""
        try:
            # 匹配 "key":[{...}] 或 "key": [...]
            pattern = rf'"{key}"\s*:\s*\['
            m = re.search(pattern, html)
            if not m:
                return None

            start = m.end() - 1  # '[' 的位置
            depth = 0
            end = start
            for i, c in enumerate(html[start:], start=start):
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            raw = html[start:end + 1]
            return json.loads(raw)
        except Exception as e:
            logger.debug(f"解析 {key} JSON 数组失败: {e}")
            return None

    def _parse_album_json_episode(self, ep, cid, seen_vids, content_type, latest_order=0, item_type=None):
        """解析专辑页 JSON 数组中的单条分集/预告数据"""
        # 从 playUrl 提取 vid（如 http://www.iqiyi.com/v_23qvzz9m3gw.html -> 23qvzz9m3gw）
        # playUrl 中的短 vid 是最可靠的标识符
        play_url = ep.get('playUrl', '') or ep.get('play_url', '') or ''
        vid = ''
        if play_url:
            v_match = re.search(r'v_([^.]+)\.html', play_url)
            if v_match:
                vid = v_match.group(1)

        # 如果 playUrl 中没提取到，尝试 tvId 或 vid 字段
        if not vid:
            vid = str(ep.get('tvId', '') or ep.get('tv_id', '') or ep.get('vid', '') or ep.get('id', ''))

        if not vid:
            return None
        if vid == str(cid):
            return None

        # 去重
        if vid in seen_vids:
            return None
        seen_vids.add(vid)

        # 标题
        title = (ep.get('shortTitle', '')
                 or ep.get('name', '')
                 or ep.get('title', '')
                 or ep.get('playTitle', '')
                 or '')

        # 集号：优先用 order 字段（专辑页 JSON 里 order 就是实际集号，非常可靠）
        ep_order = ep.get('order', 0)
        if isinstance(ep_order, str):
            ep_order = int(ep_order) if ep_order.isdigit() else 0

        # 类型判断：contentType 来自专辑页 JSON，是权威来源
        # 1=epsodelist→正片，3=updateprevuelist→预告
        # 同时传入 duration 用于时长过滤：无关键词命中但时长 < 10 分钟 → 花絮
        episode_type = self._get_episode_type(title, content_type=content_type, item_type=item_type)

        # 集号全部使用纯数字
        if episode_type == 2:
            # 花絮：使用 seen_vids 当前长度作为顺序编号（入库时按实际花絮索引）
            episode_num = str(len(seen_vids))
        elif ep_order > 0:
            episode_num = str(ep_order)
        else:
            episode_num = str(len(seen_vids))

        # 构建 play_url
        if not play_url and vid:
            play_url = f'https://www.iqiyi.com/v_{vid}.html'

        # 时长
        duration = ''
        dur = ep.get('duration', '')
        if dur:
            if isinstance(dur, (int, float)):
                minutes = int(dur) // 60
                seconds = int(dur) % 60
                duration = f'{minutes:02d}:{seconds:02d}'
            else:
                duration = str(dur)

        # 发布日期
        publish_date = str(ep.get('publishTime', '') or ep.get('firstPlayTime', '') or '')

        # 生成规范的 play_title（全部使用真实名称，不做拼接）
        play_title = title.strip() or f'第{episode_num}集'

        # VIP标识：仅正片判断，预告/花絮强制免费
        if episode_type != 0:
            is_vip = 0
        else:
            pay_mark = ep.get('payMark', 0)
            is_purchase = ep.get('isPurchase', 0)
            if str(is_purchase) == '1':
                is_vip = 2  # 点播
            elif str(pay_mark) == '1':
                is_vip = 1  # VIP
            else:
                is_vip = 0  # 免费

        return {
            'episode_num': episode_num,
            'vid': vid,
            'play_title': play_title,
            'union_title': play_title,
            'episode_type': episode_type,
            'duration': duration,
            'publish_date': publish_date,
            'play_url': play_url,
            'is_vip': is_vip,
        }

    def _find_all_playlist_links(self, soup):
        """从已知的分集列表容器中选择器查找所有链接（包括正片和预告）"""
        precise_selectors = [
            # 优先提取正片链接
            '.plotTitle',
            '.plotNum',

            # 播放器相关
            '.iqp-player-videolink',
            '.iqp-videolink',
            '[data-player-hook="playlist"]',

            # 专辑页相关
            '.album-playlist',
            '.album-con',
            '.album-info',
            '.album-content',
            '.album-detail',
            '.mod-album',

            # 列表相关
            '.site-piclist',
            'ul.site-piclist',
            '.site-pic_list',
            '.site-list',
            'ul.site-list',
            '.scroll-wrap',
            '.mod-playList',
            '.play-list-item',
            '.tab-list',
            '.m-playlist',
            '#widget-videolist',
            '.video-list-wrap',
            '.mod-row-body',
            '.qy-player-videolink',

            # 分集列表
            '.episodes-list',
            '.episode-list',
            '.video-episodes',

        ]

        # 通用选择器：可能匹配到推荐区域，只在精确选择器无结果时使用
        fuzzy_selectors = [
            '[class*="playlist"]',
            '[class*="episodes"]',
            '[class*="video-list"]',
            '[class*="album-list"]',
            '[class*="play-list"]',
        ]

        all_video_links = []
        seen_containers = set()

        # 第一轮：用精确选择器查找
        for selector in precise_selectors:
            for container in soup.select(selector):
                container_id = id(container)
                if container_id in seen_containers:
                    continue
                seen_containers.add(container_id)

                links = container.find_all('a', href=True)
                video_links = [a for a in links if re.search(r'/[va]_[^/\.]+\.html', a.get('href', ''))]
                if video_links:
                    logger.info(f"找到分集列表容器: {selector}, 包含 {len(video_links)} 个视频链接")
                    all_video_links.extend(video_links)

        # 精确选择器找到了结果就直接返回，不再用通用选择器
        if all_video_links:
            logger.info(f"共从 {len(seen_containers)} 个精确容器中找到 {len(all_video_links)} 个视频链接")
            return all_video_links

        # 第二轮：精确选择器无结果，用通用选择器兜底
        logger.info("精确选择器未找到容器，尝试通用选择器")
        for selector in fuzzy_selectors:
            for container in soup.select(selector):
                container_id = id(container)
                if container_id in seen_containers:
                    continue
                seen_containers.add(container_id)

                links = container.find_all('a', href=True)
                video_links = [a for a in links if re.search(r'/[va]_[^/\.]+\.html', a.get('href', ''))]
                if len(video_links) >= 2:
                    logger.info(f"找到分集列表容器(通用): {selector}, 包含 {len(video_links)} 个视频链接")
                    all_video_links.extend(video_links)

        if all_video_links:
            logger.info(f"共从 {len(seen_containers)} 个容器中找到 {len(all_video_links)} 个视频链接")
            return all_video_links

        return None

    def _parse_episode_link(self, link, cid, seen_vids, latest_order=0, item_type=None):
        """解析单个链接为分集数据"""
        href = link.get('href', '')
        title = ''
        original_title = ''

        match = re.search(r'/([va])_([^/\.]+)\.html', href)
        if not match:
            return None

        vid = match.group(2)

        # 跳过专辑主页
        if vid == cid:
            return None

        # 去重
        if vid in seen_vids:
            return None
        seen_vids.add(vid)
        episode_index = len(seen_vids)

        # ========== 标题提取：优先用精确属性，避免get_text被子元素污染 ==========
        # 1. 优先从title属性获取（最可靠，是页面专门设置的）
        title = link.get('title', '') or ''

        # 2. 尝试 data-title 属性
        if not title:
            title = link.get('data-title', '') or ''

        # 3. 尝试其他data属性
        if not title:
            title = link.get('data-name', '') or link.get('data-title-text', '') or ''

        # 4. 尝试从子元素获取（如 span, em, strong 标签）
        if not title:
            for tag in link.find_all(['span', 'em', 'strong']):
                txt = tag.get_text(strip=True)
                # 过滤：纯数字（可能是评分如"9.2"）、时间格式、过短文本
                if txt and len(txt) > 1 and not re.match(r'^\d{1,2}:\d{2}', txt) and not re.match(r'^\d+\.?\d*$', txt):
                    title = txt
                    break

        # 5. 最后回退到get_text
        if not title or len(title) <= 1:
            title = link.get_text(strip=True)

        # 清理：get_text 可能取到评分数字前缀（如 "9.2阿凡达"），去掉开头数字/评分
        if title:
            # 去掉开头的评分数字（如 "9.2", "8.5 "）
            cleaned = re.sub(r'^\s*\d+\.?\d*\s*', '', title).strip()
            if cleaned and len(cleaned) > 1 and cleaned != title:
                title = cleaned
            # 如果清理后还是纯数字（如 "9.2"），丢弃
            if re.match(r'^\d+\.?\d*$', title.strip()):
                title = ''

        # 6. 最终默认
        if not title or len(title) <= 1:
            title = f'第{episode_index}集'

        original_title = title

        logger.debug(f"[分集] vid={vid}, 原始标题='{original_title}', 最终标题='{title}', index={episode_index}")

        # 过滤时间格式标题（短视频时长，如 "12:30"）
        if re.match(r'^\d{1,2}:\d{2}', title.strip()):
            logger.debug(f"[过滤] 时间格式标题: {title}")
            return None

        # 构建完整URL
        if href.startswith('http'):
            full_url = href
        elif href.startswith('//'):
            full_url = f'https:{href}'
        elif href.startswith('/'):
            full_url = f'https://www.iqiyi.com{href}'
        else:
            full_url = f'https://www.iqiyi.com/{href}'

        full_url = re.sub(r'(www\.iqiyi\.com)+/+/', 'www.iqiyi.com/', full_url)

        # 尝试从 HTML 属性中获取 contentType（爱奇艺部分页面会在 data-ct 或 data-content-type 上标注）
        html_content_type = None
        ct_val = link.get('data-content-type') or link.get('data-ct') or link.get('data-type')
        if ct_val and str(ct_val).isdigit():
            html_content_type = int(ct_val)

        # 判断类型：0=正片，1=预告，2=花絮（优先使用 HTML contentType 属性）
        episode_type = self._get_episode_type(title, content_type=html_content_type, item_type=item_type)

        # 提取集号（全部使用纯数字）
        if episode_type == 2:
            # 花絮用 seen_vids 当前长度作为顺序编号
            episode_num = str(len(seen_vids))
        else:
            # 正片和预告正常提取集号
            episode_num = self._extract_episode_number(title, episode_index)
            # 注意：综艺日期期号格式（如"-08-28期"）无法从标题提取数字期号，
            # 会回退到 episode_index（seen_vids 长度），可能导致集号不连续。
            # 由 _extract_from_html 层面的 _renumber_variety_episodes 统一修正

        # 如果有 latest_order，集号大于 latest_order 且类型不是花絮，强制标记为预告
        if latest_order is not None and latest_order > 0 and episode_num.isdigit() and episode_type != 2:
            ep_num = int(episode_num)
            if ep_num > latest_order:
                episode_type = 1
                logger.debug(f"集号 {ep_num} > latestOrder {latest_order}，强制标记为预告: {title}")

        # 生成标题（全部使用真实名称，不做拼接）
        play_title = title.strip()

        # 构建数据
        episode = {
            'episode_num': episode_num,
            'vid': vid,
            'play_title': play_title,
            'union_title': play_title,
            'episode_type': episode_type,  # 0=正片，1=预告，2=花絮
            'duration': '',
            'publish_date': '',
            'play_url': full_url,
            'is_vip': 0,  # HTML解析无法获取VIP信息，默认免费，由fetch_detail层统一校正
        }
        return episode

    def _extract_with_regex(self, html, cid, page_url, latest_order=0, item_type=None):
        """使用正则表达式提取（BeautifulSoup不可用时的备选方案）"""
        episodes = []
        seen_vids = set()

        list_html = html

        # 截取到推荐区域之前的内容
        recommend_markers = [
            r'<div[^>]*class="[^"]*mod-recommend',
            r'<div[^>]*class="[^"]*qy-player-side',
            r'<div[^>]*class="[^"]*side-wrap',
            r'<div[^>]*class="[^"]*m-iqycard-wrap',
            r'猜你喜欢',
            r'相关推荐',
            r'热门推荐',
        ]
        for marker in recommend_markers:
            match = re.search(marker, html)
            if match:
                list_html = html[:match.start()]
                break

        pattern = r"""href=['"]([^'"]*?/([va])_([^'"]+)\.html)"""
        matches = re.findall(pattern, list_html)

        for match in matches:
            full_url = match[0]
            url_type = match[1]
            vid = match[2]

            if vid == cid or vid in seen_vids:
                continue
            seen_vids.add(vid)

            if not full_url.startswith('http'):
                if full_url.startswith('//'):
                    full_url = f'https:{full_url}'
                elif full_url.startswith('/'):
                    full_url = f'https://www.iqiyi.com{full_url}'
                else:
                    full_url = f'https://www.iqiyi.com/{full_url}'

            title_match = re.search(rf"""href=['"]([^'"]*?/{url_type}_{vid}\.html)[^>]*>([^<]+)<""", list_html)
            title = title_match.group(2).strip() if title_match else ''

            # 如果标题为空，尝试从属性提取
            if not title:
                attr_match = re.search(rf"""href=['"]([^'"]*?/{url_type}_{vid}\.html)[^>]*title=['"]([^'"]+)""", list_html)
                if attr_match:
                    title = attr_match.group(2).strip()

            # 如果还是为空，使用集号作为标题
            if not title:
                title = f'第{len(episodes)+1}集'

            # 过滤时间格式标题（短视频时长）
            if re.match(r'^\d{1,2}:\d{2}', title.strip()):
                continue

            # 先按标题关键词判断类型：0=正片，1=预告，2=花絮
            episode_type = self._get_episode_type(title, item_type=item_type)

            # 提取集号（全部使用纯数字）
            if episode_type == 2:
                # 花絮用 seen_vids 当前长度作为顺序编号
                episode_num = f"{len(seen_vids)}"
            else:
                # 正片和预告正常提取集号
                episode_num = self._extract_episode_number(title, len(episodes) + 1)

            episodes.append({
                'episode_num': episode_num,
                'vid': vid,
                'play_title': title,
                'union_title': title,
                'episode_type': episode_type,  # 0=正片，1=预告，2=花絮
                'duration': '',
                'publish_date': '',
                'play_url': full_url,
                'is_vip': 0,  # 正则解析无法获取VIP信息，默认免费，由fetch_detail层统一校正
            })

        if episodes:
            episodes.sort(key=lambda x: self._episode_sort_key(x['episode_num']))

        return episodes

    # ==================== 判断方法 ====================

    @staticmethod
    def _extract_episode_number(title, default_num):
        """从标题提取集号

        支持格式：
        - 电视剧：第1集, 第01集, 1集
        - 综艺：第1期, 第1期上, 第1期下, 第1期加更
        - 通用：EP1, E1
        - 综艺日期期号：20250610期, -08-28期（回退到 default_num）
        """
        patterns = [
            r'第(\d+)\s*期\s*[上下来加]?',   # 第1期上, 第1期下, 第1期加更 → 取期号
            r'第(\d+)\s*[集话回弹]',          # 第1集, 第01集, 第2话, 第4回, 第5弹
            r'(\d+)\s*集',                    # 1集, 01集
            r'[Ee][Pp]\.?\s*(\d+)',           # EP1, EP01, ep.1
            r'[Ee](\d+)',                     # E1 (需在EP之后匹配，避免误匹配)
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        return str(default_num)

    @staticmethod
    def _episode_sort_key(episode_num):
        """分集排序键：数字集号在前，非数字在后"""
        if episode_num.isdigit():
            return (0, int(episode_num), '')
        else:
            num_match = re.search(r'\d+', episode_num)
            num = int(num_match.group()) if num_match else 0
            return (1, num, episode_num)

    # 正片标题必然包含的集数标识模式
    # 核心逻辑：正片标题一定会有"第X集"之类的集数标识，
    # contentType=1 但没有集数标识 → 不是正片，极可能是花絮
    _EPISODE_NUM_RE = re.compile(
        r'第\s*\d+\s*[集话期回弹]|'           # 第1集, 第01集, 第2话, 第3期, 第4回, 第5弹
        r'(?<!\d)\d{1,3}\s*[集话期回弹]|'     # 1集, 01集 (独立出现，不跟在前置数字后)
        r'[Ee][Pp]\.?\s*\d+|'                 # EP1, EP01, ep.1
        r'[Ee]pisode\s*\d+|'                  # Episode 1
        r'\d{6,8}\s*期|'                       # 20250610期 (综艺日期期号：YYYYMMDD期)
        r'-\d{2}-\d{2}\s*期'                   # -08-28期 (综艺短日期期号)
    )

    @classmethod
    def _has_episode_number(cls, title):
        """检查标题是否包含集数标识（正片标题的必要特征）"""
        if not title:
            return False
        return bool(cls._EPISODE_NUM_RE.search(title))

    def _get_episode_type(self, title, content_type=None, item_type=None):
        """
        判断剧集类型

        判断优先级（从高到低）：
        1. 专辑页 JSON 数据源 contentType：1=正片，3=预告 → 权威来源，直接采纳
        2. 预告关键词匹配 → 预告
        3. 花絮关键词匹配 → 花絮
           - 综艺例外：标题含期号标识时，"特辑"不算花絮（如"新春特辑第4期"是正片）
        4. 无集数标识 → 花絮（正片标题一定有"第X集"之类标识，无 contentType 时同样适用）
           - 但电影(item_type='movie')和综艺(item_type='variety')跳过此检查：
             电影标题不含集数标识是正常的；综艺期号格式多样（日期期号等），不应强制要求
        5. 默认 → 正片

        :param title: 标题
        :param content_type: 来自专辑页 JSON(epsodelist/updateprevuelist)或 API 的 contentType
                             1=正片, 3=预告/宣传内容
        :param item_type: 内容类型，如 'movie'/'variety'。电影和综艺场景跳过集数标识检查
        :return: 0=正片，1=预告，2=花絮
        """
        is_movie = item_type == 'movie'
        is_variety = item_type == 'variety'
        # 电影和综艺都跳过集数标识检查：电影标题不含"第X集"是正常的；
        # 综艺期号格式多样（日期期号如"20250610期"、短日期"-08-28期"等），
        # 且综艺的"加更版""纯享版"等虽无集数标识但仍是正片
        skip_episode_num_check = is_movie or is_variety

        if not title:
            return 0 if content_type != 3 else 1

        # contentType 权威判断（但需兼顾花絮关键词，因为 epsodelist 里也可能掺杂花絮）
        # contentType=3 → 预告/宣传内容（updateprevuelist 权威）
        # contentType=1 → 正片为主，但需检查标题是否命中花絮关键词（epsodelist 可能混入花絮）
        if content_type is not None:
            if content_type == 3:
                return 1  # 预告（updateprevuelist 里的全部视为预告）
            elif content_type == 1:
                # 正片标记，但仍需检查花絮关键词（epsodelist 可能把花絮也标为 contentType=1）
                # 综艺例外：标题含期号标识时，"特辑"不算花絮（如"新春特辑第4期"是正片）
                if self._is_bts_by_keywords(title, is_variety=is_variety):
                    return 2  # 花絮：标题命中花絮关键词，覆盖 contentType=1
                # 集数标识检查：正片标题必然有"第X集"等标识，没有则极可能是花絮
                # 但电影和综艺跳过此检查
                if not skip_episode_num_check and not self._has_episode_number(title):
                    logger.debug(f"集数过滤: contentType=1 但标题无集数标识，标记为花絮: {title}")
                    return 2
                return 0  # 正片
            # contentType 为其他值（如 2、4 等），不采纳，继续走关键词判断

        title_lower = title.lower()

        # 次优先级：预告关键词
        if any(kw in title_lower for kw in self._trailer_keywords):
            return 1

        # 花絮关键词（综艺例外：含期号标识时"特辑"不算花絮）
        if self._is_bts_by_keywords(title, is_variety=is_variety):
            return 2

        # 集数标识检查：无 contentType 时，没有集数标识 → 不是正片
        # 但电影和综艺跳过此检查
        if not skip_episode_num_check and not self._has_episode_number(title):
            logger.debug(f"集数过滤: 无contentType且标题无集数标识，标记为花絮: {title}")
            return 2

        # 默认正片
        return 0

    def _is_bts_by_keywords(self, title, is_variety=False):
        """
        检查标题是否命中花絮关键词。
        综艺例外：标题含期号标识时，"特辑"不算花絮（如"新春特辑第4期"实际是正片）。
        """
        title_lower = title.lower()
        if not any(kw in title_lower for kw in self._bts_keywords):
            return False
        # 综艺例外：标题含期号标识（第X期、X期、日期期号等）时，
        # "特辑"类关键词不算花絮（综艺的"新春特辑第4期"是正片）
        if is_variety and self._has_episode_number(title):
            # 只保留明确的花絮关键词（排除"特辑"、"特别篇"等综艺正片常用词）
            strict_bts_keywords = [kw for kw in self._bts_keywords
                                   if kw not in ('特辑', '特别篇', '策划', '企划')]
            return any(kw in title_lower for kw in strict_bts_keywords)
        return True

    def _deduplicate_episodes(self, episodes, latest_order=0, total_episodes=0):
        """
        去重逻辑：同一集号既有正片又有预告时，保留正片；只有预告的才保留预告

        处理流程：
        1. 按集号分组
        2. 每组内：优先保留正片(0)，其次预告(1)，最后花絮(2)
        3. 保留所有花絮内容
        4. 如果有 latest_order，对大于 latest_order 且类型不是花絮的，标记为预告
        """
        if not episodes:
            return episodes

        # 防止 latest_order 为 None（电影场景 baseinfo API 失败时会传入 None）
        latest_order = latest_order or 0
        total_episodes = total_episodes or 0

        # 先过滤掉明显不合理的链接
        filtered_eps = []
        max_expected_episode = total_episodes if total_episodes > 0 else (latest_order + 100 if latest_order > 0 else 200)
        for ep in episodes:
            ep_num = ep.get('episode_num', '')
            episode_type = ep.get('episode_type', 0)
            valid = False
            # 保留所有花絮，不管集号
            if episode_type == 2:
                valid = True
            # 保留所有预告
            elif episode_type == 1:
                valid = True
            elif ep_num.isdigit():
                ep_int = int(ep_num)
                # 只保留在合理范围内的数字集号
                if ep_int > 0 and ep_int <= max_expected_episode:
                    valid = True
            elif len(ep_num) < 15:
                # 非数字集号，但长度合理，也保留
                valid = True
            if valid:
                filtered_eps.append(ep)

        # 把花絮单独拿出来，不参与按集号去重
        bts_eps = [ep for ep in filtered_eps if ep.get('episode_type') == 2]
        non_bts_eps = [ep for ep in filtered_eps if ep.get('episode_type') != 2]

        # 按集号分组（非花絮内容）
        episodes_by_num = {}
        for ep in non_bts_eps:
            ep_num = ep.get('episode_num', '')
            if ep_num not in episodes_by_num:
                episodes_by_num[ep_num] = []
            episodes_by_num[ep_num].append(ep)

        result = []
        for ep_num, eps in episodes_by_num.items():
            # 按优先级排序：正片(0) > 预告(1)
            eps.sort(key=lambda x: x.get('episode_type', 1))

            # 优先保留正片
            main_eps = [ep for ep in eps if ep.get('episode_type') == 0]

            if main_eps:
                # 有正片，只保留正片
                result.extend(main_eps)
                if len(eps) > len(main_eps):
                    logger.info(f"集号 {ep_num}: 有 {len(main_eps)} 个正片和 {len(eps)-len(main_eps)} 个预告，保留正片")
            else:
                # 只有预告，保留预告
                result.extend(eps)
                logger.info(f"集号 {ep_num}: 只有 {len(eps)} 个预告，保留预告")

        # 把花絮加回来
        result.extend(bts_eps)

        # 按集号排序
        result.sort(key=lambda x: self._episode_sort_key(x['episode_num']))

        # 对 latest_order 之后的集号，如果类型不是花絮且不是正片，确保是预告
        if latest_order > 0:
            for ep in result:
                ep_num = ep.get('episode_num', '')
                episode_type = ep.get('episode_type', 0)
                if ep_num.isdigit() and int(ep_num) > latest_order:
                    # 只对非花絮内容强制标记
                    if episode_type != 2:
                        if episode_type != 1:
                            logger.info(f"集号 {ep_num} > latestOrder {latest_order}，强制标记为预告")
                            ep['episode_type'] = 1

        # 对于那些集号看起来不合理（大于 latest_order+20）的预告，重新分配合理的集号
        if latest_order > 0:
            # 先找出所有需要重新编号的内容（排除花絮）
            to_renumber = []
            other_eps = []

            for ep in result:
                ep_num = ep.get('episode_num', '')
                episode_type = ep.get('episode_type', 0)
                # 跳过花絮
                if episode_type == 2:
                    other_eps.append(ep)
                    continue

                if episode_type == 1 and ep_num.isdigit():
                    num = int(ep_num)
                    if num > latest_order + 20:
                        to_renumber.append(ep)
                    else:
                        other_eps.append(ep)
                else:
                    other_eps.append(ep)

            # 如果有需要重新编号的预告
            if to_renumber:
                # 找到当前最大的合理集号
                max_valid_num = latest_order
                for ep in other_eps:
                    ep_num = ep.get('episode_num', '')
                    episode_type = ep.get('episode_type', 0)
                    if episode_type == 2:
                        continue
                    if ep_num.isdigit():
                        num = int(ep_num)
                        if latest_order < num <= latest_order + 50:
                            if num > max_valid_num:
                                max_valid_num = num

                # 重新分配集号
                next_num = max_valid_num + 1
                for ep in to_renumber:
                    old_num = int(ep.get('episode_num', ''))
                    ep['episode_num'] = str(next_num)
                    logger.info(f"为预告重新分配集号: {old_num} -> {next_num}")
                    next_num += 1

                # 合并并重新排序
                result = other_eps + to_renumber
                result.sort(key=lambda x: self._episode_sort_key(x['episode_num']))

        return result

    def _scroll_page(self, page):
        """滚动页面加载更多分集"""
        try:
            page_height = page.evaluate('document.body.scrollHeight')
            scroll_step = page_height // 5
            for i in range(5):
                page.evaluate(f'window.scrollTo(0, {scroll_step * (i + 1)})')
                time.sleep(0.3)
            page.evaluate('window.scrollTo(0, 0)')
            time.sleep(0.5)
        except Exception as e:
            logger.debug(f"滚动失败: {e}")


# 单例
episode_extractor = IQiyiEpisodeExtractor()
