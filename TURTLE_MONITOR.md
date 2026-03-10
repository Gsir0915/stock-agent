# 海龟交易监控系统使用指南

## 功能概述

海龟交易监控系统提供完整的持仓管理、价格监控、止损预警和加仓提醒功能。

### 核心功能

1. **价格监控** - 实时更新持仓股票和关注股票的当前价格
2. **移动止损追踪** - 自动计算并更新移动止损价（最高价 - 2N）
3. **加仓提醒** - 当价格接近加仓价位时发出提醒
4. **止损预警** - 当价格触及止损价时发出_CRITICAL_级别警告
5. **盈利跟踪** - 显示当前盈亏金额和百分比
6. **关注列表** - 追踪等待突破的股票

---

## 使用方式

### 命令行入口

```bash
python -m app.turtle_screener monitor [子命令] [参数]
```

### 子命令列表

| 子命令 | 说明 | 示例 |
|--------|------|------|
| `report` | 显示监控报告和提醒 | `python -m app.turtle_screener monitor report --alert` |
| `add` | 添加持仓 | `python -m app.turtle_screener monitor add 002053` |
| `remove` | 移除持仓 | `python -m app.turtle_screener monitor remove 002053` |
| `list` | 列出持仓 | `python -m app.turtle_screener monitor list` |
| `watch-add` | 添加到关注列表 | `python -m app.turtle_screener monitor watch-add 600519` |
| `watch-remove` | 从关注列表移除 | `python -m app.turtle_screener monitor watch-remove 600519` |
| `watch-list` | 列出关注列表 | `python -m app.turtle_screener monitor watch-list` |

---

## 详细使用说明

### 1. 添加持仓

当你根据交易信号建仓后，可以添加持仓到监控系统：

```bash
# 添加持仓（使用默认资金 100,000 计算头寸）
python -m app.turtle_screener monitor add 002053

# 添加持仓（指定资金量）
python -m app.turtle_screener monitor add 002053 --capital 200000
```

**输出示例：**
```
✅ 已添加持仓：002053 云南能投
   入场价：¥13.01
   股数：2,700
   止损价：¥12.29
   加仓价：¥13.19, ¥13.37, ¥13.55
```

**自动计算的内容：**
- 入场价：当前市场价格
- 股数：基于 2% 风险规则和 ATR 计算
- 止损价：入场价 - 2×ATR
- 加仓价：3 个加仓点位（0.5N 递增）

---

### 2. 查看监控报告

```bash
# 查看监控报告（默认）
python -m app.turtle_screener monitor

# 查看报告并显示实时提醒
python -m app.turtle_screener monitor report --alert
```

**报告内容包括：**
- 📊 持仓汇总：总成本、总市值、总盈亏
- 📈 持仓明细：每只股票的现价、成本、盈亏%、止损价、信号状态
- 👁️ 关注列表：等待突破的股票及其状态

**信号状态图标：**
- `❌ 止损` - 已触及止损价，建议退出
- `🎯 大盈` - 盈利 > 20%
- `✅ 盈利` - 盈利 > 10%
- `⚠️ 亏损` - 亏损 > 5%
- `➖ 持有` - 正常持有中

---

### 3. 实时提醒类型

系统自动生成以下类型的提醒：

| 提醒类型 | 级别 | 触发条件 | 建议操作 |
|----------|------|----------|----------|
| 🚨 止损触发 | CRITICAL | 现价 ≤ 移动止损价 | 建议全部卖出退出 |
| 📈 加仓机会 | INFO | 价格接近下次加仓价 | 准备加仓 |
| 🎯 大幅盈利 | INFO | 盈利 > 20% | 使用移动止损保护利润 |
| ⚠️ 接近止损 | WARNING | 距离止损价 ≤ 3% | 密切关注，准备退出 |

---

### 4. 管理持仓

```bash
# 列出所有持仓
python -m app.turtle_screener monitor list

# 移除已卖出的持仓
python -m app.turtle_screener monitor remove 002053
```

---

### 5. 关注列表管理

关注列表用于追踪等待突破的股票，当突破时会发出提醒：

```bash
# 添加到关注列表
python -m app.turtle_screener monitor watch-add 600519

# 列出关注列表
python -m app.turtle_screener monitor watch-list

# 从关注列表移除
python -m app.turtle_screener monitor watch-remove 600519
```

---

## 数据存储

监控数据保存在以下 JSON 文件中：

| 文件 | 说明 | 路径 |
|------|------|------|
| `turtle_positions.json` | 持仓数据 | `data/turtle_positions.json` |
| `turtle_watchlist.json` | 关注列表 | `data/turtle_watchlist.json` |

### 持仓数据结构

```json
{
  "code": "002053",
  "name": "云南能投",
  "entry_price": 13.01,
  "entry_date": "2026-03-10",
  "units": 1,
  "shares_per_unit": 2700,
  "total_shares": 2700,
  "total_cost": 35127,
  "initial_stop": 12.29,
  "current_stop": 12.29,
  "stop_n": 2,
  "atr": 0.36,
  "add_unit_window": 0.18,
  "add_prices": [13.19, 13.37, 13.55],
  "filled_add_prices": []
}
```

---

## 移动止损计算逻辑

系统在每个价格更新时自动计算移动止损：

```python
# 移动止损 = 最高价 - 2×ATR
highest = max(入场价，当前价，近 20 日最高价)
current_stop = highest - atr * 2
```

**特点：**
- 止损价只上移，不下移
- 股价创新高时，止损价自动跟随上移
- 保护已实现利润

---

## 加仓规则

系统支持金字塔式加仓（最多加仓 3 次，总仓位 4 个单位）：

| 加仓次数 | 加仓价格 | 累计仓位 | 统一止损 |
|----------|----------|----------|----------|
| 初始 | 入场价 | 1 单位 | 入场价 - 2N |
| 第 1 次 | 入场价 + 0.5N | 2 单位 | 入场价 - 2N |
| 第 2 次 | 入场价 + 1.0N | 3 单位 | 入场价 - 2N |
| 第 3 次 | 入场价 + 1.5N | 4 单位 | 入场价 - 2N |

**系统自动追踪：**
- 哪些加仓价格已被触发
- 下次加仓的目标价格
- 当前应持有的单位数

---

## 退出策略

### 1. 止损退出

当价格跌破移动止损价时：
- 系统发出 _CRITICAL_ 级别警告
- 建议全部卖出退出
- 报告中标记为 `❌ 止损`

### 2. 止盈退出

推荐的止盈策略：
- 盈利 > 10%：关注移动止损
- 盈利 > 20%：使用移动止损保护利润
- 股价跌破移动止损价：全部退出

---

## 完整工作流示例

### 场景：发现交易信号并建仓

```bash
# 步骤 1: 扫描全市场，发现符合海龟买入条件的股票
python -m app.turtle_screener market_scan --top-n 10

# 步骤 2: 详细检查某只股票
python -m app.turtle_screener 002053 --verbose

# 步骤 3: 建仓后添加到监控系统
python -m app.turtle_screener monitor add 002053

# 步骤 4: 添加其他待突破股票到关注列表
python -m app.turtle_screener monitor watch-add 600519
```

### 场景：每日监控持仓

```bash
# 每日查看监控报告和提醒
python -m app.turtle_screener monitor report --alert

# 查看持仓列表
python -m app.turtle_screener monitor list

# 查看关注列表是否有突破
python -m app.turtle_screener monitor watch-list
```

### 场景：执行加仓

```bash
# 收到加仓提醒后，查看报告确认
python -m app.turtle_screener monitor report

# 手动加仓（在交易软件中执行）
# 然后在监控系统中，持仓会自动更新已加仓价格
```

### 场景：止损退出

```bash
# 收到止损警告后，查看报告
python -m app.turtle_screener monitor report --alert

# 在交易软件中卖出
# 然后在监控系统中移除
python -m app.turtle_screener monitor remove 002053
```

---

## 常见问题

### Q1: 价格数据从哪里获取？
系统优先使用本地缓存数据（`data/` 目录），如果缓存不存在或数据不足，会自动从 AkShare 下载最新数据。

### Q2: 如何更新到最新价格？
运行 `monitor report` 时会自动更新所有持仓和关注股票的价格。

### Q3: 可以设置自定义止损吗？
当前版本使用海龟交易法则的标准止损（2N）。如需自定义，可以直接编辑 `data/turtle_positions.json` 文件。

### Q4: 支持实时推送提醒吗？
当前版本仅在命令行运行时显示提醒。后续可以集成飞书/微信推送功能。

### Q5: 如何回测历史表现？
当前版本不支持回测。可以使用 `market_scan` 查看历史信号，然后手动验证。

---

## 相关文档

- [海龟交易法则选股器使用指南](TURTLE_SCREENER.md)
- [项目主文档](CLAUDE.md)
