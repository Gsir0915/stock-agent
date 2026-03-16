# -*- coding: utf-8 -*-
"""
动态 skip_days 集成测试
验证数据新鲜度判断逻辑
"""

import pandas as pd
import datetime
from app.data.repository import DataRepository
from app.utils.trading_calendar import TradingCalendar


def test_repository_with_fresh_data():
    """测试数据新鲜时返回 True"""
    repo = DataRepository('data')

    # 创建一个 mock 数据，使用最新日期（今天）
    today = datetime.date.today()
    mock_df = pd.DataFrame({
        '日期': [today.strftime('%Y-%m-%d')],
        '收盘': [100.0]
    })

    # 保存 mock 数据
    repo.save_stock_data('test_fresh', mock_df)

    # 验证数据新鲜度
    is_fresh = repo.is_data_fresh('test_fresh')

    # 清理
    repo.clear_cache('test_fresh')

    if TradingCalendar.is_trading_day():
        assert is_fresh == True, "交易日今天的数据应该是新鲜的"
        print("[OK] 交易日今天的数据是新鲜的")
    else:
        # 非交易日，今天的数据也应该是新鲜的
        assert is_fresh == True
        print("[OK] 非交易日今天的数据是新鲜的")


def test_repository_with_old_data():
    """测试数据过期时返回 False"""
    repo = DataRepository('data')

    # 创建一个 mock 数据，使用 5 天前的日期
    old_date = datetime.date.today() - datetime.timedelta(days=5)
    mock_df = pd.DataFrame({
        '日期': [old_date.strftime('%Y-%m-%d')],
        '收盘': [100.0]
    })

    # 保存 mock 数据
    repo.save_stock_data('test_old', mock_df)

    # 验证数据新鲜度
    is_fresh = repo.is_data_fresh('test_old')

    # 清理
    repo.clear_cache('test_old')

    # 5 天前的数据应该过期
    assert is_fresh == False, "5 天前的数据应该过期"
    print("[OK] 5 天前的数据已过期")


def test_repository_with_weekend_data():
    """测试周末数据新鲜度判断"""
    repo = DataRepository('data')

    # 假设今天是周一，使用上周五的日期
    today = datetime.date.today()
    if today.weekday() == 0:  # 周一
        last_friday = today - datetime.timedelta(days=3)

        mock_df = pd.DataFrame({
            '日期': [last_friday.strftime('%Y-%m-%d')],
            '收盘': [100.0]
        })

        # 保存 mock 数据
        repo.save_stock_data('test_weekend', mock_df)

        # 验证数据新鲜度
        is_fresh = repo.is_data_fresh('test_weekend')

        # 清理
        repo.clear_cache('test_weekend')

        # 周一时，上周五的数据相差 3 天，而 skip_days=0（交易日必须用今日数据）
        # 所以应该判断为不新鲜
        assert is_fresh == False, "周一时上周五的数据应该不新鲜（因为 skip_days=0）"
        print("[OK] 周一时上周五的数据不新鲜（skip_days=0，必须用今日数据）")
    else:
        print(f"[SKIP] 今天不是周一，跳过测试（今天是星期{today.weekday()+1}）")


if __name__ == "__main__":
    print("=== 动态 skip_days 集成测试 ===\n")

    test_repository_with_fresh_data()
    test_repository_with_old_data()
    test_repository_with_weekend_data()

    print("\n=== 所有集成测试通过 ===")
