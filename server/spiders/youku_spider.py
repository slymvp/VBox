"""
优酷视频爬虫实现
继承自 YoukuBaseSpider，支持电视剧、电影、综艺、动漫、少儿5个频道
"""
from spiders.youku_base import YoukuBaseSpider
from core.logger import setup_logger

logger = setup_logger('vbox.youku.spider')


class YoukuSpider(YoukuBaseSpider):
    """优酷视频爬虫类"""

    def __init__(self, channel_config):
        """
        初始化优酷爬虫
        :param channel_config: 频道配置
        """
        # 优先使用 main.py 注入的 category_key（最可靠），其次使用数据库 channel_key 字段
        category_key = channel_config.get('category_key') or channel_config.get('channel_key') or 'tv'

        super().__init__('优酷', channel_config, category_key)
        logger.info(f"初始化优酷爬虫: category={category_key}, channel={self.channel_url}")

    def extract_items(self, api_data):
        """从API响应中提取剧集列表"""
        if not api_data:
            return []
        try:
            items = super().extract_items(api_data)
            logger.info(f"提取到 {len(items)} 个剧集")
            return items
        except Exception as e:
            logger.error(f"提取剧集失败: {e}", exc_info=True)
            return []

    def fetch_list_page(self, page=1, **kwargs):
        """获取列表页数据"""
        return super().fetch_list_page(page, **kwargs)


