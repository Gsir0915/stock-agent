# 配置依赖要求说明

## 重要原则

**所有策略参数严禁写死在代码里，必须统一从 config.yaml 读取**

本模块采用配置驱动设计，所有策略相关的参数必须通过配置文件管理，代码中不允许出现任何硬编码的策略参数。

---

## 配置加载机制

### 1. 配置文件搜索顺序

系统会按以下顺序查找 `config.yaml`：

1. 构造函数传入的路径
2. 当前模块目录下的 `config.yaml`
3. 项目根目录下的 `config.yaml`
4. `agents/stock_selector/` 目录下的 `config.yaml`

### 2. 配置加载失败处理

自 v2.0 起，配置加载失败时**不再使用默认值**，而是抛出异常。这是为了确保：

- 策略参数透明可查
- 避免隐式行为导致意外结果
- 强制开发者明确了解策略配置

---

## 必须从配置读取的参数

### 市场环境判断参数

| 参数 | 配置路径 | 说明 |
|------|----------|------|
| 成交量阈值 | `market_regime.volume_thresholds.*` | 定义 extremely_low/low/normal/high/extremely_high 五档 |
| 牛市阈值 | `market_regime.trend_thresholds.bull_threshold` | 价格/MA120 > 1.05 为牛市 |
| 熊市阈值 | `market_regime.trend_thresholds.bear_threshold` | 价格/MA120 < 0.95 为熊市 |
| 模式映射 | `market_regime.regime_mapping.*` | 成交量 + 趋势 -> 模式名称 |

### 因子权重参数

| 参数 | 配置路径 | 说明 |
|------|----------|------|
| 各模式权重 | `factor_weights.{模式名称}.*` | quality/momentum/dividend/valuation 四因子权重 |

**注意**：权重总和必须为 1.0（100%）

### 执行参数

| 参数 | 配置路径 | 说明 |
|------|----------|------|
| 最低分数 | `execution.min_total_score` | 综合得分低于此值不选 |
| 最大选股数 | `execution.max_selections` | 每次扫描最多选出股票数 |
| 行业集中度 | `execution.max_sector_weight` | 单一行业最大持仓比例 |

### 过滤条件参数

| 参数 | 配置路径 | 说明 |
|------|----------|------|
| 剔除 ST | `filters.exclude_st` | 是否剔除 ST/*ST 股票 |
| 最小市值 | `filters.min_market_cap` | 市值低于此值剔除（亿元） |
| 最小股价 | `filters.min_price` | 股价低于此值剔除（元） |
| 上市天数 | `filters.min_listing_days` | 上市不满 N 日剔除 |

---

## 代码示例

### 正确做法

```python
from agents.stock_selector import StockSelectorEngine

# 创建引擎（自动从 config.yaml 读取配置）
engine = StockSelectorEngine()

# 获取市场环境判断（阈值来自配置）
regime = engine.determine_market_regime()

# 获取因子权重（来自配置）
weights = engine.get_current_weights()

# 执行选股（min_score 来自配置）
results = engine.screen(stock_list=["600519"])
```

### 错误做法

```python
# 错误：在代码中硬编码参数
volume_threshold = 6000  # 严禁写死！
bull_threshold = 1.05    # 严禁写死！
default_weights = {"quality": 0.25, ...}  # 严禁写死！
```

---

## 配置验证

启动时系统会自动验证配置完整性，确保以下必需配置项存在：

- `market_regime.volume_thresholds`
- `market_regime.trend_thresholds`
- `market_regime.regime_mapping`
- `factor_weights`（包含所有 8 种模式）
- `filters`
- `execution`

---

## 自定义配置

如需修改策略参数，编辑 `config.yaml` 即可，无需修改代码：

```yaml
# 示例：调整成交量阈值
market_regime:
  volume_thresholds:
    extremely_low: 5000  # 将极度缩量阈值从 6000 亿改为 5000 亿
    low: 7000

# 示例：自定义因子权重
factor_weights:
  放量进攻:
    quality: 0.30        # 提高质量因子权重
    momentum: 0.35       # 降低动量因子权重
    dividend: 0.10
    valuation: 0.25
```

---

## 故障排查

### 问题：提示 "配置项不存在"

**原因**：config.yaml 中缺少必需的配置项

**解决**：检查 config.yaml 是否包含所有必需的配置节点

### 问题：提示 "配置文件未找到"

**原因**：config.yaml 不在搜索路径中

**解决**：
1. 将 config.yaml 放到 `agents/stock_selector/` 目录下
2. 或在初始化时指定路径：`StockSelectorEngine(config_path="/path/to/config.yaml")`

### 问题：权重加载失败

**原因**：config.yaml 中该模式名称不存在

**解决**：确保 `factor_weights` 下包含当前市场模式对应的权重配置

---

## 版本历史

- **v1.0**：初始版本，配置加载失败时使用默认值
- **v2.0**：严格模式，配置加载失败时抛出异常，严禁硬编码
