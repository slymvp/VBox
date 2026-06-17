"""
腾讯视频爬虫实现
继承自 TencentBaseSpider，支持电视剧和电影
"""
from spiders.tencent_base import TencentBaseSpider
from core.logger import setup_logger

logger = setup_logger('vbox.tencent.spider')


class TencentSpider(TencentBaseSpider):
    """腾讯视频爬虫类"""

    # 频道 key -> 腾讯 MVL API channel_id 映射
    CHANNEL_ID_MAP = {
        'tv': '100113',
        'movie': '100173',
        'variety': '100109',
        'cartoon': '100119',
        'child': '100150',
        'free': '100113',
    }

    def __init__(self, channel_config):
        """
        初始化腾讯爬虫
        :param channel_config: 频道配置
        """
        # 优先使用 main.py 注入的 category_key（最可靠），
        # 其次使用数据库 channel_key 字段，最后默认 tv
        category_key = channel_config.get('category_key') or channel_config.get('channel_key') or 'tv'
        # channel_id 优先从数据库配置读取，否则根据 category_key 自动映射
        channel_id = channel_config.get('channel_id') or self.CHANNEL_ID_MAP.get(category_key, '100113')

        super().__init__('腾讯视频', channel_config, channel_id, category_key)
        logger.info(f"初始化腾讯爬虫: category={category_key}, channel_id={channel_id}")

    def extract_items(self, data):
        """
        从API响应中提取剧集列表
        :param data: API响应数据
        :return: 剧集列表
        """
        if not data:
            return []
        
        try:
            items = self.extract_items_from_response(data)
            logger.info(f"提取到 {len(items)} 个剧集")
            return items
        except Exception as e:
            logger.error(f"提取剧集失败: {e}", exc_info=True)
            return []

    def fetch_list_page(self, page=1, **kwargs):
        """
        获取列表页数据
        :param page: 页码（从1开始）
        :return: API响应数据
        """
        # MVL API的page_index从0开始
        page_index = page - 1
        
        # 每页数量
        poster_size = kwargs.get('poster_size', 20)
        poster_offset = kwargs.get('poster_offset', page_index * poster_size)
        
        try:
            data = super().fetch_list_page(
                page_index=page_index,
                poster_offset=poster_offset,
                poster_size=poster_size
            )
            
            # 调试：打印数据结构
            if data:
                logger.debug(f"API响应数据类型: {type(data)}")
                logger.debug(f"API响应keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if 'data' in data:
                    data_dict = data.get('data', {})
                    logger.debug(f"data keys: {list(data_dict.keys())}")
                    if 'modules' in data_dict:
                        modules = data_dict.get('modules', {})
                        logger.debug(f"modules keys: {list(modules.keys())}")
            
            return data
        except Exception as e:
            logger.error(f"获取列表页失败 (page={page}): {e}", exc_info=True)
            return None


# ==================== 按频道拆分的独立Spider类 ====================

class TencentTvSpider(TencentBaseSpider):
    """腾讯电视剧爬虫"""
    def __init__(self, channel_config):
        channel_id = channel_config.get('channel_id') or '100113'
        super().__init__('腾讯视频', channel_config, channel_id, 'tv')
        logger.info("初始化腾讯电视剧爬虫")


class TencentMovieSpider(TencentBaseSpider):
    """腾讯电影爬虫"""
    def __init__(self, channel_config):
        channel_id = channel_config.get('channel_id') or '100173'
        super().__init__('腾讯视频', channel_config, channel_id, 'movie')
        logger.info("初始化腾讯电影爬虫")


class TencentVarietySpider(TencentBaseSpider):
    """腾讯综艺爬虫"""
    def __init__(self, channel_config):
        channel_id = channel_config.get('channel_id') or '100109'
        super().__init__('腾讯视频', channel_config, channel_id, 'variety')
        logger.info("初始化腾讯综艺爬虫")


class TencentCartoonSpider(TencentBaseSpider):
    """腾讯动漫爬虫"""
    def __init__(self, channel_config):
        channel_id = channel_config.get('channel_id') or '100119'
        super().__init__('腾讯视频', channel_config, channel_id, 'cartoon')
        logger.info("初始化腾讯动漫爬虫")


class TencentChildSpider(TencentBaseSpider):
    """腾讯少儿爬虫"""
    def __init__(self, channel_config):
        channel_id = channel_config.get('channel_id') or '100150'
        super().__init__('腾讯视频', channel_config, channel_id, 'child')
        logger.info("初始化腾讯少儿爬虫")