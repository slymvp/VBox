"""
安全防护模块
提供防暴力破解等功能
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

# 内存存储（生产环境可以使用 Redis）
_login_attempts: Dict[str, Dict] = {}


def get_client_identifier(phone: str, ip: Optional[str] = None) -> str:
    """
    生成客户端标识符，用于限制频率
    
    Args:
        phone: 手机号
        ip: IP 地址（可选）
        
    Returns:
        标识符
    """
    if ip:
        return f"{phone}:{ip}"
    return phone


def record_login_attempt(phone: str, ip: Optional[str] = None, success: bool = False) -> None:
    """
    记录登录尝试
    
    Args:
        phone: 手机号
        ip: IP 地址
        success: 是否成功
    """
    identifier = get_client_identifier(phone, ip)
    now = time.time()
    
    if identifier not in _login_attempts:
        _login_attempts[identifier] = {
            "attempts": 0,
            "last_attempt": now,
            "locked_until": 0
        }
    
    record = _login_attempts[identifier]
    
    if success:
        # 成功，清除失败记录
        record["attempts"] = 0
        record["locked_until"] = 0
    else:
        # 失败，增加计数
        record["attempts"] += 1
        record["last_attempt"] = now
        
        # 检查是否需要锁定
        if record["attempts"] >= 5:
            # 锁定 15 分钟
            record["locked_until"] = now + (15 * 60)
        elif record["attempts"] >= 3:
            # 锁定 5 分钟
            record["locked_until"] = now + (5 * 60)


def is_login_locked(phone: str, ip: Optional[str] = None) -> tuple[bool, int]:
    """
    检查是否被锁定
    
    Args:
        phone: 手机号
        ip: IP 地址
        
    Returns:
        (是否锁定, 剩余秒数)
    """
    identifier = get_client_identifier(phone, ip)
    now = time.time()
    
    if identifier not in _login_attempts:
        return False, 0
    
    record = _login_attempts[identifier]
    
    if record["locked_until"] > now:
        remaining = int(record["locked_until"] - now)
        return True, remaining
    
    # 如果已过锁定时间，重置计数
    if record["locked_until"] > 0:
        record["locked_until"] = 0
        record["attempts"] = 0
    
    return False, 0


def get_remaining_attempts(phone: str, ip: Optional[str] = None) -> int:
    """
    获取剩余尝试次数
    
    Args:
        phone: 手机号
        ip: IP 地址
        
    Returns:
        剩余尝试次数
    """
    identifier = get_client_identifier(phone, ip)
    
    if identifier not in _login_attempts:
        return 5
    
    record = _login_attempts[identifier]
    max_attempts = 5
    return max(0, max_attempts - record["attempts"])


def cleanup_old_records() -> None:
    """
    清理旧的记录（超过 24 小时的）
    """
    now = time.time()
    cutoff = now - (24 * 60 * 60)  # 24 小时前
    
    to_delete = []
    for identifier, record in _login_attempts.items():
        if record["last_attempt"] < cutoff:
            to_delete.append(identifier)
    
    for identifier in to_delete:
        del _login_attempts[identifier]

