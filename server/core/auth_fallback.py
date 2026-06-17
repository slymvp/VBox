"""
临时认证模块（当 python-jose 未安装时使用）
"""
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 开发模式开关
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码（临时使用简单比较，生产环境请使用 bcrypt）
    """
    # 简单比较（临时方案）
    return plain_password == hashed_password or hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """
    获取密码哈希（临时使用 SHA-256，生产环境请使用 bcrypt）
    """
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌（临时使用简单哈希，生产环境请使用 JWT）
    """
    if expires_delta:
        expire = time.time() + expires_delta.total_seconds()
    else:
        expire = time.time() + (24 * 60 * 60)  # 24 小时
    
    # 创建一个简单的 token 结构
    token_data = {
        "sub": data.get("sub"),
        "exp": expire,
        "type": "access"
    }
    
    # 简单编码（临时方案）
    import json
    import base64
    token_str = json.dumps(token_data)
    token_bytes = token_str.encode('utf-8')
    token_b64 = base64.b64encode(token_bytes).decode('utf-8')
    
    # 添加签名（临时方案）
    secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-please")
    signature = hashlib.md5(f"{token_b64}{secret}".encode()).hexdigest()
    
    return f"{token_b64}.{signature}"


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建刷新令牌（临时使用简单哈希，生产环境请使用 JWT）
    """
    if expires_delta:
        expire = time.time() + expires_delta.total_seconds()
    else:
        expire = time.time() + (7 * 24 * 60 * 60)  # 7 天
    
    # 创建一个简单的 token 结构
    token_data = {
        "sub": data.get("sub"),
        "exp": expire,
        "type": "refresh"
    }
    
    # 简单编码（临时方案）
    import json
    import base64
    token_str = json.dumps(token_data)
    token_bytes = token_str.encode('utf-8')
    token_b64 = base64.b64encode(token_bytes).decode('utf-8')
    
    # 添加签名（临时方案）
    secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-please")
    signature = hashlib.md5(f"{token_b64}{secret}".encode()).hexdigest()
    
    return f"{token_b64}.{signature}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 token（临时方案）
    """
    try:
        import json
        import base64
        
        # 分割 token 和签名
        if '.' not in token:
            return None
        
        token_b64, signature = token.split('.', 1)
        
        # 验证签名
        secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-please")
        expected_signature = hashlib.md5(f"{token_b64}{secret}".encode()).hexdigest()
        
        if signature != expected_signature:
            return None
        
        # 解码
        token_bytes = base64.b64decode(token_b64.encode('utf-8'))
        token_str = token_bytes.decode('utf-8')
        payload = json.loads(token_str)
        
        # 检查过期
        if payload.get("exp", 0) < time.time():
            return None
        
        return payload
    except Exception:
        return None


def verify_access_token(token: str) -> Optional[int]:
    """
    验证访问令牌（临时方案）
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证刷新令牌（临时方案）
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload.get("sub")


def refresh_tokens(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    使用刷新令牌获取新的访问令牌和刷新令牌（临时方案）
    """
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        return None
    
    new_access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }
