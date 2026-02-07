"""
时间测量工具
"""
import time
import functools
from quantaalpha.log import logger


def measure_time(func):
    """装饰器：测量函数执行时间"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} 耗时: {elapsed:.2f}秒")
        return result
    return wrapper
