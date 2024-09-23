# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import sys


class DateUtils:

    @staticmethod
    def now_time() -> str:
        """返回当前日期时间

        Returns:
            str: 当前日期时间
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def preday_time() -> str:
        """返回前一天的日期时间

        Returns:
            str: 前一天的日期时间
        """
        now_time = datetime.now()
        previous_time = now_time - timedelta(days=1)
        return previous_time.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_hour(time):
        t = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        return t.hour

    @staticmethod
    def datetime_to_str(datetime):
        return datetime.strftime('%Y-%m-%d %H:%M:%S')