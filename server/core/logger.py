
"""
统一日志系统配置
提供控制台 + 文件 + 错误文件的分级日志输出
"""
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name=None, log_file='logs/app.log', level=logging.INFO):
    """
    配置统一的日志系统

    :param name: logger名称，通常使用 __name__
    :param log_file: 日志文件路径
    :param level: 日志级别
    :return: 配置好的logger实例
    """
    logger = logging.getLogger(name or __name__)
    logger.setLevel(level)

    # 检查是否已有handler
    if logger.handlers:
        return logger

    # 格式化器
    detailed_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_fmt = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file) or '.'
    os.makedirs(log_dir, exist_ok=True)

    # 确保错误日志目录存在
    error_log_file = 'logs/error.log'
    error_log_dir = os.path.dirname(error_log_file) or '.'
    os.makedirs(error_log_dir, exist_ok=True)

    # 文件 handler（自动轮转，单个文件最大 10MB，保留 5 个备份）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_fmt)
    logger.addHandler(file_handler)

    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_fmt)
    logger.addHandler(error_handler)

    # 控制台 handler - 所有logger都添加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_fmt)
    logger.addHandler(console_handler)

    # 子logger禁用传播，避免重复输出（因为自身已有console handler）
    if name and name != 'vbox' and '.' in name:
        logger.propagate = False

    return logger


# 创建默认logger实例
logger = setup_logger('vbox')
