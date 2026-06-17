"""
JWT 认证模块
提供 token 生成、验证、刷新等功能
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7天

# 开发模式开关（用于跳过验证码等）
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据，通常包含 user_id
        expires_delta: 过期时间增量

    Returns:
        JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建刷新令牌

    Args:
        data: 要编码的数据，通常包含 user_id
        expires_delta: 过期时间增量

    Returns:
        JWT refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 token

    Args:
        token: JWT token

    Returns:
        解码后的数据，如果验证失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        import logging
        logging.getLogger('vbox.api').warning(f"JWT decode failed: {e}")
        return None


def verify_access_token(token: str) -> Optional[int]:
    """
    验证访问令牌

    Args:
        token: JWT access token

    Returns:
        用户 ID，如果验证失败返回 None
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id: int = payload.get("sub")
    return user_id


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证刷新令牌

    Args:
        token: JWT refresh token

    Returns:
        用户 ID，如果验证失败返回 None
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    user_id: int = payload.get("sub")
    return user_id


def refresh_tokens(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    使用刷新令牌获取新的访问令牌和刷新令牌

    Args:
        refresh_token: JWT refresh token

    Returns:
        包含 access_token 和 refresh_token 的字典，失败返回 None
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

