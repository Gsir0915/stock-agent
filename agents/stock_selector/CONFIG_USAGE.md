# config_handler 使用示例

完整的使用示例请参考 `app/utils/config_handler_examples.py`。

## 快速开始

```python
from app.utils.config_handler import get_config

# 获取配置对象
config = get_config()

# 方式 1: 属性访问（推荐）
data_source = config.global_settings.data_source
min_cap = config.filters.min_market_cap

# 方式 2: get 方法路径式访问
data_source = config.get("global_settings.data_source")
min_cap = config.get("filters.min_market_cap")

# 方式 3: get 方法带默认值
value = config.get("non_existent", "default_value")
```

## 配置文件结构

```yaml
global_settings:
  data_source: akshare
  cache:
    path: "data"
    ttl_days: 3

market_regime:
  regime_mapping:
    bear_extremely_low_volume: "缩量防御"
    bull_normal_volume: "放量进攻"

factor_weights:
  缩量防御:
    quality: 0.25
    momentum: 0.10
    dividend: 0.40
    valuation: 0.25

filters:
  exclude_st: true
  min_market_cap: 50
  min_price: 2.0
```

## 在选股策略中使用

```python
from app.utils.config_handler import get_config

def run_screening(stock_pool):
    config = get_config()

    # 1. 获取当前市场模式
    market_mode = determine_market_mode()  # 如 "缩量防御"

    # 2. 获取对应权重
    weights = config.get(f"factor_weights.{market_mode}", {
        "quality": 0.25,
        "momentum": 0.25,
        "dividend": 0.25,
        "valuation": 0.25
    })

    # 3. 获取过滤条件
    min_score = config.execution.min_total_score
    max_selections = config.execution.max_selections

    results = []
    for stock in stock_pool:
        # 应用过滤条件
        if should_exclude(stock, config):
            continue

        # 计算得分
        score = calculate_score(stock, weights)

        if score >= min_score:
            results.append(stock)

    # 返回前 N 只
    return results[:max_selections]
```
