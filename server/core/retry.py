
"""
重试机制封装
使用指数退避策略处理网络请求失败
"""
import time
import functools
from core.logger import setup_logger

logger = setup_logger('vbox.retry')


def retry_request(func, max_retries=3, base_delay=1, max_delay=10, exceptions=(Exception,)):
    """
    重试装饰器/包装器

    :param func: 要执行的函数
    :param max_retries: 最大重试次数
    :param base_delay: 基础延迟时间（秒）
    :param max_delay: 最大延迟时间（秒）
    :param exceptions: 需要捕获的异常类型
    :return: 函数执行结果
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(f"第{attempt}次尝试失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数({max_retries}), 最后错误: {e}")

        raise last_exception

    return wrapper


class RetryHelper:
    """重试辅助类"""

    @staticmethod
    def with_retry(func, *args, max_retries=3, base_delay=1, max_delay=10,
                   exceptions=(Exception,), **kwargs):
        """
        带重试地执行函数

        :param func: 要执行的函数
        :param args: 位置参数
        :param max_retries: 最大重试次数
        :param base_delay: 基础延迟
        :param max_delay: 最大延迟
        :param exceptions: 需要捕获的异常类型元组
        :param kwargs: 转发给 func 的关键字参数
        :return: 函数执行结果
        """
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(f"{func.__name__} 第{attempt}次尝试失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"{func.__name__} 达到最大重试次数({max_retries})")

        raise last_exception
