# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role Definition

你是一位精通 Python 语言的资深软件工程师，熟悉云原生开发与软件工程最佳实践。你的任务是协助我，以高质量、可维护的方式完成本项目的开发。

## Project Overview

A 股分析工具 (A-Stock Analysis Agent) - 基于分层架构的股票分析工具，提供技术分析、基本面分析、新闻情绪分析功能，生成 Markdown 投资分析报告。

## Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 运行分析（主命令）
python -m app.main 600519

# 运行分析（带参数）
python -m app.main 600519 --no-download    # 使用缓存数据
python -m app.main 600519 --no-ai          # 不使用 AI 情绪分析
python -m app.main 600519 --feishu         # 发送飞书通知

# 海龟交易法则选股器
python -m app.turtle_screener              # 扫描默认股票池
python -m app.turtle_screener 600519       # 检查单只股票
python -m app.turtle_screener --pool       # 股票池模式
python -m app.turtle_screener --capital 200000  # 指定资金量

# 全市场扫描（选出 top N）
python -m app.turtle_screener market_scan --top-n 10

# 持仓监控系统
python -m app.turtle_screener monitor              # 查看监控报告
python -m app.turtle_screener monitor report --alert  # 显示报告并检查提醒
python -m app.turtle_screener monitor add 002053   # 添加持仓
python -m app.turtle_screener monitor remove 002053 # 移除持仓
python -m app.turtle_screener monitor list         # 列出持仓
python -m app.turtle_screener monitor watch-add 600519    # 添加到关注列表
python -m app.turtle_screener monitor watch-list          # 列出关注列表

# Web 可视化界面
python -m app.web_ui --port 8080           # 启动 Web 界面（默认 8080 端口）
python -m app.web_ui --port 9000           # 指定端口
python -m app.web_ui --reload              # 开发模式（热重载）

# 运行测试
pytest tests/

# 定时任务（报告清理）
python run_scheduler.py                     # 启动调度器（每天 23:59 执行）
python -m app.tasks.cleanup_reports         # 手动执行一次清理
python -m app.tasks --once                  # 立即执行一次后退出

# 飞书机器人（双向互动）
python -m app.bot                           # 启动 HTTP 服务器
python -m app.bot --port 9000               # 指定端口
python -m app.bot --log-level DEBUG         # 指定日志级别

# 本地开发（无公网域名）
# 步骤 1: 安装 cloudflared
winget install Cloudflare.cloudflared

# 步骤 2: 启动机器人和隧道（两个终端）
python -m app.bot --port 8080               # 终端 1
cloudflared tunnel --url http://localhost:8080  # 终端 2

# 或使用快捷脚本（Windows）
.\scripts\start_bot_with_tunnel.bat
```

## Architecture

```
app/
├── main.py              # CLI 入口，编排分析流程
├── config.py            # 配置管理（从.env 加载）
├── exceptions.py        # 自定义异常
│
├── core/                # 核心业务层
│   ├── analyzer.py      # 分析引擎（协调各模块）
│   ├── technical.py     # 技术分析（MA/MACD/RSI）
│   ├── fundamental.py   # 基本面分析（PE/PB/评分）
│   ├── sentiment.py     # 情绪分析（新闻获取/AI 分析）
│   └── turtle.py        # 海龟交易法则（ATR/突破/头寸）
│
├── data/                # 数据访问层
│   ├── downloader.py    # 数据下载服务
│   ├── repository.py    # 本地数据仓库（CSV 缓存）
│   └── sources/         # 数据源适配器
│       ├── base.py      # 数据源基类
│       ├── akshare.py   # AkShare 适配器（主要数据源）
│       └── eastmoney.py # 东财适配器（新闻）
│
├── services/            # 服务层
│   ├── report.py        # Markdown 报告生成
│   └── notification.py  # 飞书通知
│
├── tasks/               # 定时任务模块
│   ├── scheduler.py     # 定时调度器
│   └── cleanup_reports.py # 报告清理任务
│
├── turtle_screener/     # 海龟交易法则选股器
│   ├── __main__.py      # 模块入口
│   ├── turtle_screener.py  # CLI 选股器
│   ├── market_scan.py   # 全市场扫描
│   ├── monitor.py       # 持仓监控器
│   └── monitor_cli.py   # 监控 CLI

├── web_ui/              # Web 可视化界面（新增）
│   ├── __init__.py      # 模块入口
│   ├── __main__.py      # CLI 启动入口
│   ├── server.py        # FastAPI 服务器 + HTML 页面
│   └── routes.py        # API 路由
│
├── bot/                 # 飞书机器人模块
│   ├── __init__.py      # 模块入口
│   ├── __main__.py      # CLI 启动入口
│   ├── server.py        # FastAPI HTTP 服务器
│   ├── handler.py       # 消息处理器
│   ├── feishu_client.py # 飞书 API 客户端
│   └── commands.py      # 命令解析器
│
├── turtle_screener/     # 海龟选股器模块（新增）
│   ├── __init__.py      # 模块入口
│   ├── __main__.py      # CLI 启动入口
│   └── turtle_screener.py # 选股器主程序
│
└── utils/
    ├── logger.py        # 日志配置
    └── stock_names.py   # 股票名称映射
```

## Data Flow

1. **CLI (main.py)** 接收股票代码 → 调用分析引擎
2. **StockAnalyzer (analyzer.py)** 协调三个分析模块：
   - `_prepare_data()` → 从 `DataDownloader` 或 `DataRepository` 获取数据
   - `_run_technical_analysis()` → `TechnicalAnalyzer`
   - `_run_fundamental_analysis()` → `FundamentalAnalyzer` + 基本面数据
   - `_run_sentiment_analysis()` → `SentimentAnalyzer` + 新闻数据
3. **ReportService** 生成 Markdown 报告
4. **NotificationService** 发送飞书通知（可选）

## Key Patterns

- **数据源适配**: `BaseDataSource` 定义了 `get_stock_history()`, `get_fundamentals()`, `get_news()` 接口
- **缓存策略**: 数据默认缓存 3 天（`cache_days` 配置），`DataRepository.is_data_fresh()` 判断
- **AI 降级**: 情绪分析优先使用 AI，失败时回退到关键词匹配
- **配置管理**: `Config` dataclass 从 `.env` 加载，`get_config()` 获取全局单例

## Configuration

关键环境变量（见 `.env.example`）:

**AI 分析**:
- `ANTHROPIC_API_KEY` - Claude API Key（AI 情绪分析必需）

**飞书 Webhook 通知**（单向推送）:
- `FEISHU_WEBHOOK_URL` - 飞书机器人 Webhook（通知必需）

**飞书机器人**（双向互动）:
- `FEISHU_APP_ID` - 飞书应用 ID
- `FEISHU_APP_SECRET` - 飞书应用密钥
- `FEISHU_VERIFICATION_TOKEN` - 事件订阅验证 token
- `FEISHU_BOT_PORT` - HTTP 服务器端口（默认：8080）

**数据配置**:
- `DATA_DIR` / `REPORTS_DIR` - 数据/报告目录
- `ENABLE_AI_ANALYSIS` / `ENABLE_CACHE` - 功能开关

## Report File Naming

报告文件命名格式：`{股票代码}_{股票名称}_{日期}_{时间}.md`
例如：`600519_贵州茅台_20260307_143022.md`

定时任务自动清理旧报告，每个股票保留最新 3 条。

## Testing

测试文件位于 `tests/`:
- `test_technical.py` - 技术分析单元测试
- `test_fundamental.py` - 基本面分析单元测试
- `test_sentiment.py` - 情绪分析单元测试

使用 pytest 运行，测试独立于外部 API（使用模拟数据）。

## Python Development Standards

### 代码风格
- 遵循 PEP 8 规范
- 使用 4 空格缩进
- 行宽限制 100 字符
- 导入顺序：标准库 → 第三方库 → 本地模块

### 类型注解
- 所有公共函数必须包含类型注解
- 使用 `typing` 模块处理复杂类型（`Optional`, `List`, `Dict`, `Any`）
- 函数返回值必须标注类型

### 文档字符串
- 公共函数使用 docstring 说明参数和返回值
- 使用简洁的中文或英文描述

### 错误处理
- 使用自定义异常类（见 `exceptions.py`）
- 避免裸 `except:`，使用具体的异常类型
- 日志记录使用 `logger` 而非 `print`

### 数据访问
- 数据层与业务层分离，禁止跨层调用
- 外部 API 调用必须封装在 `data/sources/` 目录
- 缓存操作通过 `DataRepository` 统一管理

### 配置管理
- 敏感信息通过环境变量或 `.env` 文件管理
- 使用 `get_config()` 获取全局配置，不要直接实例化 `Config`

## Project Constitution

项目的根本大章 `constitution.md` 定义了：
- 项目价值观和设计原则
- 技术决策指南和架构决策记录 (ADR)
- 代码审查清单（7 项检查）
- 开发工作流和提交规范
- 关键文件索引和常见问题

**重要**: 进行重大修改或新增功能前，应查阅 `constitution.md` 确保符合项目原则。
