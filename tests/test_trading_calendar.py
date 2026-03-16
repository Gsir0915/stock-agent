# -*- coding: utf-8 -*-
"""
动态 skip_days 测试
验证交易日逻辑是否正确
"""

import datetime
from app.utils.trading_calendar import TradingCalendar, get_skip_days, is_trading_day


def test_is_trading_day_weekday():
    """测试工作日判断"""
    # 2026-03-16 是周一
    test_date = datetime.date(2026, 3, 16)
    assert TradingCalendar.is_trading_day(test_date) == True
    print("[OK] 工作日判断正确")


def test_is_trading_day_weekend():
    """测试周末判断"""
    # 2026-03-21 是周六
    saturday = datetime.date(2026, 3, 21)
    # 2026-03-22 是周日
    sunday = datetime.date(2026, 3, 22)

    assert TradingCalendar.is_trading_day(saturday) == False
    assert TradingCalendar.is_trading_day(sunday) == False
    print("[OK] 周末判断正确")


def test_is_trading_day_holiday():
    """测试节假日判断"""
    # 2026-01-01 是元旦
    new_year = datetime.date(2026, 1, 1)

    assert TradingCalendar.is_trading_day(new_year) == False
    print("[OK] 节假日判断正确")


def test_get_skip_days_trading_day():
    """交易日 skip_days 应该是 0"""
    # 2026-03-16 是周一（交易日）
    test_date = datetime.date(2026, 3, 16)

    skip_days = TradingCalendar.get_skip_days(test_date)
    assert skip_days == 0
    print("[OK] 交易日 skip_days=0")


def test_get_skip_days_weekend():
    """非交易日 skip_days 应该大于 0"""
    # 2026-03-21 是周六
    saturday = datetime.date(2026, 3, 21)

    skip_days = TradingCalendar.get_skip_days(saturday)
    assert skip_days > 0
    print(f"[OK] 周末 skip_days={skip_days}")


def test_get_last_trading_day():
    """测试获取上一个交易日"""
    # 2026-03-21 是周六，上一个交易日应该是周五
    saturday = datetime.date(2026, 3, 21)
    last_day = TradingCalendar.get_last_trading_day(saturday)

    assert last_day.weekday() < 5  # 应该是周一到周五
    assert last_day < saturday
    print(f"[OK] 上周交易日计算正确：{saturday} -> {last_day}")


def test_get_skip_days_dynamic():
    """测试动态 skip_days 逻辑"""
    today = datetime.date.today()
    skip_days = get_skip_days()
    is_today_trading = is_trading_day()

    if is_today_trading:
        assert skip_days == 0
        print(f"[OK] 今天是交易日，skip_days=0")
    else:
        assert skip_days > 0
        print(f"[OK] 今天是非交易日，skip_days={skip_days}")


if __name__ == "__main__":
    print("=== 动态 skip_days 测试 ===\n")

    test_is_trading_day_weekday()
    test_is_trading_day_weekend()
    test_is_trading_day_holiday()
    test_get_skip_days_trading_day()
    test_get_skip_days_weekend()
    test_get_last_trading_day()
    test_get_skip_days_dynamic()

    print("\n=== 所有测试通过 ===")
