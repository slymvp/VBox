"""
统一完结判断模块

所有平台共用同一套判断逻辑，各 Spider 只负责采集信号。
信号优先级：API 字段 > 文本关键词 > 集数比较 > 预告存在性 > 兜底

返回值：1=已完结, -1=连载中, 0=未知
"""
import re
import logging

logger = logging.getLogger('vbox.finished_judge')


def judge(
    api_finished: int = 0,
    text: str = '',
    total_episodes: int = 0,
    main_count: int = 0,
    trailer_count: int = 0,
    category_key: str = '',
) -> int:
    """
    统一完结判断入口。

    :param api_finished: API 返回的完结字段（1=完结, -1=未完结, 0=未知）
    :param text: 选集标题文本（如 "全40集"、"更新至15集"）
    :param total_episodes: 总集数（API 或解析得到）
    :param main_count: 实际正片数
    :param trailer_count: 预告片数
    :param category_key: 频道类型（movie 特殊处理）
    :return: 1=已完结, -1=连载中, 0=未知
    """
    # 电影：有1集正片即完结
    if category_key == 'movie':
        return 1 if main_count >= 1 else 0

    info = (text or '').strip()

    # === 信号1：API 字段（最可靠）===
    if api_finished == 1:
        return 1
    if api_finished == -1:
        return -1

    # === 信号2：文本关键词 ===
    if info:
        # 纯日期格式（如 "2026-06-03"）→ 综艺还在更新
        if re.match(r'^\d{4}-\d{2}-\d{2}', info):
            return -1

        # "全X集" → 完结
        if '全' in info and '更新' not in info:
            # 需要集数确认：如果有 total，检查 main_count >= total
            if total_episodes > 0 and main_count > 0:
                return 1 if main_count >= total_episodes else -1
            return 1

        # "更新至X集" → 连载中
        if '更新至' in info or '更新到' in info:
            return -1

    # === 信号3：集数比较 ===
    if total_episodes > 0 and main_count > 0:
        if main_count >= total_episodes:
            return 1
        if main_count < total_episodes:
            return -1

    # === 信号4：预告存在性 ===
    if trailer_count > 0:
        return -1

    # === 信号5：有正片但无总集数信息 ===
    if main_count > 0 and total_episodes == 0:
        # 无法判断，返回未知
        return 0

    return 0


def judge_from_text(text: str) -> int:
    """
    纯文本快速判断（用于不需要完整参数的场景）。
    返回：1=完结, -1=连载中, 0=未知
    """
    return judge(text=text)
