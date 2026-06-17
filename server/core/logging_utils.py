"""
用户操作日志工具
提供记录用户操作日志的功能
"""
from typing import Optional, Dict, Any
from datetime import datetime
import json
from models import UserLog, get_session
from core.logger import setup_logger

logger = setup_logger('user_actions')


def log_user_action(
    user_id: Optional[int],
    action_type: str,
    action_detail: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = 'success'
):
    """
    记录用户操作日志
    
    Args:
        user_id: 用户ID（游客可为None）
        action_type: 操作类型（login, register, logout, password_reset等）
        action_detail: 操作详情（字典格式）
        ip_address: IP地址
        user_agent: User-Agent
        status: 状态（success, failed）
    """
    try:
        with get_session() as session:
            # 准备操作详情
            detail_json = None
            if action_detail:
                try:
                    detail_json = json.dumps(action_detail, ensure_ascii=False)
                except Exception:
                    detail_json = str(action_detail)
            
            # 创建日志记录
            log_record = UserLog(
                user_id=user_id,
                action_type=action_type,
                action_detail=detail_json,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                created_at=datetime.utcnow()  # 这里直接使用UTC时间，避免时区问题
            )
            session.add(log_record)
            session.flush()
            
            # 同时也记录到日志文件
            log_msg = f"UserAction: user={user_id}, action={action_type}, status={status}"
            if ip_address:
                log_msg += f", ip={ip_address}"
            logger.info(log_msg)
            
            return log_record.id
            
    except Exception as e:
        # 记录日志失败不影响主流程
        logger.error(f"Failed to log user action: {e}")
        return None
