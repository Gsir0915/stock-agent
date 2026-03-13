---
name: hot-news
description: 获取并推荐 A 股市场热点新闻，支持按板块/概念筛选
---

# 热点新闻推荐

获取 A 股市场热点新闻，支持按板块/概念筛选和情绪分析。

## 用法

**获取全市场热点新闻（默认 Top 10）**
```bash
python -m app.main hot-news fetch
```

**指定返回数量**
```bash
python -m app.main hot-news fetch --top-n $1
```

**指定板块/概念**
```bash
python -m app.main hot-news fetch --sector $1
```

**筛选情绪（只看利好）**
```bash
python -m app.main hot-news fetch --sentiment positive
```

**查看热门概念排行**
```bash
python -m app.main hot-news concepts
```

## 输出说明

- 新闻标题、发布时间、来源
- 情绪标签（正面/负面/中性）
- 相关股票代码及名称
- 概念板块热度排行

## 支持的板块/概念

- 人工智能
- 新能源
- 半导体
- 医药生物
- 新能源汽车
- 5G 概念
- 等等

## 示例

```bash
# 获取人工智能板块新闻
python -m app.main hot-news fetch --sector 人工智能

# 只看利好新闻
python -m app.main hot-news fetch --sentiment positive

# 获取 Top 20 新闻
python -m app.main hot-news fetch --top-n 20
```
