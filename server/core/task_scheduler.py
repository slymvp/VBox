
"""
爬虫任务调度器（多进程版本）
- 全局并发数 = 活跃平台数 × 2（动态计算）
- 同一平台最多2个进程并发
- 每个频道作为独立任务
"""
import multiprocessing
import threading
import uuid
import time
import logging
from datetime import datetime
from enum import Enum

# 导入UTC+8时间函数
def utc_plus_8():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone.utc) + timedelta(hours=8)

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChannelTask:
    """频道级别的爬虫任务"""
    
    def __init__(self, task_id, parent_task_id, platform_key, channel_key, max_items, task_type, scheduled_task_id, status, created_at, sort=None):
        self.task_id = task_id
        self.parent_task_id = parent_task_id
        self.platform_key = platform_key
        self.channel_key = channel_key
        self.max_items = max_items
        self.task_type = task_type
        self.scheduled_task_id = scheduled_task_id
        self.status = status
        self.created_at = created_at
        self.sort = sort
        self.started_at = None
        self.completed_at = None
        self.error = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "platform_key": self.platform_key,
            "channel_key": self.channel_key,
            "task_type": self.task_type,
            "sort": getattr(self, 'sort', None),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


def _worker_process(task_dict):
    """
    工作进程的主函数（独立进程中运行）
    这是顶层函数，避免pickle问题
    """
    import sys
    import os
    
    server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    sys.path.insert(0, server_dir)
    
    from core.config import Config
    from core.logger import setup_logger
    from core.database import DatabaseManager
    from main import crawl_platform
    
    setup_logger()
    config = Config()  # 使用默认配置路径
    
    task = task_dict
    logger.info("[进程 %s] 开始执行: %s-%s", os.getpid(), task.get('platform_key'), task.get('channel_key'))
    
    try:
        if task.get('task_type') == 'scheduled' and task.get('scheduled_task_id'):
            try:
                DatabaseManager.update_scheduled_task_last_run(task.get('scheduled_task_id'))
            except Exception as e:
                logger.warning("更新任务最后运行时间失败: %s", e)
        
        crawl_platform(
            task.get('platform_key'),
            task.get('channel_key'),
            max_items=task.get('max_items'),
            db_task_id=task.get('db_task_id'),
            sort=task.get('sort')
        )
        
        logger.info("[进程 %s] 完成: %s-%s", os.getpid(), task.get('platform_key'), task.get('channel_key'))
        return {"success": True}
        
    except Exception as e:
        logger.error("[进程 %s] 失败: %s", os.getpid(), e, exc_info=True)
        return {"success": False, "error": str(e)}


class ProcessTaskScheduler:
    """多进程任务调度器"""
    _instance = None
    _lock = threading.Lock()

    def __init__(self, per_platform_max_concurrent=2):
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.platform_max = per_platform_max_concurrent
        # 全局最大并发数会根据活跃平台数动态计算，初始给个默认值
        self.global_max = 12
        
        self.task_queue = []
        self.tasks = {}
        self.platform_running = {}
        self.active_processes = {}
        self.state_lock = threading.Lock()
        self._running = False
        self._scheduler_thread = None
        self.db_path = ""
        self.config_path = ""
        self.db_manager = None
        
        logger.info("调度器初始化: 平台并发=%s, 全局并发将动态计算", per_platform_max_concurrent)
    
    def initialize(self, db_path=None, config_path=None):
        """初始化路径配置和数据库管理器"""
        self.db_path = db_path
        self.config_path = config_path
        # 创建数据库管理器实例
        from core.database import DatabaseManager
        self.db_manager = DatabaseManager()
        # 初始化时计算一次全局最大并发数
        self._update_global_max_concurrent()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def submit_task(
        self,
        platform_key,
        channel_keys=None,
        channel_key=None,
        channels=None,
        max_items=10,
        task_type="manual",
        scheduled_task_id=None,
        sort=None
    ):
        from core.config import Config
        config = Config()
        
        # 从数据库获取有效的频道列表（唯一数据源）
        if platform_key == "all":
            valid_channels = {}
            for p in config.get_platforms().keys():
                valid_channels[p] = set(config.get_channels(p).keys())
        else:
            valid_channels = {platform_key: set(config.get_channels(platform_key).keys())}
        
        all_channels = []
        if channel_keys:
            all_channels = channel_keys
        elif channel_key:
            all_channels = [channel_key]
        elif channels:
            all_channels = channels
        else:
            if platform_key == "all":
                platform_list = list(config.get_platforms().keys())
                for p in platform_list:
                    all_channels.extend(["%s:%s" % (p, ch) for ch in config.get_channels(p).keys()])
            else:
                all_channels = list(config.get_channels(platform_key).keys())
        
        parent_task_id = str(uuid.uuid4())
        task_ids = []
        
        with self.state_lock:
            # 先清理已完成的任务（保留最近100个）
            self._cleanup_old_completed_tasks()
            
            for ch in all_channels:
                if platform_key == "all" and ":" in ch:
                    p_key, c_key = ch.split(":", 1)
                else:
                    p_key = platform_key
                    c_key = ch
                
                # 防线：跳过数据库中不存在的频道（防止外部硬编码、定时任务残留等绕过）
                if p_key in valid_channels and c_key not in valid_channels[p_key]:
                    logger.warning("跳过无效频道（数据库无此配置）: %s-%s", p_key, c_key)
                    continue
                
                # 检查是否已有相同的任务在队列中或正在运行（去重）
                is_duplicate = False
                for existing_task in self.tasks.values():
                    if (existing_task.platform_key == p_key and 
                        existing_task.channel_key == c_key and 
                        existing_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]):
                        is_duplicate = True
                        logger.info("跳过重复任务: %s-%s, 任务已存在", p_key, c_key)
                        break
                
                if is_duplicate:
                    continue
                
                # 在数据库创建任务记录
                db_task_id = None
                if self.db_manager:
                    db_task_id = self.db_manager.create_crawl_task(p_key, c_key)
                
                task_id = str(uuid.uuid4())
                task = ChannelTask(
                    task_id=task_id,
                    parent_task_id=parent_task_id,
                    platform_key=p_key,
                    channel_key=c_key,
                    max_items=max_items,
                    task_type=task_type,
                    scheduled_task_id=scheduled_task_id,
                    status=TaskStatus.PENDING,
                    created_at=datetime.now(),
                    sort=sort
                )
                task.db_task_id = db_task_id  # 记录数据库的任务ID
                self.tasks[task_id] = task
                self.task_queue.append(task_id)
                task_ids.append(task_id)
                logger.info("任务已提交: %s-%s, ID=%s, DB_ID=%s", p_key, c_key, task_id, db_task_id)
        
        self._wake_scheduler()
        return task_ids
    
    def _cleanup_old_completed_tasks(self):
        """清理旧的已完成任务，只保留最近的100个"""
        completed_tasks = [
            task for task in self.tasks.values() 
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        ]
        
        if len(completed_tasks) > 100:
            # 按完成时间排序，保留最近的100个
            completed_tasks.sort(
                key=lambda x: x.completed_at or x.created_at,
                reverse=True
            )
            tasks_to_remove = completed_tasks[100:]
            
            for task in tasks_to_remove:
                if task.task_id in self.tasks:
                    del self.tasks[task.task_id]
            
            logger.info("已清理 %s 个旧的已完成任务", len(tasks_to_remove))

    def _update_global_max_concurrent(self):
        """
        根据实际配置的平台数动态计算全局最大并发数
        全局最大并发 = 活跃平台数 × 平台最大并发
        """
        try:
            # 从数据库获取有配置频道的平台列表
            active_platform_count = 6  # 默认值
            if self.db_manager:
                try:
                    platforms = self.db_manager.list_platforms()
                    if platforms:
                        # 统计有至少一个频道配置的平台
                        active_platforms = []
                        platform_channels = self.db_manager.list_platform_channels()
                        
                        # 构建平台ID集合
                        platform_ids_with_channels = set()
                        for pc in platform_channels:
                            if pc.get('platform_id'):
                                platform_ids_with_channels.add(pc['platform_id'])
                        
                        # 统计有频道的平台数量
                        active_platform_count = len(platform_ids_with_channels)
                        
                        # 如果没有从数据库获取到数据，用默认值
                        if active_platform_count == 0:
                            active_platform_count = 6
                except Exception as e:
                    logger.warning("获取平台配置失败，使用默认值: %s", e)
                    active_platform_count = 6
            
            # 计算全局最大并发数：活跃平台数 × 2
            old_global_max = self.global_max
            self.global_max = active_platform_count * self.platform_max
            
            if self.global_max != old_global_max:
                logger.info("全局最大并发数已更新: %s -> %s (活跃平台数=%s, 平台并发=%s)",
                          old_global_max, self.global_max, active_platform_count, self.platform_max)
            
        except Exception as e:
            logger.error("更新全局最大并发数失败: %s", e)
    
    def _wake_scheduler(self):
        # 在唤醒调度器前更新一下全局并发数
        self._update_global_max_concurrent()
        
        if not self._running:
            return
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def start(self):
        self._running = True
        self._wake_scheduler()
        logger.info("调度器已启动")

    def stop(self, wait=True):
        self._running = False
        
        if wait and self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        
        for task_id, proc in list(self.active_processes.items()):
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2)
        
        logger.info("调度器已停止")
    
    def stop_task(self, task_id):
        """停止指定的任务"""
        with self.state_lock:
            # 首先检查是否是等待中的任务
            if task_id in self.task_queue:
                try:
                    self.task_queue.remove(task_id)
                except ValueError:
                    pass
                
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error = "用户手动停止"
                    task.completed_at = datetime.now()
                logger.info("已移除等待中的任务: %s", task_id)
                return True
            
            # 检查是否是运行中的任务
            if task_id in self.active_processes:
                proc = self.active_processes[task_id]
                if proc.is_alive():
                    try:
                        proc.terminate()
                        proc.join(timeout=3)
                    except Exception as e:
                        logger.warning("停止任务时异常: %s", e)
                        try:
                            proc.kill()
                            proc.join(timeout=1)
                        except Exception as e2:
                            logger.error("强制结束任务失败: %s", e2)
                
                # 更新任务状态
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error = "用户手动停止"
                    task.completed_at = datetime.now()
                
                # 更新平台运行计数
                if task and task.platform_key in self.platform_running:
                    count = self.platform_running.get(task.platform_key, 0)
                    if count > 0:
                        self.platform_running[task.platform_key] = count - 1
                
                # 从active_processes中移除
                if task_id in self.active_processes:
                    del self.active_processes[task_id]
                
                logger.info("已停止运行中的任务: %s", task_id)
                return True
            
            logger.warning("任务不存在或已完成: %s", task_id)
            return False
    
    def stop_all_running(self):
        """停止所有运行中的任务"""
        with self.state_lock:
            stopped_count = 0
            
            # 清理等待队列
            self.task_queue.clear()
            
            # 停止所有运行中的进程
            for task_id, proc in list(self.active_processes.items()):
                if proc.is_alive():
                    try:
                        proc.terminate()
                        proc.join(timeout=3)
                    except Exception as e:
                        logger.warning("停止任务时异常: %s", e)
                        try:
                            proc.kill()
                            proc.join(timeout=1)
                        except Exception as e2:
                            logger.error("强制结束任务失败: %s", e2)
                
                # 更新任务状态
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error = "用户手动停止"
                    task.completed_at = datetime.now()
                    stopped_count += 1
            
            # 清空运行中的进程
            self.active_processes.clear()
            self.platform_running.clear()
            
            logger.info("已停止所有 %s 个运行中的任务", stopped_count)
            return stopped_count

    def _scheduler_loop(self):
        logger.info("调度循环启动")
        
        while self._running:
            try:
                self._try_start_tasks()
                self._cleanup_completed()
                self._check_task_timeouts()  # 检查超时任务并强制终止
                time.sleep(0.5)
            except Exception as e:
                logger.error("调度循环异常: %s", e, exc_info=True)
                time.sleep(1)

    def _try_start_tasks(self):
        with self.state_lock:
            current_global = len(self.active_processes)
            task_ids_to_start = []
            remaining_tasks = []
            
            for task_id in self.task_queue:
                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                platform_count = self.platform_running.get(task.platform_key, 0)
                
                if current_global < self.global_max and platform_count < self.platform_max:
                    task_ids_to_start.append(task_id)
                    current_global += 1
                    self.platform_running[task.platform_key] = platform_count + 1
                else:
                    remaining_tasks.append(task_id)
            
            self.task_queue = remaining_tasks
        
        # 在锁外启动任务，减少锁持有时间
        for task_id in task_ids_to_start:
            self._start_task(task_id)

    def _start_task(self, task_id):
        with self.state_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        # 更新数据库中的任务状态为 running
        if hasattr(task, 'db_task_id') and task.db_task_id and self.db_manager:
            try:
                self.db_manager.start_crawl_task(task.db_task_id)
            except Exception as e:
                logger.error("更新数据库任务状态失败: %s", e)
        
        task_dict = {
            "task_id": task.task_id,
            "db_task_id": getattr(task, 'db_task_id', None),
            "platform_key": task.platform_key,
            "channel_key": task.channel_key,
            "max_items": task.max_items,
            "task_type": task.task_type,
            "scheduled_task_id": task.scheduled_task_id,
            "sort": getattr(task, 'sort', None)
        }
        
        proc = multiprocessing.Process(
            target=_worker_process,
            args=(task_dict,),
            daemon=True
        )
        
        with self.state_lock:
            self.active_processes[task_id] = proc
        
        proc.start()
        logger.info("进程已启动: PID=%s, Task=%s-%s", proc.pid, task.platform_key, task.channel_key)

    def _cleanup_completed(self):
        completed_task_ids = []
        
        with self.state_lock:
            for task_id, proc in list(self.active_processes.items()):
                if not proc.is_alive():
                    task = self.tasks.get(task_id)
                    if task:
                        exitcode = proc.exitcode
                        if exitcode == 0:
                            task.status = TaskStatus.COMPLETED
                        else:
                            task.status = TaskStatus.FAILED
                            task.error = "进程异常退出: %s" % exitcode
                        
                        task.completed_at = datetime.now()
                        
                        count = self.platform_running.get(task.platform_key, 0)
                        if count > 0:
                            self.platform_running[task.platform_key] = count - 1
                        
                        # 注意：数据库状态由 crawl_platform 函数处理，这里不需要重复更新
                    
                    completed_task_ids.append(task_id)
            
            for task_id in completed_task_ids:
                if task_id in self.active_processes:
                    del self.active_processes[task_id]
        
        if completed_task_ids:
            logger.info("已完成 %s 个任务", len(completed_task_ids))

    def _check_task_timeouts(self, timeout_seconds=1800):
        """检查运行中的任务是否超时，超时则强制终止（默认30分钟）"""
        now = datetime.now()
        timed_out_ids = []
        
        with self.state_lock:
            for task_id, proc in list(self.active_processes.items()):
                if not proc.is_alive():
                    continue  # 已完成的会在 _cleanup_completed 处理
                
                task = self.tasks.get(task_id)
                if not task or not task.started_at:
                    continue
                
                elapsed = (now - task.started_at).total_seconds()
                if elapsed > timeout_seconds:
                    timed_out_ids.append(task_id)
        
        # 在锁外终止进程，避免持有锁期间执行IO操作
        for task_id in timed_out_ids:
            self._force_stop_task(task_id, "任务超时（超过30分钟），强制终止")

    def _force_stop_task(self, task_id, error_message):
        """强制停止单个任务并更新状态"""
        proc = None
        task = None
        
        with self.state_lock:
            proc = self.active_processes.get(task_id)
            task = self.tasks.get(task_id)
        
        if not proc or not task:
            return
        
        # 终止进程
        if proc.is_alive():
            try:
                proc.terminate()
                proc.join(timeout=3)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=1)
            except Exception as e:
                logger.error("强制终止任务异常: %s", e)
        
        # 更新任务状态
        with self.state_lock:
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = error_message
                task.completed_at = datetime.now()
                
                # 更新平台运行计数
                count = self.platform_running.get(task.platform_key, 0)
                if count > 0:
                    self.platform_running[task.platform_key] = count - 1
                
                if task_id in self.active_processes:
                    del self.active_processes[task_id]
        
        # 更新数据库状态（如有db_task_id）
        db_task_id = getattr(task, 'db_task_id', None)
        if db_task_id and self.db_manager:
            try:
                self.db_manager.complete_crawl_task(db_task_id, 0, error_message)
            except Exception as e:
                logger.error("更新数据库任务状态失败: %s", e)
        
        logger.warning("已强制终止超时任务: %s-%s, 错误: %s", task.platform_key, task.channel_key, error_message)

    def get_queue_size(self):
        with self.state_lock:
            return len(self.task_queue)

    def get_all_tasks(self):
        with self.state_lock:
            running = []
            pending = []
            completed = []
            
            for task in self.tasks.values():
                task_dict = task.to_dict()
                if task.status == TaskStatus.RUNNING:
                    running.append(task_dict)
                elif task.status == TaskStatus.PENDING:
                    pending.append(task_dict)
                else:
                    completed.append(task_dict)
            
            completed.sort(key=lambda x: x.get('completed_at') or '', reverse=True)
            
            platform_running_dict = {}
            for k, v in self.platform_running.items():
                platform_running_dict[k] = v
            
            return {
                "running": running,
                "pending": pending,
                "completed": completed[:100],
                "platform_running": platform_running_dict,
                "global_active": len(self.active_processes)
            }


_scheduler_instance = None


def get_scheduler(platform_max=2):
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ProcessTaskScheduler(
            per_platform_max_concurrent=platform_max
        )
    return _scheduler_instance

