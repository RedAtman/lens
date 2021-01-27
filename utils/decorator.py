import time
from lens.utils import logger

__all__ = [
    'timer'
]


def timer(func):
    """
    装饰器函数timer
    :param func:想要计时的函数
    :return:
    """

    def wrapper(*args, **kwargs):
        time_start = time.time()
        res = func(*args, **kwargs)
        cost_time = time.time() - time_start
        logger.info("(%s)运行时间:(%s)秒" % (func.__name__, cost_time))
        return res

    return wrapper
