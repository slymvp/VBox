"""
配置管理模块
所有配置从数据库读取
"""
import json
import os
from .database import DatabaseManager


class Config:
    def __init__(self):
        self.db = DatabaseManager()
        self._default_keyword_template = {
            'positive_keywords': ['正片', '第'],
            'trailer_keywords': ['预告', '预告片'],
            'bts_keywords': ['花絮', '幕后', '精彩片段']
        }
        # 缓存
        self._platforms_cache = None
        self._channels_cache = {}
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, 'vbox.db')
    
    def _load_from_db(self):
        """从数据库重新加载所有配置"""
        platforms = self.db.list_platforms()
        self._platforms_cache = {}
        self._channels_cache = {}
        
        for p in platforms:
            self._platforms_cache[p['key']] = p
            self._channels_cache[p['key']] = {}
        
        channels = self.db.list_platform_channels()
        for ch in channels:
            # 跳过无效的平台配置
            if not ch['platform']:
                continue
            platform_key = ch['platform']['key']
            category_key = ch['category']['key']
            if platform_key not in self._channels_cache:
                self._channels_cache[platform_key] = {}
            self._channels_cache[platform_key][category_key] = ch
    
    def get_platforms(self):
        """获取所有平台配置"""
        if not self._platforms_cache:
            self._load_from_db()
        return self._platforms_cache
    
    def get_platform(self, platform_key):
        """获取单个平台配置"""
        if not self._platforms_cache:
            self._load_from_db()
        return self._platforms_cache.get(platform_key, {})
    
    def get_channels(self, platform_key):
        """获取平台下的所有频道"""
        if not self._channels_cache or platform_key not in self._channels_cache:
            self._load_from_db()
        return self._channels_cache.get(platform_key, {})
    
    def get_channel(self, platform_key, channel_key):
        """获取单个频道配置"""
        if not self._channels_cache or platform_key not in self._channels_cache:
            self._load_from_db()
        return self._channels_cache.get(platform_key, {}).get(channel_key, {})
    
    def get_keyword_template(self):
        """获取全局关键词模板（从数据库读取平台关键词或者返回默认）"""
        return self._default_keyword_template
    
    def get_platform_keywords(self, platform_key):
        """获取平台关键词配置"""
        platform = self.get_platform(platform_key)
        # 先尝试从 keywords 字典中获取
        keywords_dict = platform.get('keywords')
        if keywords_dict and isinstance(keywords_dict, dict):
            return {
                'positive_keywords': keywords_dict.get('positive', []),
                'trailer_keywords': keywords_dict.get('trailer', []),
                'bts_keywords': keywords_dict.get('bts', []),
                'vip_keywords': keywords_dict.get('vip', []),
                'finish_keywords': keywords_dict.get('finish', []),
                'ongoing_keywords': keywords_dict.get('ongoing', []),
            }
        # 如果没有，再尝试旧的字段名
        return {
            'positive_keywords': platform.get('positive_keywords', []),
            'trailer_keywords': platform.get('trailer_keywords', []),
            'bts_keywords': platform.get('bts_keywords', []),
            'vip_keywords': platform.get('vip_keywords', []),
            'finish_keywords': platform.get('finish_keywords', []),
            'ongoing_keywords': platform.get('ongoing_keywords', []),
        }
    
    # 以下方法保持向后兼容，但不再操作 YAML
    def create_platform(self, *args, **kwargs):
        pass
    
    def update_platform(self, *args, **kwargs):
        self._platforms_cache = None
        self._channels_cache = None
    
    def delete_platform(self, *args, **kwargs):
        self._platforms_cache = None
        self._channels_cache = None
    
    def create_channel(self, *args, **kwargs):
        pass
    
    def update_channel(self, *args, **kwargs):
        self._platforms_cache = None
        self._channels_cache = None
    
    def delete_channel(self, *args, **kwargs):
        self._platforms_cache = None
        self._channels_cache = None
    
    def update_keyword_template(self, *args, **kwargs):
        pass
    
    def update_platform_keywords(self, *args, **kwargs):
        self._platforms_cache = None
        self._channels_cache = None
