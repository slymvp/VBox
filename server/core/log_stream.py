
"""
实时日志流处理器
支持 Server-Sent Events 推送日志，支持任务关联
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque


class MemoryLogHandler(logging.Handler):
    """内存日志处理器，用于收集和存储日志"""

    def __init__(self, max_logs: int = 1000):
        super().__init__()
        self.max_logs = max_logs
        self.logs: deque = deque(maxlen=max_logs)
        self.lock = threading.Lock()
        # 使用threading.local()让每个线程有自己独立的task_id
        self.local = threading.local()
        self.local.current_task_id = None
        # 简单的格式化器
        self.setFormatter(logging.Formatter('%(message)s'))

    def set_task_id(self, task_id: Optional[int]):
        """设置当前任务ID，用于关联日志"""
        self.local.current_task_id = task_id

    def emit(self, record: logging.LogRecord):
        """处理日志记录"""
        try:
            # 获取当前线程的task_id
            current_task_id = getattr(self.local, 'current_task_id', None)
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'name': record.name,
                'message': self.format(record),
                'line': record.lineno,
                'task_id': current_task_id,
            }

            with self.lock:
                self.logs.append(log_entry)

            # 如果有任务ID，保存到数据库
            if current_task_id:
                self._save_to_db(current_task_id, record.levelname, self.format(record))
        except Exception:
            self.handleError(record)

    def _save_to_db(self, task_id: int, level: str, message: str):
        """保存日志到数据库 - 使用原生sqlite3，避免子进程中SQLAlchemy的问题"""
        try:
            import sqlite3
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'vbox.db')
            db_path = os.path.abspath(db_path)
            
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            from datetime import datetime, timedelta
            def utc_plus_8():
                now = datetime.utcnow() + timedelta(hours=8)
                return now.replace(microsecond=0).isoformat()
            
            created_at = utc_plus_8()
            cursor.execute(
                'INSERT INTO crawl_task_logs (task_id, level, message, created_at) VALUES (?, ?, ?, ?)',
                (task_id, level, message, created_at)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[LOG_SAVE_ERROR] 保存任务日志失败: task_id={task_id}, error={str(e)}")
            import traceback
            traceback.print_exc()

    def get_logs(self, since_timestamp: str = None, task_id: int = None) -> List[Dict[str, Any]]:
        """获取日志"""
        with self.lock:
            logs_list = list(self.logs)
            if task_id:
                logs_list = [log for log in logs_list if log.get('task_id') == task_id]
            if since_timestamp:
                logs_list = [log for log in logs_list if log['timestamp'] > since_timestamp]
            return logs_list


# 全局日志处理器实例
_memory_handler: Optional[MemoryLogHandler] = None
_init_lock = threading.Lock()


def get_memory_log_handler(max_logs: int = 1000) -> MemoryLogHandler:
    """获取全局内存日志处理器"""
    global _memory_handler
    with _init_lock:
        if _memory_handler is None:
            _memory_handler = MemoryLogHandler(max_logs)
            # 直接附加到 root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(_memory_handler)
            # 也附加到 uvicorn logger
            for logger_name in ['uvicorn', 'uvicorn.error', 'uvicorn.access']:
                lgr = logging.getLogger(logger_name)
                lgr.addHandler(_memory_handler)
    return _memory_handler


def cleanup_old_logs(days: int = 10):
    """清理指定天数之前的旧日志"""
    try:
        from models import TaskCrawlLog, get_session
        cutoff_date = datetime.utcnow() + timedelta(hours=8) - timedelta(days=days)
        with get_session() as session:
            deleted = session.query(TaskCrawlLog).filter(
                TaskCrawlLog.created_at < cutoff_date
            ).delete(synchronize_session=False)
            return deleted
    except Exception as e:
        print(f"清理旧日志失败: {e}")
        return 0

