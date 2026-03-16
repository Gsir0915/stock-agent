# -*- coding: utf-8 -*-
"""
A 股交易日工具
判断给定日期是否为 A 股交易日
"""

import datetime
from typing import Optional
import akshare as ak


# A 股法定节假日（需要每年更新）
# 格式：YYYY-MM-DD
HOLIDAYS = {
    # 2026 年
    "2026-01-01",  # 元旦
    "2026-02-17",  # 春节
    "2026-02-18",  # 春节
    "2026-02-19",  # 春节
    "2026-02-20",  # 春节
    "2026-04-05",  # 清明
    "2026-04-06",  # 清明调休
    "2026-05-01",  # 劳动节
    "2026-05-02",  # 劳动节
    "2026-05-03",  # 劳动节
    "2026-06-19",  # 端午节
    "2026-09-25",  # 中秋节
    "2026-10-01",  # 国庆节
    "2026-10-02",  # 国庆节
    "2026-10-03",  # 国庆节
    "2026-10-04",  # 国庆节
    "2026-10-05",  # 国庆节
    # 2025 年
    "2025-01-01",  # 元旦
    "2025-01-28",  # 春节
    "2025-01-29",  # 春节
    "2025-01-30",  # 春节
    "2025-01-31",  # 春节
    "2025-02-01",  # 春节
    "2025-02-02",  # 春节
    "2025-02-03",  # 春节
    "2025-02-04",  # 春节
    "2025-04-04",  # 清明
    "2025-05-01",  # 劳动节
    "2025-05-02",  # 劳动节
    "2025-05-03",  # 劳动节
    "2025-05-04",  # 劳动节
    "2025-05-05",  # 劳动节
    "2025-06-02",  # 端午节
    "2025-10-01",  # 国庆节
    "2025-10-02",  # 国庆节
    "2025-10-03",  # 国庆节
    "2025-10-04",  # 国庆节
    "2025-10-05",  # 国庆节
    "2025-10-06",  # 国庆节
}


class TradingCalendar:
    """A 股交易日日历类"""

    # 缓存：日期 -> 是否交易日
    _cache: dict[str, bool] = {}

    @classmethod
    def is_trading_day(cls, date: Optional[datetime.date] = None) -> bool:
        """
        判断给定日期是否为 A 股交易日

        Args:
            date: 日期，默认为今天

        Returns:
            True 如果是交易日
        """
        if date is None:
            date = datetime.date.today()

        # 检查缓存
        date_str = date.strftime("%Y-%m-%d")
        if date_str in cls._cache:
            return cls._cache[date_str]

        # 1. 检查是否是周末
        if date.weekday() >= 5:  # 5=周六，6=周日
            cls._cache[date_str] = False
            return False

        # 2. 检查是否是法定节假日
        if date_str in HOLIDAYS:
            cls._cache[date_str] = False
            return False

        # 3. 默认是交易日
        cls._cache[date_str] = True
        return True

    @classmethod
    def is_weekend(cls, date: Optional[datetime.date] = None) -> bool:
        """
        判断给定日期是否是周末

        Args:
            date: 日期，默认为今天

        Returns:
            True 如果是周末
        """
        if date is None:
            date = datetime.date.today()
        return date.weekday() >= 5

    @classmethod
    def get_last_trading_day(cls, date: Optional[datetime.date] = None) -> datetime.date:
        """
        获取给定日期之前的最后一个交易日

        Args:
            date: 日期，默认为今天

        Returns:
            最后一个交易日
        """
        if date is None:
            date = datetime.date.today()

        current = date

        # 最多向前查找 7 天（覆盖周末 + 单日假期）
        for _ in range(7):
            if cls.is_trading_day(current):
                return current
            current -= datetime.timedelta(days=1)

        # 如果今天就是交易日，返回今天
        return date

    @classmethod
    def get_skip_days(cls, date: Optional[datetime.date] = None) -> int:
        """
        获取允许的 skip_days 值

        逻辑：
        - 如果是交易日：skip_days = 0（必须用今日数据）
        - 如果是非交易日：skip_days = 距离上次交易日的天数

        Args:
            date: 日期，默认为今天

        Returns:
            skip_days 值
        """
        if date is None:
            date = datetime.date.today()

        if cls.is_trading_day(date):
            return 0

        # 非交易日，计算距离上次交易日的天数
        last_trading_day = cls.get_last_trading_day(date)
        days_diff = (date - last_trading_day).days

        # 最多允许 3 天（覆盖长假期）
        return min(days_diff, 3)

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        cls._cache.clear()


# 便捷函数
def is_trading_day(date: Optional[datetime.date] = None) -> bool:
    """判断是否为交易日"""
    return TradingCalendar.is_trading_day(date)


def get_skip_days(date: Optional[datetime.date] = None) -> int:
    """获取 skip_days 值"""
    return TradingCalendar.get_skip_days(date)


def get_last_trading_day(date: Optional[datetime.date] = None) -> datetime.date:
    """获取上一个交易日"""
    return TradingCalendar.get_last_trading_day(date)
