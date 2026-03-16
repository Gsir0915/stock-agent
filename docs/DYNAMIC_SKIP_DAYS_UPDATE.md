# 动态 skip_days 更新

## 概述

缓存数据新鲜度判断逻辑已从固定 `skip_days=3` 改为**根据交易日动态计算**。

## 背景

原逻辑使用固定 `skip_days=3`，导致以下问题：
- **交易日**：可以使用 3 天前的缓存，无法获取最新收盘价
- **周末/节假日**：`skip_days=3` 可能不够（如 7 天长假）

## 新逻辑

### 规则

| 日期类型 | skip_days | 说明 |
|----------|-----------|------|
| 交易日（周一 - 周五） | 0 | 必须获取今日收盘价 |
| 周六 | 1 | 可使用周五数据 |
| 周日 | 2 | 可使用周五数据 |
| 节假日 | 1-3 | 可使用上次交易日数据 |

### 实现

```python
# app/utils/trading_calendar.py

class TradingCalendar:
    @classmethod
    def get_skip_days(cls, date=None):
        if cls.is_trading_day(date):
            return 0  # 交易日必须用今日数据
        else:
            # 非交易日，计算距离上次交易日的天数
            last_day = cls.get_last_trading_day(date)
            return min((date - last_day).days, 3)
```

## 使用示例

```python
from app.data.repository import DataRepository
from app.utils.trading_calendar import TradingCalendar

repo = DataRepository('data')

# 自动根据今天是否为交易日决定 skip_days
is_fresh = repo.is_data_fresh('600519')  # skip_days=None，自动计算

# 手动指定 skip_days（不推荐）
is_fresh = repo.is_data_fresh('600519', skip_days=3)
```

## 节假日配置

节假日数据硬编码在 `HOLIDAYS` 集合中，需要每年更新：

```python
HOLIDAYS = {
    # 2026 年
    "2026-01-01",  # 元旦
    "2026-02-17",  # 春节
    ...
}
```

## 测试

```bash
# 运行单元测试
python -m tests.test_trading_calendar

# 验证逻辑
python -c "
from app.utils.trading_calendar import TradingCalendar
print(f'今天是否交易日：{TradingCalendar.is_trading_day()}')
print(f'今天的 skip_days: {TradingCalendar.get_skip_days()}')
"
```

## 相关文件

- `app/utils/trading_calendar.py` - 交易日工具类
- `app/data/repository.py` - 数据仓库（使用动态 skip_days）
- `app/core/analyzer.py` - 分析引擎（传递 skip_days=None）
- `tests/test_trading_calendar.py` - 单元测试
