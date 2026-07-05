"""
数据格式标准化模块

统一各平台爬取数据的格式，确保入库前数据一致性。
"""
import re
import json
import logging

logger = logging.getLogger('vbox.normalize')


def normalize_actors(actors) -> str:
    """
    统一演员格式为 JSON 数组字符串。

    接受：list, JSON string, 逗号/顿号分隔字符串
    返回：JSON array string，空值返回 '[]'
    """
    if not actors:
        return '[]'

    # 已经是 JSON 数组
    if isinstance(actors, list):
        cleaned = [str(a).strip() for a in actors if a and str(a).strip()]
        return json.dumps(cleaned, ensure_ascii=False)

    if isinstance(actors, str):
        # 尝试 JSON 解析
        if actors.startswith('['):
            try:
                parsed = json.loads(actors)
                if isinstance(parsed, list):
                    cleaned = [str(a).strip() for a in parsed if a and str(a).strip()]
                    return json.dumps(cleaned, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

        # 逗号/顿号/空格分隔
        parts = re.split(r'[,，、\s]+', actors.strip())
        cleaned = [p.strip() for p in parts if p.strip()]
        return json.dumps(cleaned, ensure_ascii=False) if cleaned else '[]'

    return '[]'


def normalize_area(area: str) -> str:
    """
    统一地区格式。
    - 去除首尾空白
    - 空值返回 ''
    - 多个地区用逗号分隔（保留原样）
    """
    if not area or not isinstance(area, str):
        return ''
    return area.strip()


def normalize_tags(tags) -> list:
    """
    统一标签格式为 list。

    接受：list, JSON string, 逗号分隔字符串
    返回：list，空值返回 []
    """
    if not tags:
        return []

    if isinstance(tags, list):
        return [str(t).strip() for t in tags if t and str(t).strip()]

    if isinstance(tags, str):
        if tags.startswith('['):
            try:
                parsed = json.loads(tags)
                if isinstance(parsed, list):
                    return [str(t).strip() for t in parsed if t and str(t).strip()]
            except (json.JSONDecodeError, TypeError):
                pass
        parts = re.split(r'[,，、]+', tags.strip())
        return [p.strip() for p in parts if p.strip()]

    return []


def normalize_score(score) -> str:
    """
    统一评分为字符串。
    - 数字 → 字符串
    - 空/None → ''
    """
    if score is None or score == '' or score == 0:
        return ''
    try:
        return str(float(score))
    except (ValueError, TypeError):
        return str(score).strip()


def normalize_directors(directors) -> str:
    """
    统一导演格式为 JSON 数组字符串（与演员格式一致）。
    """
    return normalize_actors(directors)  # 逻辑相同


def infer_area_from_lang_and_actors(tags: list, actors_str: str) -> str:
    """
    当 area 字段为空时，从语言标签和演员名字推断地区。

    :param tags: 标签列表
    :param actors_str: 演员 JSON 字符串
    :return: 推断的地区，无法推断返回 ''
    """
    # 语言→地区映射
    LANG_AREA_MAP = {
        '普通话': '中国大陆', '国语': '中国大陆', '华语': '中国大陆',
        '粤语': '中国香港',
        '韩语': '韩国',
        '日语': '日本',
    }

    # 1. 从语言标签推断
    for tag in (tags or []):
        if tag in LANG_AREA_MAP:
            return LANG_AREA_MAP[tag]

    # 2. 从演员名推断
    if not actors_str:
        return ''

    try:
        actor_list = json.loads(actors_str) if isinstance(actors_str, str) else actors_str
    except Exception:
        return ''

    if not actor_list:
        return ''

    # 含间隔号（·）的名字判定为外国人名译名
    foreign_count = sum(1 for a in actor_list if '·' in a or '\u00b7' in a)
    total = len(actor_list)

    if total == 0:
        return ''
    if foreign_count > total / 2:
        return '欧美'
    if foreign_count == 0:
        return '中国大陆'
    return ''
