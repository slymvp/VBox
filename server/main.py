
"""
VBox 爬虫核心功能模块
提供爬取和数据保存功能，供 web 界面调用
"""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.logger import setup_logger
from core.database import DatabaseManager

logger = setup_logger('vbox.crawler')


def get_spider_cls(spider_path):
    """动态导入爬虫类"""
    module_path, class_name = spider_path.rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


def save_items_to_db(items, platform_key, category_key, sort=None):
    """
    将爬取的数据统一保存到数据库（批量入库，单次session）
    :param items: 爬虫返回的数据列表
    :param platform_key: 平台键名
    :param category_key: 频道标识（tv, movie, variety, cartoon, child）
    :param sort: 排序类型，'hot'=只刷is_hot, 'new'=只刷is_new, None=全量保存
    """
    if not items:
        return 0

    from core.normalize import normalize_actors, normalize_area, normalize_tags, normalize_score

    # 组装批量数据
    batch_data = []
    for item in items:
        series_data = {
            'platform': item.get('platform', platform_key),
            'cid': item.get('cid', '') or item.get('album_id', '') or item.get('vid', ''),
            'title': item.get('title', ''),
            'url': item.get('url', '') or item.get('play_url', ''),
            'first_vid': item.get('first_vid', '') or item.get('vid', ''),
            'area': normalize_area(item.get('area', '')),
            'year': item.get('year', ''),
            'score': normalize_score(item.get('score')),
            'tags': normalize_tags(item.get('tags', [])),
            'thumbnail': item.get('thumbnail', ''),
            'cover_url': item.get('cover_url', ''),
            'description': item.get('description', ''),
            'actors': normalize_actors(item.get('actors', '')),
            'director': normalize_actors(item.get('director', '')),
            'total_episodes': item.get('total_episodes', 0),
            'updated_episodes': item.get('updated_episodes', 0),
            'is_vip': item.get('is_vip', 0),
            'is_hot': item.get('is_hot', 0),
            'is_new': item.get('is_new', 0),
            'is_finished': item.get('is_finished', 0),
        }

        # 计算分集数量
        episodes = item.get('episodes', [])
        if episodes:
            main_eps = [ep for ep in episodes if ep.get('episode_type', 0) == 0]
            if not series_data['total_episodes']:
                series_data['total_episodes'] = len(main_eps)
            if not series_data['updated_episodes']:
                series_data['updated_episodes'] = len(main_eps)

        batch_data.append({
            'series_data': series_data,
            'episodes_data': episodes,
        })

    # 批量入库（单次session），sort=hot/new 时只更新标记字段
    saved_count = DatabaseManager.batch_save_series_and_episodes(
        category_key, batch_data, sort=sort
    )
    return saved_count


def crawl_platform(platform_key, channel_key=None, max_items=10, db_task_id=None, sort=None):
    """
    爬取单个平台（可在独立进程中运行）
    :param platform_key: 平台键名
    :param channel_key: 频道键名（可选）
    :param max_items: 最大爬取数量
    :param db_task_id: 已存在的数据库任务ID（可选，避免重复创建）
    :param sort: 排序类型，'hot'=只刷is_hot, 'new'=只刷is_new, None=全量保存
    """
    from core.log_stream import get_memory_log_handler
    log_handler = get_memory_log_handler()

    config = Config()
    platform_config = config.get_platform(platform_key)

    if not platform_config:
        logger.error(f'找不到平台 "{platform_key}"')
        return

    spider_path = platform_config.get('spider')
    if not spider_path:
        logger.error(f'平台 "{platform_key}" 未配置爬虫')
        return

    try:
        spider_cls = get_spider_cls(spider_path)
    except Exception as e:
        logger.error(f'加载爬虫类失败 {spider_path}: {e}')
        return

    channels = config.get_channels(platform_key)
    if channel_key:
        channels = {channel_key: channels.get(channel_key, {})}

    if not channels:
        logger.error('未找到频道配置')
        return

    # 遍历频道，但只处理与channel_key匹配的单个频道（避免重复处理）
    for ch_key, ch_config in channels.items():
        # 如果指定了channel_key，只处理那个频道
        if channel_key and ch_key != channel_key:
            continue

        # 注入 category_key 到频道配置中，供爬虫使用
        if 'category_key' not in ch_config:
            ch_config['category_key'] = ch_key

        # 注入 sort 到频道配置，用于刷新 is_hot/is_new
        if sort:
            ch_config['sort'] = sort

        task_id = db_task_id
        try:
            # 只有在没有传入task_id时才创建新任务
            if not task_id:
                task_id = DatabaseManager.create_crawl_task(platform_key, ch_key)
            
            # 标记任务为开始状态
            DatabaseManager.start_crawl_task(task_id)
            log_handler.set_task_id(task_id)

            logger.info(f'\n{"="*60}')
            logger.info(f'开始爬取: {platform_config.get("name")} - {ch_config.get("name", ch_key)}')
            logger.info(f'{"="*60}\n')

            spider = spider_cls(ch_config)
            items = spider.crawl(max_items=max_items)

            # 调度层统一保存数据到数据库（ch_key 即为 category_key）
            saved_count = save_items_to_db(items, platform_key, ch_key, sort=sort)
            logger.info(f'数据入库: {saved_count}/{len(items)} 条')

            # 更新任务状态
            if task_id:
                DatabaseManager.complete_crawl_task(task_id, len(items))

            logger.info(f'\n爬取完成: {platform_config.get("name")} - {ch_config.get("name", ch_key)}, 共 {len(items)} 条\n')

        except Exception as e:
            logger.error(f'爬取失败: {e}', exc_info=True)
            if task_id:
                DatabaseManager.complete_crawl_task(task_id, 0, str(e))
        finally:
            log_handler.set_task_id(None)

