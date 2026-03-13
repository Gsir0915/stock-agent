# Skills (技能)

本目录包含本 A 股分析工具提供的所有可用技能。

## 技能列表

| 技能 | 说明 | 命令 |
|------|------|------|
| **analyze-stock** | 股票分析 - 生成投资分析报告 | `/analyze-stock <代码>` |
| **turtle-scan** | 海龟交易法则 - 检查突破信号 | `/turtle-scan <代码>` |
| **selector-scan** | 多因子选股 - 动态因子权重 | `/selector-scan` |
| **hot-news** | 热点新闻 - A 股市场新闻推荐 | `/hot-news` |
| **start-bot-with-tunnel** | 飞书机器人 - 本地开发隧道 | `/start-bot-with-tunnel` |

## 技能详细说明

### analyze-stock
为指定的 A 股股票代码生成完整的投资分析报告，包括技术面、基本面和情绪面分析。

### turtle-scan
使用海龟交易法则扫描股票，检查 20 日突破信号和 ATR 趋势，给出建议头寸。

### selector-scan
基于质量、动量、股息、估值四个因子，根据市场环境动态调整权重进行选股。

### hot-news
获取 A 股市场热点新闻，支持按板块/概念筛选和情绪分析。

### start-bot-with-tunnel
启动飞书机器人 HTTP 服务器并自动创建 ngrok 隧道，用于本地开发和测试。

## 使用方式

在 Claude Code 中，只需提及技能名称即可触发。例如：

- "使用 analyze-stock 分析 600519"
- "用 turtle-scan 检查这只股票"
- "运行 selector-scan 选股"
- "看看 hot-news 有什么热门"

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 项目配置和开发指南
- [README.md](README.md) - 项目使用说明
- [constitution.md](constitution.md) - 项目章程
