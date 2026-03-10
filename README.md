# 股票分析 Agent

基于分层架构重构的 A 股分析工具，提供技术分析、基本面分析、新闻情绪分析功能，生成 Markdown 投资分析报告。

## 🏗️ 架构设计

```
app/
├── main.py              # 应用入口 (CLI)
├── config.py            # 配置管理 (支持.env)
├── exceptions.py        # 自定义异常体系
│
├── core/                # 核心业务层
│   ├── analyzer.py      # 分析引擎 (协调各模块)
│   ├── technical.py     # 技术分析 (MA/MACD/RSI)
│   ├── fundamental.py   # 基本面分析 (PE/PB/评分)
│   └── sentiment.py     # 情绪分析 (新闻获取/分析)
│
├── data/                # 数据访问层
│   ├── downloader.py    # 数据下载服务
│   ├── repository.py    # 本地数据仓库 (CSV/缓存)
│   └── sources/         # 数据源适配器
│       ├── base.py      # 数据源基类
│       ├── akshare.py   # AkShare 适配器
│       └── eastmoney.py # 东财适配器
│
├── services/            # 服务层
│   ├── report.py        # 报告生成 (Markdown)
│   └── notification.py  # 通知服务 (飞书)
│
└── utils/               # 工具类
    ├── logger.py        # 统一日志配置
    └── stock_names.py   # 股票名称映射
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置必要的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
ANTHROPIC_API_KEY=your_api_key_here
FEISHU_WEBHOOK_URL=https://open.feishu.cn/...
```

### 3. 运行分析

```bash
# 分析贵州茅台
python -m app.main 600519

# 分析并推送到飞书
python -m app.main 600519 --feishu

# 使用缓存数据
python -m app.main 600519 --no-download

# 不使用 AI 分析（使用本地规则）
python -m app.main 600519 --no-ai
```

## 📋 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `code` | 股票代码（必需） | - |
| `--data-dir` | 数据保存目录 | `data` |
| `--output-dir` | 报告输出目录 | `reports` |
| `--no-download` | 跳过下载，使用缓存 | `False` |
| `--feishu` | 发送飞书通知 | `False` |
| `--no-ai` | 不使用 AI 情绪分析 | `False` |
| `--log-level` | 日志级别 | `INFO` |

## 📊 分析内容

### 技术分析
- **均线系统**: MA5, MA10, MA20, MA60
- **MACD 指标**: DIF, DEA, MACD 柱
- **RSI 指标**: RSI(14) 超买超卖判断
- **成交量分析**: 放量/缩量判断
- **技术信号**: 多头/空头排列、金叉/死叉等

### 基本面分析
- **估值指标**: PE（动态）、PB
- **成长指标**: 净利润增长率
- **价值评分**: 0-100 分综合评估
- **投资评级**: 五星级评级系统

### 情绪分析
- **新闻获取**: 从东方财富获取最新新闻
- **AI 分析**: 使用 Claude 进行情绪判断（可选）
- **本地规则**: 关键词匹配备用方案
- **情绪汇总**: 正面/负面/中性统计

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Claude API Key | 否（用于 AI 情绪分析） |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook | 否（用于推送通知） |
| `DATA_DIR` | 数据目录 | 否 |
| `REPORTS_DIR` | 报告目录/定时任务清理目录 | 否 |
| `LOG_LEVEL` | 日志级别 | 否 |

## 📁 目录结构

```
stock-agent/
├── app/                   # 应用代码
│   ├── main.py            # 应用入口
│   ├── core/              # 核心业务层
│   ├── data/              # 数据访问层
│   ├── services/          # 服务层
│   ├── utils/             # 工具类
│   └── tasks/             # 定时任务模块
├── tests/                 # 测试用例
├── data/                  # 股票数据缓存
├── reports/               # 生成的报告
├── .env                   # 环境变量配置
├── .env.example           # 配置模板
├── requirements.txt       # Python 依赖
├── run_scheduler.py       # 定时任务启动脚本
├── cleanup_reports.bat    # Windows 清理脚本
├── TASKS_README.md        # 定时任务详细说明
└── README.md              # 说明文档
```

## 🕐 定时任务

### 报告自动清理

系统提供定时任务，自动清理 `reports` 目录中的旧报告，**每个股票编码只保留最新的 3 条报告**。

**执行时间**: 每天 23:59:59

#### 启动定时任务

```bash
# 方式 1: 启动调度器（持续运行）
python run_scheduler.py

# 方式 2: 手动执行一次清理
python -m app.tasks.cleanup_reports

# 方式 3: 使用批处理脚本 (Windows)
cleanup_reports.bat
```

#### Windows 任务计划程序配置

如需系统级定时任务，可将 `cleanup_reports.bat` 配置到 Windows 任务计划程序：

1. 打开"任务计划程序"
2. 创建基本任务 → 设置每天 23:59:59 触发
3. 操作：启动程序 → 选择 `cleanup_reports.bat`

详细文档请参阅 `TASKS_README.md`

## 🧪 运行测试

```bash
# 运行单元测试
pytest tests/
```

## 📝 输出示例

### 控制台输出
```
======================================================================
📊 股票投资分析报告生成器 v2.0
======================================================================
股票代码：600519
股票名称：贵州茅台
======================================================================

开始分析...

📊 技术分析:
  收盘价：1520.50
  RSI: 45.23
  技术信号：3 条
    - 🟢 多头排列：短期均线在长期均线上方

💰 基本面分析:
  PE: 28.50
  PB: 7.82
  净利润增长率：15.30%
  价值评分：65/100
  评级：★★★★ 具有投资价值

📰 新闻情绪分析:
  正面：3 条
  负面：1 条
  中性：1 条
  整体判断：整体偏正面

✅ 报告生成成功！
📄 报告路径：reports/600519_贵州茅台_20260307_143022.md
```

### Markdown 报告

报告包含：
- 核心指标概览表
- 详细技术指标
- 技术信号列表
- 基本面估值分析
- 新闻情绪汇总
- 综合投资建议

## 🔌 扩展开发

### 添加新数据源

1. 继承 `app/data/sources/base.py` 的 `BaseDataSource`
2. 实现 `get_stock_history()`, `get_fundamentals()`, `get_news()` 方法
3. 在 `DataDownloader` 中注册新数据源

### 添加新通知渠道

1. 继承 `app/services/notification.py` 的 `NotificationChannel`
2. 实现 `send()` 方法
3. 在 `NotificationService` 中注册

### 添加新指标

在对应分析模块中添加计算函数：
- 技术指标：`app/core/technical.py`
- 基本面指标：`app/core/fundamental.py`
- 情绪指标：`app/core/sentiment.py`

## ⚠️ 注意事项

1. **数据时效性**: 请在交易日运行，休市日可能无法获取实时数据
2. **API 限制**: 注意 akshare 和 Claude API 的调用频率限制
3. **投资风险**: 报告仅供参考，不构成投资建议
4. **缓存策略**: 默认缓存 3 天内的数据，避免重复下载
5. **定时任务**: 报告清理任务每天 23:59:59 执行，需确保进程运行或配置系统任务计划

## 📄 License

MIT License

## 🙏 致谢

- 数据源：[AkShare](https://github.com/akfamily/akshare), [东方财富](https://www.eastmoney.com/)
- AI 分析：[Claude API](https://www.anthropic.com/api)
- 通知：[飞书开放平台](https://open.feishu.cn/)
