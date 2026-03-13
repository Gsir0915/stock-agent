---
name: turtle-scan
description: 使用海龟交易法则扫描股票，检查突破信号和建议头寸
---

# 海龟交易法则选股

使用海龟交易法则扫描股票，检查 20 日突破信号和 ATR 趋势。

## 用法

**检查单只股票**
```bash
python -m app.main turtle-screener check $1
```

**扫描默认股票池**
```bash
python -m app.main turtle-screener scan
```

**股票池模式**
```bash
python -m app.main turtle-screener --pool
```

**指定资金量**
```bash
python -m app.main turtle-screener --capital 200000
```

**全市场扫描（选出 top N）**
```bash
python -m app.main turtle-screener market_scan --top-n 10
```

## 输出说明

- `breakout`: 是否创 20 日新高（突破信号）
- `current_price`: 当前价格
- `twenty_day_high`: 20 日最高价
- `atr_trend`: ATR 趋势（rising/falling/stable）
- `position_size`: 建议建仓股数（基于 2% 风险）
- `stop_loss_price`: 止损价格（2N）

## 示例

```bash
# 检查单只股票
python -m app.main turtle-screener check 600519

# 全市场扫描，返回 Top 10
python -m app.main turtle-screener market_scan --top-n 10
```
