"""
爬虫关键词统一加载模块

所有平台的关键词统一从 AdminPlatform 配置的 keywords 字段加载，
硬编码列表仅作 fallback。

使用方式：
    from spiders.keywords import load_keywords

    trailer_kw = load_keywords('youku', 'trailer', HARDCODED_TRAILER_FALLBACK)
    vip_kw    = load_keywords('youku', 'vip',      HARDCODED_VIP_FALLBACK)
    finish_kw = load_keywords('tencent', 'finish',  HARDCODED_FINISH_FALLBACK)

加载优先级：
    1. AdminPlatform 配置的 keywords 字段
    2. 调用方传入的 fallback 硬编码列表
"""
import logging
import time

logger = logging.getLogger('vbox.keywords')

# 全局缓存：避免重复查询
_cache: dict = {}       # {cache_key: keywords_list}
_cache_ts: dict = {}    # {cache_key: timestamp}
_CACHE_TTL = 300  # 5分钟 TTL


def _load_from_platform_config(platform: str, keyword_type: str):
    """从 AdminPlatform 配置的 keywords 字段加载"""
    try:
        from core.config import Config
        config = Config()
        platform_config = config.get_platform(platform)
        keywords_dict = platform_config.get('keywords')
        if keywords_dict and isinstance(keywords_dict, dict):
            keywords = keywords_dict.get(keyword_type, [])
            if keywords:
                logger.debug(f"[keywords] 平台配置加载 {len(keywords)} 条 [{platform}|{keyword_type}]")
                return keywords
    except Exception as e:
        logger.debug(f"[keywords] 平台配置加载失败 ({platform}|{keyword_type}): {e}")
    return []


def load_keywords(platform: str, keyword_type: str, fallback: list = None) -> list:
    """
    加载关键词列表（带 TTL 缓存）

    :param platform: 平台标识，如 'youku' / 'tencent' / 'iqiyi' / 'all'
    :param keyword_type: 类型，如 'trailer' / 'bts' / 'vip' / 'positive' / 'finish' / 'ongoing'
    :param fallback: 硬编码 fallback 列表，平台配置无数据时使用
    :return: 关键词列表
    """
    cache_key = f'{platform}:{keyword_type}'
    now = time.time()

    # 检查缓存是否有效
    if cache_key in _cache:
        cached_ts = _cache_ts.get(cache_key, 0)
        if now - cached_ts < _CACHE_TTL:
            return _cache[cache_key]
        # 缓存过期，清除
        del _cache[cache_key]
        _cache_ts.pop(cache_key, None)

    # 优先级 1: AdminPlatform 配置
    keywords = _load_from_platform_config(platform, keyword_type)
    # 优先级 2: 硬编码 fallback
    if not keywords:
        keywords = fallback or []
        if keywords:
            logger.debug(f"[keywords] 硬编码 fallback {len(keywords)} 条 [{platform}|{keyword_type}]")

    _cache[cache_key] = keywords
    _cache_ts[cache_key] = now
    return keywords


def clear_cache():
    """清除关键词缓存（用于调试或配置热更新）"""
    _cache.clear()
    _cache_ts.clear()
