---
name: analyze-stock
description: 为指定的股票代码生成投资分析报告（技术面 + 基本面 + 情绪面）
---

# 股票分析技能

为指定的 A 股股票代码生成完整的投资分析报告。

## 用法

**基本分析**
```bash
python -m app.main stock-analyzer analyze $1
```

**使用缓存数据（不下载）**
```bash
python -m app.main stock-analyzer analyze $1 --no-download
```

**不使用 AI 情绪分析**
```bash
python -m app.main stock-analyzer analyze $1 --no-ai
```

**仅技术分析**
```bash
python -m app.main stock-analyzer technical $1
```

**仅基本面分析**
```bash
python -m app.main stock-analyzer fundamental $1
```

**仅情绪分析**
```bash
python -m app.main stock-analyzer sentiment $1
```

**发送飞书通知**
```bash
python -m app.main stock-analyzer analyze $1 --feishu
```

## 输出说明

- **技术指标**: 收盘价、MA5/10/20/60、MACD、RSI
- **技术信号**: 均线排列、趋势判断、超买超卖
- **基本面**: PE、PB、净利润增长率、价值评分 (0-100)
- **情绪分析**: 新闻标题、情绪判断（正面/负面/中性）
- **Markdown 报告**: 保存到 reports/ 目录

## 示例

```bash
# 分析贵州茅台
python -m app.main stock-analyzer analyze 600519

# 分析平安银行（使用缓存）
python -m app.main stock-analyzer analyze 000001 --no-download
```
