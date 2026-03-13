---
name: selector-scan
description: 使用多因子模型选股，根据市场环境动态调整因子权重
---

# 多因子选股扫描

基于质量、动量、股息、估值四个因子，根据市场环境动态调整权重进行选股。

## 用法

**默认扫描（返回 Top 10）**
```bash
python -m app.main stock-selector scan --top-n 10
```

**指定返回数量**
```bash
python -m app.main stock-selector scan --top-n $1
```

**检查单只股票**
```bash
python -m app.main stock-selector scan --stock-code $1
```

**查看当前市场环境**
```bash
python -m app.main stock-selector regime
```

**获取当前因子权重**
```bash
python -m app.main stock-selector weights
```

## 因子说明

| 因子 | 说明 |
|------|------|
| 质量因子 (quality) | FCF/净利润比率 + 利润增长率 |
| 动量因子 (momentum) | 价格位置 (20 日区间) + 成交量 |
| 股息因子 (dividend) | 股息率 + 连续分红年数 |
| 估值因子 (valuation) | PE/PB 等 |

## 市场环境模式

| 模式 | 质量 | 动量 | 红利 | 估值 |
|------|------|------|------|------|
| 缩量防御 | 25% | 10% | 40% | 25% |
| 放量进攻 | 25% | 40% | 10% | 25% |
| 结构性行情 | 35% | 20% | 20% | 25% |

## 示例

```bash
# 扫描 Top 20 股票
python -m app.main stock-selector scan --top-n 20

# 检查贵州茅台
python -m app.main stock-selector scan --stock-code 600519
```
