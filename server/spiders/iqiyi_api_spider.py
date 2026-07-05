"""
爱奇艺API爬虫
直接调用爱奇艺官方API获取剧集列表和分集数据
"""
import requests
import json
import re
from core.base_spider import BaseSpider
from core.logger import setup_logger
from spiders.iqiyi_episode_extractor import episode_extractor
from spiders.keywords import load_keywords

logger = setup_logger('vbox.iqiyi_api')


class IQiyiAPISpider(BaseSpider):
    """爱奇艺API爬虫类"""

    # 完结/连载关键词 fallback（优先使用平台配置的关键词）
    _FINISHED_FALLBACK = ['完结', '大结局', '全剧终', '最终话', '全', '全集']
    _ONGOING_FALLBACK = ['更新至', '连载', '更新中', '每周', '每日']

    def __init__(self, channel_config):
        super().__init__('爱奇艺', channel_config)
        # 反爬：动态构建完整请求头（带代理轮换）
        from core.anti_crawl import build_headers
        self.session = self.create_session()
        self.session.headers.update(build_headers(
            referer='https://www.iqiyi.com/',
            ua=self.get_user_agent(),
        ))
        self.headers = self.session.headers

        # 优先使用 main.py 注入的 category_key（最可靠），
        # 其次使用数据库 channel_key 字段，最后默认 tv
        self.category_key = channel_config.get('category_key') or channel_config.get('channel_key') or 'tv'
        CHANNEL_ID_MAP = {'tv': 2, 'movie': 1, 'variety': 6, 'cartoon': 4, 'child': 15}
        self.channel_id = CHANNEL_ID_MAP.get(self.category_key, 2)

        # sort: 'hot' = 热门列表, 'new' = 最新列表, ''/None = 默认（不刷标记）
        sort_val = str(channel_config.get('sort', '') or '')
        self._list_type = sort_val if sort_val in ('hot', 'new') else ''

        # 加载完结/连载关键词
        self._finished_keywords = load_keywords('iqiyi', 'finish', self._FINISHED_FALLBACK)
        self._ongoing_keywords = load_keywords('iqiyi', 'ongoing', self._ONGOING_FALLBACK)

    def _get_total_pages(self, first_page_data, max_items, first_page_count):
        """重写：利用爱奇艺API返回的总数计算页数"""
        try:
            data = first_page_data.get('data', {})
            # 爱奇艺API返回 total 字段表示总条数
            total = data.get('total', 0)
            if total > 0:
                page_size = 30  # 与fetch_list_page中的page_size一致
                total_pages = (total + page_size - 1) // page_size
                # 如果指定了max_items，限制页数
                if max_items is not None:
                    needed_pages = (max_items + page_size - 1) // page_size
                    total_pages = min(total_pages, needed_pages)
                logger.info(f'API返回总数: {total}, 总页数: {total_pages}')
                return total_pages
        except Exception as e:
            logger.debug(f'解析API总数失败: {e}')
        # 回退到默认实现
        return super()._get_total_pages(first_page_data, max_items, first_page_count)

    def fetch_list_page(self, page=1, **kwargs):
        """
        通过API获取剧集列表
        API端点：爱奇艺PCW API
        """
        try:
            # 使用爱奇艺官方API
            url = 'https://pcw-api.iqiyi.com/search/recommend/list'

            params = {
                'channel_id': self.channel_id,
                'data_type': '1',
                'mode': '1',
                'page_size': '30',
                'page_num': str(page),
                'filter_info': '',
            }

            logger.info(f"请求API: 第{page}页")
            response = self.session.get(url, params=params, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"API请求失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"API请求异常: {e}")
            return None

    def extract_items(self, api_data):
        """从API响应中提取剧集列表项"""
        if not api_data:
            return []

        results = []
        seen = set()

        try:
            # API返回结构
            data_list = api_data.get('data', {}).get('list', [])

            for item in data_list:
                # 提取基本信息
                title = item.get('name', '').strip()
                if not title or title in seen:
                    continue

                # 提取albumId（用于后续获取分集），确保转为字符串
                album_id = str(item.get('albumId', '') or item.get('album_id', ''))
                if not album_id:
                    continue

                # 提取vid（视频ID，用于构建播放URL）
                vid = str(item.get('tvId', '') or item.get('vid', '') or '')

                # 构建URL - 优先使用API返回的playUrl
                play_url = item.get('playUrl', '')

                # 从 playUrl 提取稳定的字符串 album ID（如 /a_131ig5wtqg5.html）
                # 避免 cid 在 extract_items 和 fetch_detail 之间不一致
                album_str_id_from_url = ''
                if play_url:
                    m = re.search(r'/a_([^.]+)\.html', play_url)
                    if m:
                        album_str_id_from_url = m.group(1)

                if not play_url:
                    if vid:
                        play_url = f'https://www.iqiyi.com/v_{vid}.html'
                    else:
                        play_url = f'https://www.iqiyi.com/a_{album_id}.html'

                # 优先用字符串 ID 作为 cid（稳定性更高）
                stable_cid = album_str_id_from_url or album_id

                # 提取其他信息
                # year: 列表API不直接提供 year 字段，但 period 字段有完整日期（如 "2026-05-27"）
                period = item.get('period', '')
                year = item.get('year', '') or (period[:4] if period and len(period) >= 4 else '')
                score = item.get('score', '')
                area = item.get('area', '')
                description = item.get('description', '')

                # 封面图
                image = item.get('imageUrl', '') or item.get('image_url', '')

                # 标签（从categories提取）
                categories = item.get('categories', [])
                tags = []
                if categories and isinstance(categories, list):
                    for c in categories:
                        if isinstance(c, dict):
                            tag_name = c.get('name', '')
                            if tag_name:
                                tags.append(tag_name)
                        elif isinstance(c, str):
                            tags.append(c)

                # 演员列表（从 people.main_charactor 提取）
                people = item.get('people', {})
                actors = ''
                if isinstance(people, dict):
                    main_actors = people.get('main_charactor', [])
                    if main_actors and isinstance(main_actors, list):
                        actor_names = [p.get('name', '') for p in main_actors
                                       if isinstance(p, dict) and p.get('name')]
                        if actor_names:
                            actors = json.dumps(actor_names, ensure_ascii=False)

                # area 推断：列表API不返回 area 字段
                # 优先从 categories 的语言标签推断，其次从演员名字的间隔号推断
                if not area:
                    area = self._infer_area_from_categories_and_actors(tags, actors)

                # 封面URL（列表阶段暂用原始imageUrl，详情阶段会用headImage替换）
                cover_url = image

                # 使用 category_key 作为 item_type（与频道映射一致）
                item_type = self.category_key

                # 列表页VIP标识（详情页会进一步校正）
                is_vip = 1 if str(item.get('payMark', 0)) == '1' else 0

                result = {
                    'platform': 'iqiyi',
                    'cid': stable_cid,        # 优先使用字符串ID，确保cid稳定
                    'title': title,
                    'url': play_url,
                    'vid': vid or album_id,  # 优先使用tvId，没有则用albumId
                    'album_id': album_id,     # albumId专门用于分集API
                    'category_key': self.category_key,
                    'thumbnail': image,
                    'cover_url': cover_url,
                    'year': year,
                    'score': score,
                    'area': area,
                    'tags': tags,
                    'actors': actors,
                    'description': description,
                    'is_vip': is_vip,
                    'is_hot': 1 if self._list_type == 'hot' else 0,
                    'is_new': 1 if self._list_type == 'new' else 0,
                }

                results.append(result)
                seen.add(title)

            logger.info(f"从API提取到 {len(results)} 个剧集")
            return results

        except Exception as e:
            logger.error(f"解析API数据失败: {e}")
            return []

    def fetch_detail(self, item):
        """
        获取剧集详情和分集信息
        只填充 item 数据，不直接保存到数据库（由调度层统一保存）
        """
        try:
            url = item.get('url', '')
            # album_id 是数字ID，用于 API 调用；cid 可能已是字符串ID
            album_id = str(item.get('album_id', '') or item.get('vid', ''))
            existing_cid = item.get('cid', '')

            if not url and not album_id and not existing_cid:
                logger.warning(f"缺少URL或albumId: {item.get('title')}")
                return

            logger.info(f"获取详情: {item.get('title')} - albumId={album_id}, cid={existing_cid}")

            # 通过baseinfo API获取专辑详细信息（字符串ID + 元数据）
            album_str_id, baseinfo = self._get_album_info(album_id)
            if album_str_id:
                item['cid'] = album_str_id
                # 更新URL为专辑页URL，确保分集链接正确
                item['url'] = f'https://www.iqiyi.com/a_{album_str_id}.html'
            elif not existing_cid:
                # 回退：使用原始albumId作为cid（仅当cid为空时）
                item['cid'] = album_id

            # 从baseinfo补充缺失字段
            if baseinfo:
                # 地区
                if not item.get('area'):
                    item['area'] = self._extract_area(baseinfo)
                # 地区推断（baseinfo有area但区域字段仍为空时用baseinfo）
                if not item.get('area') and baseinfo.get('areas'):
                    item['area'] = self._extract_area(baseinfo)
                # 年份
                if not item.get('year'):
                    item['year'] = self._extract_year(baseinfo)
                # 标签：空列表视为未填充，尝试从baseinfo补充
                existing_tags = item.get('tags', [])
                if not existing_tags:
                    item['tags'] = self._extract_tags(baseinfo)
                # 高清封面URL（详情页大图）
                item['cover_url'] = self._extract_cover_url(baseinfo)
                # 演员列表
                if not item.get('actors'):
                    item['actors'] = self._extract_actors(baseinfo)
                # 演员提取后再做area推断兜底（baseinfo来源的actors也可参与推断）
                if not item.get('area') and item.get('actors'):
                    item['area'] = self._infer_area_from_categories_and_actors(
                        item.get('tags', []) if isinstance(item.get('tags'), list) else [],
                        item.get('actors', '')
                    )
                # 评分（baseinfo的score更准确）
                score = baseinfo.get('score', 0)
                if score and not item.get('score'):
                    item['score'] = score
                # 缩略图保持原始尺寸（爱奇艺不支持随意替换尺寸后缀，替换后404）
                # 总集数和已更新集数（baseinfo的videoCount/latestOrder最准确）
                video_count = baseinfo.get('videoCount', 0)
                latest_order = baseinfo.get('latestOrder', 0)
                if video_count:
                    item['total_episodes'] = video_count
                if latest_order:
                    item['updated_episodes'] = latest_order

            # baseinfo不可用（如电影）时，用搜索API补充标签和图片
            # 电影场景：baseinfo API返回A00001，无法获取headImages横版大图
            # 搜索API返回albumHImage（横版）→cover_url, albumVImage（竖版）→thumbnail
            existing_tags = item.get('tags', [])
            item_type = self.category_key
            need_search = (not existing_tags
                           or (item_type == 'movie' and item.get('cover_url') == item.get('thumbnail')))
            if need_search:
                search_result = self._fetch_tags_from_search(item.get('title', ''), album_id=album_id)
                if search_result['tags']:
                    item['tags'] = search_result['tags']
                    # 标签补充后再做area推断兜底
                    if not item.get('area') and (item.get('actors') or search_result.get('actors')):
                        item['area'] = self._infer_area_from_categories_and_actors(
                            search_result['tags'], item.get('actors') or search_result.get('actors', '')
                        )
                # 搜索API的演员数据 → actors（电影场景：baseinfo不可用，list API演员可能不全）
                if not item.get('actors') and search_result.get('actors'):
                    item['actors'] = search_result['actors']
                # 搜索API的横版大图 → cover_url（替代与thumbnail重复的imageUrl）
                if search_result['cover_url']:
                    item['cover_url'] = search_result['cover_url']
                # 搜索API的竖版图 → thumbnail（可能比列表API的imageUrl更清晰）
                if search_result['thumbnail']:
                    item['thumbnail'] = search_result['thumbnail']

            # 使用分集提取器获取真实分集数据
            # 传入album_str_id避免extract_episodes内部重复请求baseinfo API
            # 传入集数信息用于判断是否完结（已完结不需要补充预告）
            # 传入item_type让分集提取器知道内容类型（电影场景跳过集数标识检查）
            episodes = episode_extractor.extract_episodes(
                album_id, url, album_str_id=album_str_id,
                total_episodes=item.get('total_episodes', 0),
                updated_episodes=item.get('updated_episodes', 0),
                item_type=self.category_key
            )
            if episodes:
                # 整剧VIP标识：优先从baseinfo提取，
                # 若为0则回退从分集is_vip聚合判断（电影场景baseinfo常缺失VIP标识）
                series_is_vip = self._extract_is_vip(baseinfo)
                if not series_is_vip:
                    # 回退：只要任一正片分集的 is_vip > 0，整剧即为 VIP
                    for ep in episodes:
                        if ep.get('episode_type') == 0 and ep.get('is_vip', 0) > 0:
                            series_is_vip = 1
                            break

                # 根据整剧VIP状态统一设置分集is_vip
                for ep in episodes:
                    ep['is_vip'] = series_is_vip  # 全部先按整剧级别赋值

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
                item['is_vip'] = series_is_vip
                # 区分正片、预告和花絮计数
                main_eps = [ep for ep in episodes if ep.get('episode_type') == 0]
                trailer_eps = [ep for ep in episodes if ep.get('episode_type') == 1]
                bts_eps = [ep for ep in episodes if ep.get('episode_type') == 2]
                # 如果baseinfo没有提供集数信息，则用实际爬取的正片数
                # 确保 total_episodes >= updated_episodes（实际正片数）
                if not item.get('total_episodes'):
                    item['total_episodes'] = len(main_eps)
                elif item['total_episodes'] < len(main_eps):
                    item['total_episodes'] = len(main_eps)
                # updated_episodes 始终用实际入库的正片数，保证与DB中episodes数据一致
                item['updated_episodes'] = len(main_eps)
                item['has_episodes'] = True

                # 判断完结状态
                from core.finished_judge import judge
                # 爱奇艺 baseinfo.isFinish 字段
                api_finished = 0
                if baseinfo:
                    is_finish_val = baseinfo.get('isFinish', None)
                    if is_finish_val == 1:
                        api_finished = 1
                    elif is_finish_val == 0:
                        api_finished = -1
                item['is_finished'] = judge(
                    api_finished=api_finished,
                    total_episodes=item.get('total_episodes', 0),
                    main_count=len(main_eps),
                    trailer_count=len(trailer_eps),
                    category_key=self.category_key,
                )
                logger.info(f"提取到 {len(episodes)} 集（正片{len(main_eps)}集，预告{len(trailer_eps)}集，花絮{len(bts_eps)}集），总{item['total_episodes']}集，更新至{item['updated_episodes']}集，VIP={item['is_vip']}，完结={item['is_finished']}")
            else:
                # 电影兜底：电影只有1集正片，当所有分集提取方法都失败时，
                # 用 playUrl 中的 vid 构造1集正片（电影本质就只有1集）
                if self.category_key == 'movie' and item.get('url'):
                    movie_vid = ''
                    play_url = item.get('url', '')
                    v_match = re.search(r'v_([^.]+)\.html', play_url)
                    if v_match:
                        movie_vid = v_match.group(1)
                    if not movie_vid:
                        movie_vid = item.get('vid', '') or album_id
                    item['episodes'] = [{
                        'episode_num': '1',
                        'vid': movie_vid,
                        'play_title': item.get('title', ''),
                        'union_title': item.get('title', ''),
                        'episode_type': 0,
                        'duration': '',
                        'publish_date': '',
                        'play_url': play_url,
                        'is_vip': self._extract_is_vip(baseinfo),
                    }]
                    item['total_episodes'] = 1
                    item['updated_episodes'] = 1
                    item['has_episodes'] = True
                    item['is_finished'] = 1  # 电影只有1集，视为完结
                    logger.info(f"电影兜底：构造1集正片 vid={movie_vid}")
                else:
                    item['has_episodes'] = False
                    if not item.get('total_episodes'):
                        item['total_episodes'] = 0
                    if not item.get('updated_episodes'):
                        item['updated_episodes'] = 0
                    item['is_finished'] = 0  # 无法获取分集，状态未知

            # 电影场景：尝试获取横版大图封面
            # 策略：搜索API已有cover_url则接受（作为基础图），同时尝试获取更好的大图
            # 只有完全没有封面时才强制触发额外提取
            item_type = self.category_key
            cover_url = item.get('cover_url', '') or ''
            if item_type == 'movie':
                # 第一步：尝试轻量图片API（vrsAlbumPicInfo等），获取横版大图
                api_cover = self._fetch_movie_cover(album_id, tv_id=item.get('vid', ''))
                if api_cover:
                    item['cover_url'] = api_cover
                    logger.info(f"图片API提取电影封面图: {item.get('title', '')} -> {api_cover[:80]}")
                elif not cover_url:
                    # 第二步：API失败且完全没有封面时才用Playwright
                    movie_url = item.get('url', '')
                    if movie_url:
                        pw_cover = episode_extractor.extract_cover_url(movie_url)
                        if pw_cover:
                            item['cover_url'] = pw_cover
                            logger.info(f"Playwright提取电影封面图: {item.get('title', '')} -> {pw_cover[:80]}")
                # 有搜索API封面但API大图失败：保留搜索API的cover_url（够用）

        except Exception as e:
            logger.error(f"详情获取失败: {item.get('title', '未知')}, 错误: {e}", exc_info=True)

    def _get_album_info(self, album_id):
        """
        通过album/baseinfo API获取专辑详细信息
        返回 (album_str_id, baseinfo_data) 元组：
        - album_str_id: 专辑页字符串ID(如131ig5wtqg5)，用作稳定的cid
        - baseinfo_data: baseinfo完整数据，用于提取area/year/tags/cover_url等
        """
        try:
            baseinfo_url = f'https://pcw-api.iqiyi.com/album/album/baseinfo/{album_id}'
            resp = self.session.get(baseinfo_url, timeout=15)
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            if data.get('code') != 'A00000':
                return None, None
            baseinfo = data.get('data', {})
            if not isinstance(baseinfo, dict):
                return None, None

            # 提取专辑页字符串ID
            album_str_id = None
            album_url = baseinfo.get('url', '')
            if album_url:
                match = re.search(r'/a_([^.]+)\.html', album_url)
                if match:
                    album_str_id = match.group(1)

            return album_str_id, baseinfo
        except Exception as e:
            logger.debug(f"baseinfo API请求失败: {e}")
            return None, None

    @staticmethod
    def _extract_area(baseinfo):
        """从baseinfo提取地区信息"""
        areas = baseinfo.get('areas', [])
        if areas and isinstance(areas, list):
            # areas可能是 [{name: "中国大陆"}] 或 ["中国大陆"]
            names = []
            for a in areas:
                if isinstance(a, dict):
                    names.append(a.get('name', ''))
                elif isinstance(a, str):
                    names.append(a)
            return ','.join(n for n in names if n)
        return ''

    @staticmethod
    def _extract_year(baseinfo):
        """从baseinfo提取年份（从period字段如2026-05-27中取前4位）"""
        period = baseinfo.get('period', '')
        if period and len(period) >= 4:
            return period[:4]
        return ''

    @staticmethod
    def _extract_tags(baseinfo):
        """从baseinfo提取标签（从categories字段）"""
        categories = baseinfo.get('categories', [])
        if categories and isinstance(categories, list):
            tags = []
            for c in categories:
                if isinstance(c, dict):
                    name = c.get('name', '')
                    if name:
                        tags.append(name)
                elif isinstance(c, str):
                    tags.append(c)
            return tags
        return []

    @staticmethod
    def _extract_cover_url(baseinfo):
        """
        从baseinfo提取高清封面URL
        优先使用headImages（横版大图），回退使用升级后的imageUrl
        """
        # 优先使用headImages（通常是横版大图，适合详情页封面）
        head_images = baseinfo.get('headImages', [])
        if head_images and isinstance(head_images, list):
            for hi in head_images:
                if isinstance(hi, dict):
                    src = hi.get('src', '')
                    if src:
                        return src
        # 回退：使用原始imageUrl（爱奇艺不支持替换尺寸后缀）
        image_url = baseinfo.get('imageUrl', '')
        if image_url:
            return image_url
        return ''

    @staticmethod
    def _extract_is_vip(baseinfo):
        """从baseinfo提取整剧VIP标识
        爱奇艺baseinfo中payMark=1表示付费，exclusive=1表示独播（通常也是VIP）
        """
        if not baseinfo or not isinstance(baseinfo, dict):
            return 0
        pay_mark = baseinfo.get('payMark', 0)
        if pay_mark and str(pay_mark) == '1':
            return 1
        exclusive = baseinfo.get('exclusive', 0)
        if exclusive and str(exclusive) == '1':
            return 1
        return 0

    @staticmethod
    def _extract_actors(baseinfo):
        """从baseinfo提取演员列表"""
        people = baseinfo.get('people', {})
        if not people or not isinstance(people, dict):
            return ''
        main_actors = people.get('main_charactor', [])
        if main_actors and isinstance(main_actors, list):
            names = [p.get('name', '') for p in main_actors if isinstance(p, dict) and p.get('name')]
            if names:
                return json.dumps(names, ensure_ascii=False)
        return ''

    @staticmethod
    def _infer_area_from_categories_and_actors(tags: list, actors: str) -> str:
        """
        当 area 字段为空时，从 categories 标签和演员名字推断地区。

        推断逻辑：
        1. 优先从 categories 语言标签推断（更精准）
           - '普通话' / '国语' / '华语' → 中国大陆
           - '粤语' → 中国香港
           - '韩语' → 韩国
           - '日语' → 日本
        2. 若无语言标签，从演员名中的间隔号（·）判断
           - 含间隔号（外国人名译法如"杰拉德·巴特勒"）占多数 → 欧美
           - 无间隔号的中文名占多数 → 中国大陆
        """
        # 语言→地区映射
        LANG_AREA_MAP = {
            '普通话': '中国大陆', '国语': '中国大陆', '华语': '中国大陆',
            '粤语': '中国香港',
            '韩语': '韩国',
            '日语': '日本',
        }

        # 1. 优先从语言标签推断
        for tag in tags:
            if tag in LANG_AREA_MAP:
                return LANG_AREA_MAP[tag]

        # 2. 从演员名推断
        if not actors:
            return ''

        try:
            actor_list = json.loads(actors) if isinstance(actors, str) else actors
        except Exception:
            return ''

        if not actor_list:
            return ''

        # 含间隔号（·）的名字判定为外国人名译名
        foreign_count = sum(1 for a in actor_list if '·' in a or '\u00b7' in a)
        total = len(actor_list)

        if total == 0:
            return ''
        # 超过半数是外国名 → 欧美
        if foreign_count > total / 2:
            return '欧美'
        # 全部是中文名 → 中国大陆
        if foreign_count == 0:
            return '中国大陆'
        # 混合（配音版等）→ 留空，不强制推断
        return ''

    def _fetch_tags_from_search(self, title, album_id=None):
        """
        通过搜索API获取标签和图片（兜底方案）。
        当列表API categories 为空且 baseinfo 不可用（如电影）时，
        使用搜索API的 three_category_v2_info 字段获取标签，
        同时从 albumHImage/albumVImage 获取横版/竖版图片。
        返回 dict: {"tags": [...], "cover_url": "...", "thumbnail": "..."}
        - cover_url: albumHImage 横版大图（适合详情页封面）
        - thumbnail: albumVImage 竖版海报图（适合列表缩略图）
        """
        result = {"tags": [], "cover_url": None, "thumbnail": None, "actors": ""}
        if not title:
            return result
        try:
            resp = self.session.get(
                'https://search.video.iqiyi.com/o',
                params={'if': 'html5', 'key': title, 'pageNum': 1, 'pageSize': 5},
                timeout=10,
            )
            data = resp.json()
            items = data.get('data', {}).get('docinfos', [])
            for item in items:
                info = item.get('albumDocInfo', {})
                info_title = info.get('title', '')
                info_album_id = str(info.get('albumId', ''))

                # 匹配逻辑：标题精确/包含匹配，或 albumId 匹配
                # 注意：搜索API返回的title可能为空，但albumId通常有值
                matched = False
                if info_title and (info_title == title or title in info_title or info_title in title):
                    matched = True
                elif album_id and info_album_id and info_album_id == str(album_id):
                    matched = True

                if not matched:
                    continue

                # 提取图片（albumHImage=横版大图→cover_url, albumVImage=竖版→thumbnail）
                if not result['cover_url']:
                    album_h = info.get('albumHImage', '')
                    if album_h:
                        result['cover_url'] = album_h
                if not result['thumbnail']:
                    album_v = info.get('albumVImage', '')
                    if album_v:
                        result['thumbnail'] = album_v

                # 优先从 three_category_v2_info（结构化数据）提取标签
                if not result['tags']:
                    category_info = info.get('three_category_v2_info', [])
                    if category_info and isinstance(category_info, list):
                        tags = []
                        for cat in category_info:
                            if isinstance(cat, dict):
                                name = cat.get('name', '')
                                # 优先取核心标签(is_key_tag)
                                if name and cat.get('is_key_tag'):
                                    tags.append(name)
                        # 如果核心标签不足3个，补充非核心的类型标签
                        if len(tags) < 3:
                            for cat in category_info:
                                if isinstance(cat, dict):
                                    name = cat.get('name', '')
                                    root = cat.get('root_name', '')
                                    if name and name not in tags and root == '类型':
                                        tags.append(name)
                                        if len(tags) >= 5:
                                            break
                        if tags:
                            result['tags'] = tags[:5]

                # 回退：从 three_category_v2 字符串解析标签
                if not result['tags']:
                    cat_str = info.get('three_category_v2', '')
                    if cat_str and isinstance(cat_str, str):
                        parts = [p.strip() for p in cat_str.split(',') if p.strip()]
                        # 取前5个作为标签
                        if parts:
                            result['tags'] = parts[:5]

                # 提取演员（从star/people字段，电影场景补充更多演员）
                if not result['actors']:
                    actor_names = []
                    # 从star字段提取
                    star = info.get('star', [])
                    if star and isinstance(star, list):
                        actor_names = [s.get('name', '') for s in star if isinstance(s, dict) and s.get('name')]
                    # 从people字段补充更多演员
                    if len(actor_names) < 5:
                        people = info.get('people', {})
                        if isinstance(people, dict):
                            for key in ['main_charactor', 'actor', 'guest_actor', 'supporting_charactor']:
                                vals = people.get(key, [])
                                if vals and isinstance(vals, list):
                                    actor_names.extend([p.get('name', '') for p in vals if isinstance(p, dict) and p.get('name')])
                                    if len(actor_names) >= 15:
                                        break
                        # 去重保持顺序
                        seen = set()
                        unique = []
                        for n in actor_names:
                            if n and n not in seen:
                                seen.add(n)
                                unique.append(n)
                        actor_names = unique
                    if actor_names:
                        result['actors'] = json.dumps(actor_names[:15], ensure_ascii=False)

                # 标签和图片都有了，提前返回
                if result['tags'] and result['cover_url'] and result['thumbnail']:
                    break

            if result['tags']:
                logger.info(f"从搜索API补充标签: {title} -> {result['tags']}")
            if result['cover_url']:
                logger.info(f"从搜索API补充封面: {title} -> cover_url")
            if result['thumbnail']:
                logger.info(f"从搜索API补充缩略图: {title} -> thumbnail")
            return result
        except Exception as e:
            logger.debug(f"搜索API获取标签失败: {e}")
            return result

    def _fetch_movie_cover(self, album_id, tv_id=''):
        """
        通过 playervideoinfo 接口获取电影封面 URL。
        返回 str 或 None。

        调查结论（2026-05-30）：
        - vrsAlbumPicInfo API 已 404 废弃
        - meta.video.iqiyi.com 已 405 废弃
        - 搜索API的 albumHImage/albumVImage 实际是同一张 120×160 竖版小图
        - playervideoinfo 接口的字段含义：
            apic/vpic: 当前封面图（通常是竖版小图）
            preImageUrl(m_624): 横版大图，在 preimage 域名下，但部分电影 404
            previewImageUrl(m_611): 横版预览图，同样在 preimage 域名下
        - 策略：preImageUrl → 尝试换为 pic 域名（部分可用）→ previewImageUrl → apic（兜底）

        tv_id 和 album_id 对于电影来说是同一个值（qipuId）。
        """
        # tv_id 和 album_id 对于电影是同一个值，取不为空的那个
        qipu_id = tv_id or album_id
        if not qipu_id:
            return None

        try:
            url = (f'https://mesh.if.iqiyi.com/player/pcw/video/playervideoinfo'
                   f'?id={qipu_id}&locale=zh_cn')
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                logger.debug(f"playervideoinfo HTTP {resp.status_code}: qipuId={qipu_id}")
                return None
            data = resp.json()
            if data.get('code') != 'A00000':
                logger.debug(f"playervideoinfo 非成功: {data.get('code')} {data.get('msg')}")
                return None
            d = data.get('data', {})

            # 优先级1: preImageUrl（横版大图，m_624 格式）
            # 在 preimage 域名下可能 404，尝试转换为 pic 域名
            pre_image_url = d.get('preImageUrl', '')
            if pre_image_url:
                pic_url = self._preimage_to_pic(pre_image_url)
                if pic_url and self._url_exists(pic_url):
                    logger.info(f"playervideoinfo preImageUrl(pic域名): {d.get('vn')} -> {pic_url[:80]}")
                    return pic_url
                # preimage 域名原始 URL
                if self._url_exists(pre_image_url):
                    logger.info(f"playervideoinfo preImageUrl(preimage域名): {d.get('vn')} -> {pre_image_url[:80]}")
                    return pre_image_url

            # 优先级2: previewImageUrl（横版预览图，m_611 格式）
            preview_url = d.get('previewImageUrl', '')
            if preview_url:
                pic_url = self._preimage_to_pic(preview_url)
                if pic_url and self._url_exists(pic_url):
                    logger.info(f"playervideoinfo previewImageUrl(pic域名): {d.get('vn')} -> {pic_url[:80]}")
                    return pic_url
                if self._url_exists(preview_url):
                    logger.info(f"playervideoinfo previewImageUrl(preimage域名): {d.get('vn')} -> {preview_url[:80]}")
                    return preview_url

            # 优先级3: apic（当前封面图，通常是竖版小图，但总是存在的）
            apic = d.get('apic', '') or d.get('vpic', '')
            if apic:
                logger.info(f"playervideoinfo apic(兜底): {d.get('vn')} -> {apic[:80]}")
                return apic

        except Exception as e:
            logger.debug(f"playervideoinfo 封面提取失败: qipuId={qipu_id}, 错误: {e}")

        return None

    @staticmethod
    def _preimage_to_pic(preimage_url):
        """
        将 preimage 域名的 URL 转换为 pic 域名，并将路径中的 /preimage/ 换为 /image/。
        例如：
          preimage1.iqiyipic.com/preimage/20230907/... → pic1.iqiyipic.com/image/20230907/...
        返回转换后的 URL，若无法识别则返回 None。
        """
        converted = re.sub(
            r'https?://preimage(\d*)\.iqiyipic\.com/preimage/',
            lambda m: f'https://pic{m.group(1)}.iqiyipic.com/image/',
            preimage_url
        )
        if converted != preimage_url:
            return converted
        return None

    def _url_exists(self, url):
        """HEAD 请求检查 URL 是否存在（HTTP 200）"""
        try:
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False

