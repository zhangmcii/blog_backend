# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from functools import wraps
import time
import pytz


class DateUtils:
    Shanghai_tz = pytz.timezone('Asia/Shanghai')

    @staticmethod
    def now_time() -> str:
        """返回当前日期时间

        Returns:
            str: 当前日期时间
        """
        return datetime.now(DateUtils.Shanghai_tz).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def preday_time() -> str:
        """返回前一天的日期时间

        Returns:
            str: 前一天的日期时间
        """
        now_time = datetime.now(DateUtils.Shanghai_tz)
        previous_time = now_time - timedelta(days=1)
        return previous_time.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_hour(time):
        t = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        return t.hour

    @staticmethod
    def datetime_to_str(date_time):
        return date_time.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def datetime_diff(t1: str, t2: str, diff: int):
        """比较两个datetime对象时间间隔 大于某个分钟数

        Returns:
            bool: 是否大于diff分钟
        """
        r1 = datetime.strptime(t1, '%Y-%m-%d %H:%M:%S')
        r2 = datetime.strptime(t2, '%Y-%m-%d %H:%M:%S')
        return abs(r1 - r2) > timedelta(minutes=diff)

    @staticmethod
    def record_time(func):
        """记录函数执行时间"""
        @wraps(func)
        def decorate(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            name = func.__name__
            arg_str = ', '.join(repr(arg) for arg in args)
            print(f'[{elapsed:0.8f}s] {name}({arg_str}) -> {result!r}')
            return result

        return decorate
