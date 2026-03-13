# 市场环境判断与动态权重使用指南

## 功能概述

`StockSelectorEngine` 提供市场环境判断功能，根据两市成交额和上证指数趋势，自动调整因子权重配置。

## 使用方法

### 1. 基本使用

```python
from agents.stock_selector import StockSelectorEngine

# 创建引擎实例
engine = StockSelectorEngine()

# 获取两市成交额（亿元）
turnover = engine.get_market_turnover()
print(f"两市成交额：{turnover} 亿元")

# 判断市场环境
regime = engine.determine_market_regime()
print(f"市场模式：{regime.regime_name}")
print(f"成交量水平：{regime.volume_level}")
print(f"趋势类型：{regime.trend_type}")

# 获取当前因子权重（自动根据市场环境）
weights = engine.get_current_weights()
print(f"当前权重：{weights}")
```

### 2. 打印市场环境分析

```python
# 打印完整的市场环境分析报告
engine.print_market_regime()
```

输出示例：
```
============================================================
市场环境分析
============================================================
两市成交额：9500.00 亿元
成交量水平：normal
上证指数：3250.50 点
120 日均线：3200.00 点
趋势类型：bull
市场模式：放量进攻

当前因子权重:
  quality: 25%
  momentum: 40%
  dividend: 10%
  valuation: 25%
============================================================
```

### 3. 获取指定模式的权重

```python
# 获取"缩量防御"模式的权重
defensive_weights = engine.get_weights_for_mode("缩量防御")

# 获取"放量进攻"模式的权重
offensive_weights = engine.get_weights_for_mode("放量进攻")
```

### 4. 在选股流程中使用

```python
from agents.stock_selector import StockSelectorEngine, QualityFactor, MomentumFactor, DividendFactor

engine = StockSelectorEngine()

# 1. 判断市场环境，获取权重
regime = engine.determine_market_regime()
weights = engine.get_current_weights()
print(f"当前市场模式：{regime.regime_name}")

# 2. 计算股票得分
def calculate_score(stock_data, weights):
    quality_score = QualityFactor().run(stock_data["quality_data"])
    momentum_score = MomentumFactor().run(stock_data["momentum_data"])
    dividend_score = DividendFactor().run(stock_data["dividend_data"])
    valuation_score = stock_data.get("valuation_score", 0.5)

    # 根据市场模式加权
    total_score = (
        quality_score * weights["quality"] +
        momentum_score * weights["momentum"] +
        dividend_score * weights["dividend"] +
        valuation_score * weights["valuation"]
    )
    return total_score

# 3. 执行选股
stock_pool = [...]  # 股票池
results = []
for stock in stock_pool:
    score = calculate_score(stock, weights)
    if score >= 0.5:  # 最低门槛
        results.append(stock)
```

## 市场环境模式说明

### 成交量水平判断

| 水平 | 成交额（亿元） | 经济学意义 |
|------|----------------|------------|
| extremely_low | < 6000 | 流动性枯竭，市场底部区域 |
| low | 6000-8000 | 风险偏好下降，观望情绪浓厚 |
| normal | 8000-10000 | 多空平衡，结构性行情 |
| high | 10000-12000 | 风险偏好提升，增量资金进场 |
| extremely_high | > 15000 | 情绪亢奋，警惕过热回调 |

### 趋势类型判断

| 类型 | 判断标准 | 经济学意义 |
|------|----------|------------|
| bull | 指数/MA120 > 1.05 | 经济扩张期，估值提升 |
| bear | 指数/MA120 < 0.95 | 经济收缩期，估值压缩 |
| range | 0.95 ≤ 指数/MA120 ≤ 1.05 | 震荡整理，方向不明 |

### 市场模式与权重配置

| 市场模式 | 质量 | 动量 | 红利 | 估值 | 策略逻辑 |
|----------|------|------|------|------|----------|
| 缩量防御 | 25% | 10% | 40% | 25% | 高股息防御，低估值安全边际 |
| 防守观望 | 30% | 10% | 35% | 25% | 聚焦真成长，保持防御属性 |
| 反弹博弈 | 20% | 35% | 15% | 30% | 快进快出，关注弹性 |
| 区间震荡 | 35% | 15% | 25% | 25% | 震荡中质量为王 |
| 结构性行情 | 35% | 20% | 20% | 25% | 精选个股，质量 + 估值双轮驱动 |
| 突破酝酿 | 25% | 35% | 15% | 25% | 适度激进，关注突破信号 |
| 放量进攻 | 25% | 40% | 10% | 25% | 积极参与，动量主导 |
| 过热预警 | 40% | 15% | 25% | 20% | 逐步撤退，质量最重要 |

## MarketRegime 数据类属性

```python
@dataclass
class MarketRegime:
    volume_level: str       # 成交量水平
    trend_type: str         # 趋势类型
    regime_name: str        # 市场模式名称
    total_turnover: float   # 两市总成交额（亿元）
    sh_index_close: float   # 上证指数收盘价
    sh_ma120: float         # 上证指数 120 日均线
```

## 注意事项

1. **网络依赖**: 获取市场数据需要联网，失败时返回默认值
2. **数据更新**: 建议使用最新交易日数据
3. **配置依赖**: 权重配置来自 `config.yaml`，确保文件存在
4. **严格模式**: 自 v2.0 起，配置加载失败时抛出异常，不再使用默认值
5. **严禁硬编码**: 所有策略参数必须从 `config.yaml` 读取，代码中不允许出现硬编码的策略参数

有关配置要求的详细说明，请参考 `CONFIG_REQUIREMENTS.md`。

## 配置自定义

如需修改市场环境判断阈值，编辑 `config.yaml`:

```yaml
market_regime:
  volume_thresholds:
    extremely_low: 5000  # 自定义阈值
    low: 7000
    # ...
```
