"""
腾讯视频爬虫基类
提供通用的API调用和数据提取方法
优化点：
1. 列表页/详情页请求加重试机制（使用RetryHelper）
2. 翻页间隔从0.5s降到0.3s
3. 合并_extract_from_card中重复的card_type判断
4. 分集请求也加重试
5. 裸except改为Exception
6. 提取_request_with_retry统一请求封装
"""
import requests
import json
import re
import time
from core.base_spider import BaseSpider
from core.logger import setup_logger
from core.retry import RetryHelper
from spiders.keywords import load_keywords

logger = setup_logger('vbox.tencent')


class TencentBaseSpider(BaseSpider):
    """腾讯视频爬虫基类"""

    MVL_API = 'https://pbaccess.video.qq.com/trpc.multi_vector_layout.mvl_controller.MVLPageHTTPService/getMVLPage?vversion_platform=2'
    GETPAGE_API = 'https://pbaccess.video.qq.com/trpc.vector_layout.page_view.PageService/getPage?vdevice_guid=e217cf57e9a4e187&video_appid=3000010&vversion_platform=2'

    HEADERS = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Origin': 'https://v.qq.com',
        'Referer': 'https://v.qq.com/',
    }

    # 关键词 fallback：AdminPlatform 未配置时使用
    _TRAILER_FALLBACK = [
        '预告', 'trailer', 'teaser', '先导', '前瞻', '片花',
        '抢先看', '抢先版', '预告片',
    ]
    _VIP_FALLBACK = [
        'VIP', '云首发', '用券', '付费', '会员', 'pay', 'need_pay',
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
    _FINISHED_FALLBACK = ['完结', '大结局', '全剧终', '最终话', '全集']
    _ONGOING_FALLBACK = ['更新至', '连载', '更新中', '每周', '每日']

    # 需要提取params的card类型集合
    _PARAMS_CARD_TYPES = {'searchlist_poster_card', 'video_card', 'poster_card'}

    def __init__(self, platform_name, channel_config, channel_id, category_key='tv'):
        super().__init__(platform_name, channel_config)
        self.channel_id = str(channel_id) if channel_id else '100113'
        self.category_key = category_key
        self.timeout = 20
        # 从 channel_config 读取排序类型，支持 is_hot / is_new 标记
        # sort: 'hot' = 热门列表, 'new' = 最新列表, ''/None = 默认（不刷标记）
        # 腾讯 API 需要映射为数字编码：75=热门, 71/79=最新
        sort_val = str(channel_config.get('sort', '') or '').strip()
        if sort_val == 'hot':
            self._list_type = 'hot'
            self._filter_params = 'sort=75'
        elif sort_val == 'new':
            self._list_type = 'new'
            self._filter_params = 'sort=71'
        else:
            self._list_type = ''
            self._filter_params = ''
        # 动态获取 User-Agent
        self.HEADERS = {
            'Content-Type': 'application/json',
            'User-Agent': self.get_user_agent(),
            'Origin': 'https://v.qq.com',
            'Referer': 'https://v.qq.com/',
        }

        # 从 AdminPlatform 配置加载关键词（fallback 到硬编码）
        self._trailer_keywords = load_keywords('tencent', 'trailer', self._TRAILER_FALLBACK)
        self._vip_keywords = load_keywords('tencent', 'vip', self._VIP_FALLBACK)
        self._bts_keywords = load_keywords('tencent', 'bts', self._BTS_FALLBACK)
        self._finished_keywords = load_keywords('tencent', 'finish', self._FINISHED_FALLBACK)
        self._ongoing_keywords = load_keywords('tencent', 'ongoing', self._ONGOING_FALLBACK)

    def _request_with_retry(self, url, payload, timeout=None):
        """带重试的POST请求封装，所有腾讯API请求统一走这里"""
        timeout = timeout or self.timeout

        def _do_request():
            resp = requests.post(url, json=payload, headers=self.HEADERS, timeout=timeout)
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError(f"API返回数据结构不正确: {type(data)}")
            return data

        return RetryHelper.with_retry(
            _do_request, max_retries=3, base_delay=1, max_delay=8,
            exceptions=(requests.RequestException, ValueError)
        )

    def crawl(self, max_items=10):
        """腾讯游标分页：串行获取列表，并发获取详情"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print(f'[{self.platform_name}] 开始爬取...')

        all_items = []
        seen_ids = set()

        # 第一阶段：串行翻页获取列表（游标分页，不能并发）
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
                    if (max_items is not None) and (len(all_items) >= max_items):
                        break

            print(f'本次获取 {len(items)} 条，新增 {new_count} 条，总计 {len(all_items)} 条')

            if new_count == 0 and len(items) == 0:
                break

            page += 1
            time.sleep(0.3)  # 优化：从0.5s降到0.3s

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

    def fetch_list_page(self, page_index=0, poster_offset=0, poster_size=12, showed_module=0):
        page_params = {
            'channel_id': self.channel_id,
            'filter_params': self._filter_params,
            'page_id': 'channel_list',
            'page_type': 'operation',
        }

        payload = {'page_params': page_params}

        if page_index > 0:
            payload['page_context'] = {
                '_ctrl_page_index': str(page_index),
                '_ctrl_showed_module_num': str(showed_module),
                '_ds_cli_6970df954e7a9803_poster_offset': str(poster_offset),
                '_ds_cli_6970df954e7a9803_poster_size': str(poster_size),
                '_merger_mod_cnt': str(showed_module),
                'page_index': str(page_index),
                'sdk_page_ctx': json.dumps({
                    'page_offset': page_index,
                    'page_size': 5,
                    'used_module_num': showed_module
                }),
                'video_un_page_index': str(page_index),
            }

        try:
            return self._request_with_retry(self.MVL_API, payload)
        except Exception as e:
            logger.error(f"列表页请求失败(已重试3次): {e}", exc_info=True)
            return None

    def extract_items_from_response(self, data):
        items_list = []

        try:
            data_content = data.get('data', data)
            modules = data_content.get('modules', {})

            # 遍历 modules 的所有键（normal, video, variety, movie, cartoon, child 等）
            # 不同频道的API返回的modules键名不同，不能只取normal和video
            for module_key, module_data in modules.items():
                if not isinstance(module_data, dict):
                    continue
                cards = module_data.get('cards', [])
                for card in cards:
                    items_list.extend(self._extract_from_card(card))

            data_cards = data_content.get('cards', [])
            for card in data_cards:
                items_list.extend(self._extract_from_card(card))

            logger.debug(f"从 {len(items_list)} 个项目中提取")
        except Exception as e:
            logger.error(f"提取项目失败: {e}", exc_info=True)

        seen = set()
        unique_items = []
        for item in items_list:
            cid = item.get('cid')
            if cid and cid not in seen:
                seen.add(cid)
                unique_items.append(item)

        return unique_items

    def _extract_from_card(self, card):
        items = []

        if not isinstance(card, dict):
            return items

        children_list = card.get('children_list', {})
        for key, sub_cards_data in children_list.items():
            if isinstance(sub_cards_data, list):
                sub_cards = sub_cards_data
            elif isinstance(sub_cards_data, dict):
                sub_cards = sub_cards_data.get('cards', [])
            else:
                continue

            for sub_card in sub_cards:
                # 优化：合并三种card_type判断，减少重复代码
                card_type = sub_card.get('type', '')
                if card_type in self._PARAMS_CARD_TYPES or 'params' in sub_card:
                    params = sub_card.get('params', {})
                    item = self._extract_item_params(params)
                    if item:
                        items.append(item)

        return items

    def _extract_item_params(self, params):
        cid = params.get('cid', '')
        first_vid = params.get('first_vid', '')
        title = params.get('title', '')

        if not cid or not title:
            return None

        area = params.get('areaName', '') or params.get('area_name', '')

        year = params.get('year', '')

        all_ids_raw = params.get('all_ids', '[]')
        try:
            all_ids = json.loads(all_ids_raw)
            vids = [item['V'] for item in all_ids if item.get('V')]
        except Exception:
            vids = []

        tags = []
        labels_raw = params.get('chnlist_search_label', '[]')
        try:
            labels = json.loads(labels_raw)
            tags = [l.get('label', '') for l in labels if l.get('label')]
        except Exception:
            pass

        # 封面图：优先使用 new_pic_hz（横版高清）/ new_pic_vt（竖版），回退到 poster_pic/horizontal_pic
        pic_hz = params.get('new_pic_hz', '')
        pic_vt = params.get('new_pic_vt', '')
        poster_pic = params.get('poster_pic', '') or params.get('horizontal_pic', '')
        if not poster_pic and vids:
            poster_pic = f'https://vpic-cover.puui.qpic.cn/{vids[0]}/{vids[0]}_hz.jpg'

        score = ''
        for tag in tags:
            m = re.match(r'评分\s*(\d+\.?\d*)', tag)
            if m:
                score = m.group(1)
                break

        play_url = params.get('play_url', '')
        if not play_url and cid and first_vid:
            play_url = f'https://v.qq.com/x/cover/{cid}/{first_vid}.html'
        elif not play_url and cid:
            play_url = f'https://v.qq.com/x/cover/{cid}.html'

        # 提取演员信息
        actors = []
        leading_actor = params.get('leading_actor', '')
        if leading_actor:
            leading_actor = leading_actor.strip()
            if leading_actor.startswith('[') and leading_actor.endswith(']'):
                leading_actor = leading_actor[1:-1]
            actors = [a.strip() for a in re.split(r'[\s]+', leading_actor) if a.strip()]

        # 列表页提取 is_vip：优先 is_pay，其次检查 tags/text 中是否有 VIP 字样
        is_vip = 0
        if params.get('is_pay', '') == '1':
            is_vip = 1
        else:
            # 检查 params 中其他字段是否有 VIP 标识
            for key in ['tag_text', 'tags', 'title', 'description']:
                val = params.get(key, '')
                if val and any(kw in str(val) for kw in self._vip_keywords):
                    is_vip = 1
                    break
            # 检查 tags 列表中是否有 VIP 标签
            for tag in tags:
                if any(kw in tag for kw in self._vip_keywords):
                    is_vip = 1
                    break

        return {
            'cid': cid,
            'title': title,
            'first_vid': first_vid or (vids[0] if vids else ''),
            'area': area,
            'year': year,
            'score': score,
            'tags': tags,
            'actors': json.dumps(actors, ensure_ascii=False) if actors else '',
            'thumbnail': pic_vt or poster_pic,
            'cover_url': pic_hz or poster_pic,
            'play_url': play_url,
            'platform': 'tencent',
            'category_key': self.category_key,
            # 列表页提取的 is_vip（详情页会进一步校正）
            'is_vip': is_vip,
            # 根据当前 channel 的 sort 类型标记最热/最新
            'is_hot': 1 if self._list_type == 'hot' else None,
            'is_new': 1 if self._list_type == 'new' else None,
        }

    def fetch_detail(self, item):
        """获取剧集详情和分集信息，只填充数据不保存（由调度层统一保存）"""
        try:
            cid = item.get('cid', '')
            first_vid = item.get('first_vid', '')

            if not cid:
                logger.warning(f"缺少CID: {item.get('title')}")
                return

            logger.info(f"获取详情: {item.get('title')} - CID: {cid}")

            episodes, detail = self._fetch_episodes(cid, first_vid)

            if detail.get('description'):
                item['description'] = detail['description']
            if detail.get('year') and not item.get('year'):
                item['year'] = detail['year']
            if detail.get('area') and not item.get('area'):
                item['area'] = detail['area']
            if detail.get('broadcast_time'):
                item['broadcast_time'] = detail['broadcast_time']
            if detail.get('actors') and not item.get('actors'):
                item['actors'] = detail['actors']
            # 问题6：将导演字段写入 item['director']
            if detail.get('director') and not item.get('director'):
                item['director'] = detail['director']
            if detail.get('cover_url'):
                item['cover_url'] = detail['cover_url']
            # 问题8：评分 fallback（详情页补充）
            if detail.get('score') and not item.get('score'):
                item['score'] = detail['score']
            if episodes:
                # 问题7：所有 tab 拼合完毕后，按 episode_num 数字升序排序再入库
                def _ep_sort_key(ep):
                    num = str(ep.get('episode_num', '') or '')
                    return int(num) if num.isdigit() else 9999
                episodes.sort(key=_ep_sort_key)

                # 整剧 VIP 标识：优先从 detail_info 解析，
                # 若为0则回退从分集 pay_type 聚合判断（电影场景 detail_info 常缺失 VIP 标识）
                series_is_vip = detail.get('series_is_vip', 0)
                if not series_is_vip:
                    # 回退1：检查所有分集（包括正片）的 pay_type
                    pay_vip_count = 0
                    for ep in episodes:
                        if ep.get('is_vip', 0) > 0:
                            pay_vip_count += 1
                    # 如果有一半以上的分集是 VIP，或者有任何一个正片是 VIP，那么整剧就是 VIP
                    if pay_vip_count > 0:
                        series_is_vip = 1
                    # 回退2：如果是电影，再检查列表页的 is_vip 和详情页的其他字段
                    if not series_is_vip and self.category_key == 'movie':
                        # 优先用列表页判断的 is_vip
                        if item.get('is_vip', 0) > 0:
                            series_is_vip = item.get('is_vip', 0)
                        else:
                            # 再检查 detail 中是否有其他 VIP 相关信息
                            for key in ['tag_text', 'detail_info', 'normal_matrix_info', 'title', 'description']:
                                val = detail.get(key, '')
                                if val and any(kw in str(val) for kw in self._vip_keywords):
                                    series_is_vip = 1
                                    break
                            # 再检查 item 本身是否有 VIP 相关信息
                            if not series_is_vip:
                                for key in ['tags', 'title', 'description']:
                                    val = item.get(key, '')
                                    if val and any(kw in str(val) for kw in self._vip_keywords):
                                        series_is_vip = 1
                                        break

                # 根据整剧 VIP 状态统一设置分集 is_vip
                for ep in episodes:
                    ep['is_vip'] = series_is_vip  # 全部先按整剧级别赋值

                # VIP 前2集免费规则：非电影的电视剧，正片前2集强制 is_vip=0
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
                api_total = detail.get('total_episodes', 0)
                api_updated = detail.get('updated_episodes', 0)
                # 真实总集数：优先用 pc_introduction 的 episode_all（全局），fallback 到 episode_list 的 total（per-tab）
                real_total = detail.get('episode_all', 0) or api_total
                episode_sub_title = detail.get('episode_sub_title', '')

                # 问题5：updated_episodes 用 main_count（实际正片数），API返回值含预告/花絮不准
                if real_total:
                    item['total_episodes'] = real_total
                else:
                    item['total_episodes'] = main_count
                item['updated_episodes'] = main_count
                item['has_episodes'] = True

                # 剧集级 VIP：直接使用从 detail_info 解析的整剧标识（比分集聚合更准确）
                item['is_vip'] = series_is_vip

                # 完结状态判断
                item['is_finished'] = self._judge_finished(
                    episode_sub_title=episode_sub_title,
                    episode_all=real_total,
                    main_eps=main_eps,
                    trailer_eps=trailer_eps,
                    updated_episodes=api_updated or main_count,
                    year=item.get('year', ''),
                )

                logger.info(f"提取到 {len(episodes)} 集（正片{main_count}集，预告{len(trailer_eps)}集，花絮{len(bts_eps)}集），API: 总{api_total}集/更新{api_updated}集，全局总{real_total}集，最终: 总{item['total_episodes']}集，更新至{item['updated_episodes']}集，VIP={item['is_vip']}，完结={item['is_finished']}")
            else:
                item['has_episodes'] = False
                item['total_episodes'] = detail.get('total_episodes', 0) or 0
                item['updated_episodes'] = detail.get('updated_episodes', 0) or 0

        except Exception as e:
            logger.error(f"详情获取失败: {item.get('title', '未知')}, 错误: {e}", exc_info=True)

    def _fetch_episodes(self, cid, first_vid=''):
        base_page_params = {
            'req_from': 'web_vsite',
            'new_mark_label_enabled': '1',
            'cid': cid,
            'vid': first_vid,
            'is_pc_new_detail_page': '0',
            'is_from_web_flyflow': '1',
        }

        payload = {
            'page_params': base_page_params.copy(),
            'page_bypass_params': {
                'params': {
                    'caller_id': '3000010',
                    'platform_id': '2'
                },
                'scene': 'desk_detail',
            },
            'page_context': {},
        }

        try:
            data = self._request_with_retry(self.GETPAGE_API, payload)
        except Exception as e:
            logger.error(f"getPage请求失败(已重试) for {cid}: {e}")
            return [], {}

        card_list = data.get('data', {}).get('CardList', [])
        all_episodes = []
        series_detail = {}
        tabs_to_fetch = []
        episode_sub_title = ''  # 选集区域标题（如"更新至06集"/"全24集"）

        for card in card_list:
            card_type = card.get('type', '')

            if card_type == 'pc_web_episode_list':
                all_episodes.extend(self._extract_episodes_from_card(card, cid))

                params = card.get('params', {})
                # 提取选集标题（官网详情页选集区域的标题文案）
                st = params.get('sub_title', '') or params.get('desk_module_title', '')
                if st:
                    episode_sub_title = st
                for ep_field in ['total_episode', 'episode_count', 'total_num', 'video_count', 'count']:
                    val = params.get(ep_field)
                    if val and isinstance(val, (int, str)) and str(val).isdigit():
                        series_detail['total_episodes'] = int(val)
                        break
                for upd_field in ['latest_order', 'update_episode', 'current_episode', 'latest_num']:
                    val = params.get(upd_field)
                    if val and isinstance(val, (int, str)) and str(val).isdigit():
                        series_detail['updated_episodes'] = int(val)
                        break

                tabs_raw = params.get('tabs', '')
                if tabs_raw:
                    try:
                        tabs = json.loads(tabs_raw)
                        for tab in tabs:
                            if not tab.get('selected', False):
                                tabs_to_fetch.append(tab)
                    except json.JSONDecodeError:
                        pass

            elif card_type == 'pc_introduction':
                detail = self._extract_detail_from_card(card)
                series_detail.update(detail)

            elif card_type == 'pad_star_introduction':
                actors_json, directors_json = self._extract_actors_from_star_card(card)
                if actors_json and not series_detail.get('actors'):
                    series_detail['actors'] = actors_json
                if directors_json and not series_detail.get('director'):
                    series_detail['director'] = directors_json

        # 将选集标题写入 series_detail
        if episode_sub_title:
            series_detail['episode_sub_title'] = episode_sub_title

        for tab in tabs_to_fetch:
            tab_ctx = tab.get('page_context', '')
            if not tab_ctx:
                continue

            ctx_dict = {}
            for pair in tab_ctx.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    ctx_dict[k] = v

            extra_page_params = base_page_params.copy()
            for k in ['episode_begin', 'episode_end', 'episode_step', 'tab_type',
                       'detail_page_type', 'id_type', 'need_tab', 'page_num', 'page_size',
                       'mvl_strategy_id', 'filter_rule_id']:
                if k in ctx_dict:
                    extra_page_params[k] = ctx_dict[k]

            payload2 = {
                'page_params': extra_page_params,
                'page_bypass_params': {
                    'params': {
                        'caller_id': '3000010',
                        'platform_id': '2'
                    },
                    'scene': 'desk_detail',
                },
                'page_context': {},
            }

            try:
                data2 = self._request_with_retry(self.GETPAGE_API, payload2)
            except Exception as e:
                logger.error(f"getPage tab请求失败(已重试) for {cid}: {e}")
                continue

            card_list2 = data2.get('data', {}).get('CardList', [])
            for card2 in card_list2:
                if card2.get('type') == 'pc_web_episode_list':
                    all_episodes.extend(self._extract_episodes_from_card(card2, cid))

        return all_episodes, series_detail

    def _judge_finished(self, episode_sub_title, episode_all, main_eps, trailer_eps,
                        updated_episodes, year):
        """
        综合多信号判断完结状态。
        返回值：1=已完结，-1=未完结/连载中，0=未知

        信号优先级：
        1. 标题关键词+集数综合判断（连载关键词需集数确认，完结关键词需集数确认）
        2. 集数比较：main_count vs episode_all
        3. 标题提取总集数
        4. 其他兜底
        """
        main_count = len(main_eps)
        trailer_count = len(trailer_eps)
        
        logger.debug(f"[_judge_finished] episode_sub_title={episode_sub_title}, episode_all={episode_all}, updated_episodes={updated_episodes}, main_count={main_count}")

        st = (episode_sub_title or '').strip()

        # 优先级1：标题关键词 + 集数综合判断
        if st:
            has_ongoing = any(kw in st for kw in self._ongoing_keywords)
            has_finished = any(kw in st for kw in self._finished_keywords)
            logger.debug(f"[_judge_finished] 标题关键词检查 - has_ongoing={has_ongoing}, has_finished={has_finished}")
            # 连载关键词：需结合集数确认
            if has_ongoing and episode_all > 0 and main_count < episode_all:
                logger.debug("[_judge_finished] 判断为未完结（标题含连载关键词且正片数<总集数）")
                return -1
            # 完结关键词：需结合集数确认
            if has_finished and episode_all > 0 and main_count >= episode_all:
                logger.debug("[_judge_finished] 判断为完结（标题含完结关键词且正片数>=总集数）")
                return 1

        # 优先级2：集数比较（用main_count替代updated_episodes，后者含预告/花絮不准）
        if episode_all > 0 and main_count > 0:
            logger.debug(f"[_judge_finished] 集数比较 - episode_all={episode_all}, main_count={main_count}")
            if main_count < episode_all:
                logger.debug("[_judge_finished] 判断为未完结（正片数<总集数）")
                return -1
            if main_count >= episode_all:
                logger.debug("[_judge_finished] 判断为完结（正片数>=总集数）")
                return 1

        # 优先级3：标题关键词判断
        title_total = self._extract_total_from_title(st)
        if title_total > 0:
            # 如果标题中提取的总集数大于正片数，则未完结
            if main_count < title_total:
                return -1
            # 如果标题中提取的总集数等于正片数，则完结
            if main_count == title_total:
                return 1

        # 优先级4：其他
        # 正片数 < 总集数 → 未完结
        if episode_all > 0 and main_count < episode_all:
            return -1

        # 正片最后一集号 + 1 == 预告第一集号 → 未完结
        main_nums = sorted([
            int(str(ep.get('episode_num', '0'))) for ep in main_eps
            if str(ep.get('episode_num', '')).isdigit()
        ])
        trailer_nums = sorted([
            int(str(ep.get('episode_num', '0'))) for ep in trailer_eps
            if str(ep.get('episode_num', '')).isdigit()
        ])
        max_main = main_nums[-1] if main_nums else 0
        min_trailer = trailer_nums[0] if trailer_nums else 0
        if max_main > 0 and min_trailer > 0 and max_main + 1 == min_trailer:
            return -1

        # 综合兜底
        main_consecutive = (
            main_nums
            and main_nums[0] == 1
            and len(main_nums) == main_nums[-1]  # 1~N 连续无跳号
        )
        has_trailer = trailer_count > 0

        # episode_all 未知时
        if episode_all == 0:
            if not main_consecutive and has_trailer:
                return -1
            if main_consecutive and not has_trailer:
                y = int(year) if year and str(year).isdigit() else 0
                # 只有在剧集年份超过3年且没有预告的情况下才判断为完结
                # 否则默认为未知，避免误判
                if y > 0 and y <= 2023:  # 上映超3年
                    return 1
                # 如果年份未知或较近，且没有预告，则默认为未知
                return 0

        return 0  # 未知

    def _get_episode_type(self, title, is_trailer='0'):
        """
        判断分集类型：0=正片，1=预告，2=花絮

        判断逻辑：
        1. 标题包含"X集"格式且不包含预告/花絮关键词 → 正片
        2. 标题包含预告关键词 → 预告
        3. 标题包含花絮关键词 → 花絮
        4. is_trailer=1 → 预告
        5. 默认 → 正片
        """
        if not title:
            return 0

        title_lower = title.lower()

        # 优先判断预告/花絮关键词
        if any(kw in title_lower for kw in self._trailer_keywords):
            return 1

        if any(kw in title_lower for kw in self._bts_keywords):
            return 2

        # 标题包含"X集"格式（如"第31集"）且不包含预告/花絮关键词 → 正片
        if re.search(r'\d+\s*集', title):
            return 0

        # is_trailer=1 → 预告
        if is_trailer == '1':
            return 1

        return 0

    @staticmethod
    def _format_duration(duration_str: str) -> str:
        """将腾讯返回的纯秒数统一转为 MM:SS 格式；非纯数字则原样返回。"""
        if not duration_str:
            return duration_str
        s = str(duration_str).strip()
        if not s.isdigit():
            return s  # 已经是 "46:09" 等格式，原样保留
        total_sec = int(s)
        minutes = total_sec // 60
        seconds = total_sec % 60
        return f'{minutes:02d}:{seconds:02d}'

    def _extract_episodes_from_card(self, card, cid):
        episodes = []
        children_list = card.get('children_list', {})
        for key, sub_data in children_list.items():
            if not isinstance(sub_data, dict):
                continue
            for sub_card in sub_data.get('cards', []):
                if sub_card.get('type') != 'pc_web_episode_list':
                    continue
                params = sub_card.get('params', {})
                vid = params.get('vid', '')
                if not vid:
                    continue

                play_title = params.get('play_title', '')
                union_title = params.get('union_title', '')
                is_trailer = params.get('is_trailer', '0')
                # 问题2：统一 duration 格式，腾讯返回纯秒数，转为 MM:SS
                duration = self._format_duration(params.get('duration', ''))
                episode_num = params.get('title', '')
                video_subtitle = params.get('video_subtitle', '')

                # 问题4：尝试多个字段获取 publish_date，优先取毫秒时间戳
                publish_date = (
                    params.get('publish_date', '')
                    or params.get('publish_time', '')
                    or params.get('pubdate', '')
                    or params.get('air_date', '')
                    or params.get('upload_time', '')
                    or params.get('time', '')
                    or ''
                )

                episode_type = self._get_episode_type(
                    play_title, is_trailer=is_trailer
                )

                # VIP 标识：仅正片判断，预告/花絮强制免费
                if episode_type != 0:
                    is_vip = 0
                else:
                    pay_type = params.get('pay_type', '0')
                    is_advance = params.get('is_advance', '0')
                    is_vip = 0  # 默认免费
                    
                    # 判断逻辑
                    if is_advance == '1':
                        is_vip = 2  # 超前点播
                    elif str(pay_type) == '1':
                        is_vip = 1  # VIP
                    else:
                        # 额外检查其他字段是否有 VIP 相关信息
                        for key in ['play_title', 'union_title', 'title', 'tag_text', 'video_subtitle', 'description']:
                            val = params.get(key, '')
                            if val:
                                val_str = str(val)
                                for kw in self._vip_keywords:
                                    if kw in val_str:
                                        is_vip = 1
                                        break
                                if is_vip > 0:
                                    break

                episodes.append({
                    'episode_num': episode_num,
                    'vid': vid,
                    'play_title': play_title,
                    'union_title': union_title,
                    'episode_type': episode_type,
                    'is_trailer': is_trailer == '1',
                    'duration': duration,
                    'video_subtitle': video_subtitle,
                    'publish_date': publish_date,
                    'is_vip': is_vip,
                    'play_url': f'https://v.qq.com/x/cover/{cid}/{vid}.html',
                })
        return episodes

    def _extract_detail_from_card(self, card):
        series_detail = {}
        children_list = card.get('children_list', {})
        for key, sub_data in children_list.items():
            if not isinstance(sub_data, dict):
                continue
            for sub_card in sub_data.get('cards', []):
                params = sub_card.get('params', {})
                if params.get('cover_description'):
                    series_detail['description'] = params['cover_description']
                if params.get('cover_year'):
                    series_detail['year'] = params['cover_year']
                if params.get('area_name'):
                    series_detail['area'] = params['area_name']
                if params.get('broadcast_time'):
                    series_detail['broadcast_time'] = params['broadcast_time']
                if params.get('new_pic_hz'):
                    series_detail['cover_url'] = params['new_pic_hz']
                elif params.get('title_image_url'):
                    series_detail['cover_url'] = params['title_image_url']
                # 问题8：评分 fallback，从多个字段中提取
                if not series_detail.get('score'):
                    for score_field in ['cover_score', 'score', 'rating', 'user_rating', 'rat_score']:
                        val = params.get(score_field)
                        if val:
                            series_detail['score'] = str(val)
                            break
                # 真实总集数（pc_introduction 子 card 的 episode_all，非 per-tab 值）
                if not series_detail.get('episode_all'):
                    ea = params.get('episode_all', '')
                    if ea and str(ea).isdigit():
                        series_detail['episode_all'] = int(ea)
                # 整剧 VIP 标识：
                # pc_introduction card 中有 tag_text="VIP" 和 detail_info 含 VIP 字样
                # getPage 分集 card 不返回 pay_type，所以只能在这层判断
                if not series_detail.get('series_is_vip'):
                    # 方案1：tag_text 直接返回 "VIP" 或 "云首发"（最可靠）
                    tag_text = str(params.get('tag_text', '') or '')
                    # 方案2：detail_info 文本（HTML 格式，含 "VIP"/"云首发"）
                    di = str(params.get('detail_info', '') or '')
                    # 方案3：normal_matrix_info 文本
                    nmi = str(params.get('normal_matrix_info', '') or '')
                    # 腾讯VIP标识词从 DB 加载
                    if any(kw in tag_text or kw in di or kw in nmi for kw in self._vip_keywords):
                        series_detail['series_is_vip'] = 1
                actors_raw = params.get('actor', '') or params.get('actors', '') or params.get('star', '') or params.get('performer', '') or params.get('actors_name', '') or params.get('actor_name', '') or params.get('main_actor', '') or params.get('leading_role', '') or params.get('starring', '')
                if actors_raw and not series_detail.get('actors'):
                    try:
                        actors_list = json.loads(actors_raw)
                        if isinstance(actors_list, list):
                            series_detail['actors'] = json.dumps([a.get('name', a) if isinstance(a, dict) else str(a) for a in actors_list], ensure_ascii=False)
                        elif isinstance(actors_list, dict):
                            actor_names = []
                            for key, value in actors_list.items():
                                if isinstance(value, dict) and 'name' in value:
                                    actor_names.append(value['name'])
                                elif isinstance(value, str):
                                    actor_names.append(value)
                                elif isinstance(value, list):
                                    actor_names.extend([item.get('name', item) if isinstance(item, dict) else str(item) for item in value])
                            if actor_names:
                                series_detail['actors'] = json.dumps(actor_names, ensure_ascii=False)
                        else:
                            series_detail['actors'] = json.dumps([str(actors_list)], ensure_ascii=False)
                    except (json.JSONDecodeError, TypeError):
                        actors = [a.strip() for a in re.split(r'[,，、\s]+', str(actors_raw)) if a.strip()]
                        if actors:
                            series_detail['actors'] = json.dumps(actors, ensure_ascii=False)
        return series_detail

    def _extract_total_from_title(self, title):
        """从选集标题中提取总集数，如更新X/总X集
        返回总集数，如果无法提取则返回0
        """
        if not title:
            return 0
            
        # 匹配模式1: 更新X/总X集
        pattern1 = r'更新\s*(\d+)\s*/\s*总\s*(\d+)\s*集'
        match1 = re.search(pattern1, title)
        if match1:
            return int(match1.group(2))
            
        # 匹配模式2: 更新至X集/共X集
        pattern2 = r'更新\s*至\s*(\d+)\s*集\s*/\s*共\s*(\d+)\s*集'
        match2 = re.search(pattern2, title)
        if match2:
            return int(match2.group(2))
            
        # 匹配模式3: X/集数
        pattern3 = r'(\d+)\s*/\s*(\d+)\s*集'
        match3 = re.search(pattern3, title)
        if match3:
            return int(match3.group(2))
            
        return 0

    def _extract_actors_from_star_card(self, card):
        """从 pad_star_introduction 卡片中提取演员和导演信息，返回 (actors_json, directors_json)"""
        actors = []
        directors = []
        children_list = card.get('children_list', {})
        for key, sub_data in children_list.items():
            if not isinstance(sub_data, dict):
                continue
            for sub_card in sub_data.get('cards', []):
                params = sub_card.get('params', {})
                star_name = params.get('star_name', '')
                star_role = params.get('star_role_label', '')
                if star_name:
                    if star_role and ('导演' in star_role or '监制' in star_role):
                        directors.append(star_name)
                    else:
                        actors.append(star_name)

        actors_json = json.dumps(actors, ensure_ascii=False) if actors else ''
        directors_json = json.dumps(directors, ensure_ascii=False) if directors else ''
        # 返回 (actors_json, directors_json) 元组供 fetch_detail 拆分使用
        return actors_json, directors_json
