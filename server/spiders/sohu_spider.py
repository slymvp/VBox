
"""
搜狐视频爬虫实现
"""
import requests
import json
import re
import time
from core.base_spider import BaseSpider
from core.logger import setup_logger
from bs4 import BeautifulSoup

logger = setup_logger('vbox.sohu')


class SohuSpider(BaseSpider):
    """搜狐视频爬虫类"""

    def __init__(self, channel_config):
        super().__init__('搜狐视频', channel_config)
        
        # 从数据库配置直接读取 channel_key 和 url
        self.category_key = channel_config.get('channel_key', 'tv')
        channel_url = channel_config.get('url', 'https://tv.sohu.com/drama')
        # 搜狐综艺/少儿URL必须带尾部斜杠，否则302到404
        if self.category_key in ('variety', 'cartoon', 'child') and not channel_url.endswith('/'):
            channel_url += '/'
        self.channel_url = channel_url
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Referer': 'https://tv.sohu.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        self.timeout = 20
        
        logger.info(f"初始化搜狐爬虫: category={self.category_key}, url={self.channel_url}")

    def fetch_list_page(self, page=1, **kwargs):
        """
        获取列表页（搜狐用HTML页面，不是API）
        """
        try:
            # 搜狐列表页可能没有分页，或者用不同的方式
            url = self.channel_url
            logger.info(f"正在访问列表页: {url} (page={page})")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.encoding = 'GBK'  # 搜狐用GBK编码
            
            if response.status_code == 200:
                # 返回原始HTML字符串，在extract_items里解析
                return {'html': response.text, 'is_html': True, 'page': page}
            else:
                logger.error(f"访问失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取列表页异常: {e}", exc_info=True)
            return None

    def extract_items(self, data):
        """
        从HTML解析出视频列表
        """
        if not data or not data.get('is_html', False):
            return []
        
        html = data.get('html', '')
        if not html:
            return []
        
        results = []
        seen = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 搜狐不同频道使用不同的HTML结构：
            # 电视剧/电影: div.g-item
            # 动漫: div.g-item + div.g-item_double
            # 综艺/少儿: li.list-item
            items = []

            # 方式1: div.g-item（电视剧/电影/动漫）
            items.extend(soup.find_all('div', class_='g-item'))

            # 方式2: div.g-item_double（动漫双列布局）
            items.extend(soup.find_all('div', class_='g-item_double'))

            # 方式3: li.list-item（综艺/少儿）
            if not items:
                items = soup.find_all('li', class_='list-item')

            # 方式4: li.g-item
            if not items:
                items = soup.find_all('li', class_='g-item')

            # 方式5: 兜底 - 含data-vid的元素
            if not items:
                items = soup.find_all(attrs={'data-vid': True})

            logger.info(f"找到 {len(items)} 个候选元素")
            
            for item in items:
                try:
                    # 找链接
                    a_tag = item.find('a', class_='cover-link') or item.find('a')
                    if not a_tag:
                        continue
                    
                    href = a_tag.get('href', '')
                    if not href:
                        continue
                    
                    # 补全URL
                    if href.startswith('//'):
                        play_url = 'https:' + href
                    elif href.startswith('/'):
                        play_url = 'https://tv.sohu.com' + href
                    else:
                        play_url = href
                    
                    # 获取标题
                    title = a_tag.get('title', '').strip()
                    if not title:
                        title_tag = item.find('div', class_='item-title')
                        if title_tag:
                            title = title_tag.get_text().strip()
                    if not title or title in seen:
                        continue
                    
                    # 从item获取vid和plid
                    vid = item.get('data-vid', '') or ''
                    plid = item.get('data-plid', '') or ''

                    # 从链接里提取视频ID（搜狐URL格式: /v/BASE64.html 或 /v/数字.html）
                    url_vid = ''
                    match = re.search(r'v/([a-zA-Z0-9_/+=\-]+)\.html', href)
                    if match:
                        url_vid = match.group(1)

                    # cid优先级: data-vid > data-plid > URL中的视频ID
                    cid = vid or plid or url_vid

                    if not cid:
                        # 用标题的hash作为备选cid
                        import hashlib
                        cid = hashlib.md5(title.encode('utf-8')).hexdigest()

                    # first_vid: 优先用data-vid，其次用URL中的视频ID
                    first_vid = vid or url_vid or cid
                    
                    # 提取封面图
                    thumbnail = ''
                    img_tag = item.find('img')
                    if img_tag:
                        # 搜狐用的是 lazysrc 属性懒加载
                        thumbnail = img_tag.get('lazysrc', '') or img_tag.get('src', '') or img_tag.get('data-src', '')
                        if thumbnail.startswith('//'):
                            thumbnail = 'https:' + thumbnail
                    
                    result = {
                        'platform': 'sohu',
                        'cid': cid,
                        'title': title,
                        'first_vid': first_vid,
                        'vid': vid,
                        'playlist_id': plid,
                        'category_key': self.category_key,
                        'thumbnail': thumbnail,
                        'cover_url': thumbnail,
                        'url': play_url,
                        'play_url': play_url,
                    }
                    
                    results.append(result)
                    seen.add(title)
                    
                except Exception as e:
                    logger.debug(f"解析item异常: {e}")
                    continue
            
            logger.info(f"从列表页提取到 {len(results)} 条数据")
            return results
            
        except Exception as e:
            logger.error(f"解析HTML失败: {e}", exc_info=True)
            return []

    # ---- 搜狐 API 端点 ----
    VRS_VIDEOLIST_API = 'https://hot.vrs.sohu.com/vrs_videolist.action'
    PL_VIDEOLIST_API = 'https://pl.hd.sohu.com/videolist'

    @staticmethod
    def _extract_playlist_id(html: str) -> str:
        """从详情页 HTML 的 script 中提取 playlistId"""
        m = re.search(r'var\s+playlistId\s*=\s*[\'"](\d+)[\'"]', html)
        return m.group(1) if m else ''

    @staticmethod
    def _extract_episode_num(video_name: str) -> int:
        """从分集标题提取集号: \"太行谣第1集\" → 1"""
        if not video_name:
            return 0
        m = re.search(r'第\s*(\d+)\s*[集期话]', video_name)
        if m:
            return int(m.group(1))
        return 0

    @staticmethod
    def _parse_update_notification(text: str) -> tuple:
        """解析更新通知，返回 (total_episodes, is_finished)
        \"38集全\" → (38, 1), \"每晚24点更新\" → (0, -1), \"会员尊享全集\" → (0, 1)
        """
        if not text:
            return 0, 0
        # \"XX集全\" / \"共XX集\" / \"已完结\"
        m = re.search(r'(\d+)\s*集\s*全', text)
        if m:
            return int(m.group(1)), 1
        if '全' in text and '集' in text:
            return 0, 1
        if any(kw in text for kw in ['已完结', '完结', '全集']):
            return 0, 1
        # 连载中
        if any(kw in text for kw in ['更新', '连载', '每周', '每晚']):
            return 0, -1
        return 0, 0

    def _fetch_pl_metadata(self, playlist_id: str) -> dict:
        """从 pl API 获取剧集元数据"""
        try:
            resp = requests.get(self.PL_VIDEOLIST_API, params={'playlistid': playlist_id},
                               headers=self.headers, timeout=self.timeout)
            resp.encoding = 'GBK'
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f'pl API 请求失败 (playlistid={playlist_id}): {e}')
        return {}

    def _fetch_vrs_episodes(self, playlist_id: str) -> list:
        """从 vrs API 获取分集列表"""
        try:
            resp = requests.get(self.VRS_VIDEOLIST_API, params={'playlist_id': playlist_id},
                               headers=self.headers, timeout=self.timeout)
            resp.encoding = 'GBK'
            m = re.search(r'var\s+vrsvideolist\s*=\s*(\{.*)', resp.text, re.DOTALL)
            if m:
                vrs_data = json.loads(m.group(1))
                return vrs_data.get('videolist', [])
        except Exception as e:
            logger.warning(f'vrs API 请求失败 (playlist_id={playlist_id}): {e}')
        return []

    def fetch_detail(self, item: dict) -> None:
        """获取视频详情和分集"""
        play_url = item.get('play_url', '') or item.get('url', '')
        title = item.get('title', '')

        if not play_url:
            logger.warning(f'没有URL，跳过: {title}')
            return

        logger.info(f'获取详情: {title[:30]}')

        try:
            # 1. 从详情页 HTML 提取 playlistId
            playlist_id = ''
            response = requests.get(play_url, headers=self.headers, timeout=self.timeout)
            response.encoding = 'GBK'
            if response.status_code != 200:
                logger.warning(f'详情页访问失败: {response.status_code}')
                return

            html = response.text
            playlist_id = self._extract_playlist_id(html)

            # 2. 电影频道 fallback：HTML 中没有 playlistId，用列表页 data-plid
            if not playlist_id:
                playlist_id = item.get('playlist_id', '')
                if playlist_id:
                    logger.debug(f'  使用列表页 playlist_id: {playlist_id}')

            # 3. 从 pl API 获取元数据
            pl_data = {}
            if playlist_id:
                pl_data = self._fetch_pl_metadata(playlist_id)

            # 4. 从 vrs API 获取分集列表
            vrs_episodes_raw = []
            if playlist_id:
                vrs_episodes_raw = self._fetch_vrs_episodes(playlist_id)

            # ========== 解析元数据 ==========
            if pl_data:
                item['description'] = pl_data.get('albumDesc', '')
                item['area'] = pl_data.get('area', '')
                item['language'] = pl_data.get('language', '')
                item['year'] = pl_data.get('publishYear', '')

                # 演员
                actors = pl_data.get('mainActors', [])
                if actors:
                    item['actors'] = ','.join(actors)

                # 导演
                directors = pl_data.get('directors', [])
                if directors:
                    item['directors'] = ','.join(directors)

                # VIP 状态
                fee = int(pl_data.get('fee', 0) or 0)
                ppp = int(pl_data.get('isPaySeparately', 0) or 0)
                coupon = int(pl_data.get('isUseCoupons', 0) or 0)
                if fee:
                    item['is_vip'] = 1
                elif ppp or coupon:
                    item['is_vip'] = 2  # 点播
                else:
                    item['is_vip'] = 0

                # 总集数
                total_set = int(pl_data.get('totalSet', 0) or 0)
                update_set = int(pl_data.get('updateSet', 0) or 0)

                # 完结状态
                update_notif = pl_data.get('updateNotification', '')
                parsed_total, parsed_finish = self._parse_update_notification(update_notif)
                item['total_episodes'] = parsed_total or total_set or 1
                item['updated_episodes'] = update_set or len(vrs_episodes_raw)
                item['is_finished'] = parsed_finish or (
                    1 if total_set > 0 and update_set >= total_set else (-1 if update_notif else 0)
                )

                # 封面
                cover = pl_data.get('largeVerPicUrl', '') or pl_data.get('largePicUrl', '') or pl_data.get('pic170_110', '')
                if cover and not item.get('thumbnail'):
                    item['thumbnail'] = cover
                    item['cover_url'] = cover

            # ========== 解析分集 ==========
            if vrs_episodes_raw:
                # 电视剧/动漫/少儿：使用 vrs 分集数据
                episodes = []
                for ep in vrs_episodes_raw:
                    video_name = ep.get('videoName', '')
                    ep_num = int(ep.get('videoOrder', 0) or 0)
                    if not ep_num:
                        ep_num = self._extract_episode_num(video_name)

                    episodes.append({
                        'vid': str(ep.get('videoId', '')),
                        'episode_num': ep_num,
                        'play_title': video_name,
                        'union_title': ep.get('videoSubName', '') or '',
                        'episode_type': 0,  # 正片
                        'is_vip': item.get('is_vip', 0),
                        'duration': str(ep.get('playLength', '') or ''),
                        'publish_date': ep.get('videoShowDate', '') or '',
                        'play_url': ep.get('videoUrl', '') or '',
                    })

                # 按 episode_num 去重
                seen = set()
                deduped = []
                for ep in episodes:
                    key = (ep['episode_num'], ep['episode_type'])
                    if key not in seen and ep['vid']:
                        seen.add(key)
                        deduped.append(ep)
                episodes = deduped

                # 预告片（prevideos from pl API）
                trailer_eps = []
                if pl_data:
                    prevideos = pl_data.get('prevideos', [])
                    for pre in prevideos:
                        name = pre.get('name', '') or pre.get('episodeName', '')
                        trailer_eps.append({
                            'vid': str(pre.get('vid', '')),
                            'episode_num': 0,
                            'play_title': name,
                            'union_title': '',
                            'episode_type': 1,  # 预告
                            'is_vip': item.get('is_vip', 0),
                            'duration': str(pre.get('playLength', '') or ''),
                            'publish_date': pre.get('publishTime', '') or '',
                            'play_url': pre.get('pageUrl', '') or '',
                        })
                episodes.extend(trailer_eps)

            elif pl_data:
                # 电影频道：vrs 无数据，使用 pl API 的 videos 数组
                pl_videos = pl_data.get('videos', [])
                episodes = []
                for v in pl_videos:
                    episodes.append({
                        'vid': str(v.get('vid', '')),
                        'episode_num': int(v.get('order', 1) or 1),
                        'play_title': v.get('name', title),
                        'union_title': v.get('subName', '') or '',
                        'episode_type': 0,  # 正片
                        'is_vip': item.get('is_vip', 0),
                        'duration': str(v.get('playLength', '') or ''),
                        'publish_date': v.get('publishTime', '') or v.get('showDate', '') or '',
                        'play_url': v.get('pageUrl', play_url),
                    })

                # 预告
                prevideos = pl_data.get('prevideos', [])
                for pre in prevideos:
                    episodes.append({
                        'vid': str(pre.get('vid', '')),
                        'episode_num': 0,
                        'play_title': pre.get('name', '') or pre.get('episodeName', ''),
                        'union_title': '',
                        'episode_type': 1,
                        'is_vip': item.get('is_vip', 0),
                        'duration': str(pre.get('playLength', '') or ''),
                        'publish_date': pre.get('publishTime', '') or '',
                        'play_url': pre.get('pageUrl', '') or '',
                    })
            else:
                # 完全无法获取分集，回退到单集
                episodes = [{
                    'vid': item.get('vid', '') or item.get('cid', ''),
                    'episode_num': 1,
                    'play_title': title,
                    'union_title': title,
                    'episode_type': 0,
                    'is_vip': item.get('is_vip', 0),
                    'duration': '',
                    'publish_date': '',
                    'play_url': play_url,
                }]
                item['total_episodes'] = 1
                item['updated_episodes'] = 1

            item['episodes'] = episodes

            main_eps = [e for e in episodes if e['episode_type'] == 0]
            trailer_eps = [e for e in episodes if e['episode_type'] == 1]

            # first_vid
            if main_eps:
                item['first_vid'] = main_eps[0].get('vid', '')
                item['vid'] = main_eps[0].get('vid', '')

            # 如果没有 total_episodes，用正片数
            if not item.get('total_episodes') or item['total_episodes'] <= 1:
                if len(main_eps) > 1:
                    item['total_episodes'] = max(item.get('total_episodes', 0), len(main_eps))
            item['updated_episodes'] = max(item.get('updated_episodes', 0), len(main_eps))
            item['has_episodes'] = True

            logger.info(f'  ✓ {title[:25]}: {len(main_eps)}正片+{len(trailer_eps)}预告, '
                        f'is_vip={item.get("is_vip",0)}, total_ep={item.get("total_episodes",0)}, '
                        f'finished={item.get("is_finished",0)}')

        except Exception as e:
            logger.error(f'获取详情异常: {title[:30]} - {e}', exc_info=True)
