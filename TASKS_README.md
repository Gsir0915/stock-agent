# 定时任务使用说明

## 功能说明

定时任务系统用于自动清理 `reports` 目录中的报告文件，确保每个股票编码只保留最新的 3 条报告数据。

**执行时间**: 每天 23:59:59

## 使用方式

### 方式一：作为服务运行（推荐）

启动定时任务调度器，将持续运行并在指定时间自动执行清理：

```bash
python run_scheduler.py
```

或

```bash
python -m app.tasks.scheduler
```

### 方式二：手动执行清理

立即执行一次清理任务：

```bash
python -m app.tasks.cleanup_reports
```

或

```bash
python -m app.tasks --once
```

### 方式三：使用批处理脚本（Windows）

在 Windows 系统中，可以使用提供的批处理脚本：

```bash
cleanup_reports.bat
```

### 方式四：配置 Windows 任务计划程序

1. 打开"任务计划程序"
2. 点击"创建基本任务"
3. 设置触发器为"每天"，时间为"23:59:59"
4. 操作选择"启动程序"
5. 程序/脚本填写：`cleanup_reports.bat` 的完整路径
6. 完成配置

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--reports-dir` | 报告目录路径 | `reports` |
| `--keep-count` | 每个股票保留的报告数量 | `3` |
| `--once` | 立即执行一次后退出 | `False` |

### 使用示例

```bash
# 指定报告目录和保留数量
python -m app.tasks --reports-dir /path/to/reports --keep-count 5

# 立即执行一次清理
python -m app.tasks --once

# 使用默认配置启动调度器
python run_scheduler.py
```

## 报告文件命名格式

报告文件遵循以下命名格式：
```
{股票代码}_{股票名称}_{日期}_{时间}.md
例如：600519_贵州茅台_20260307_143022.md
```

## 清理逻辑

1. 扫描报告目录中所有 `.md` 文件
2. 从文件名中提取股票代码和时间戳
3. 按股票代码分组
4. 每组内按时间戳排序（最新的在前）
5. 保留最新的 N 条（默认 3 条），删除其余旧报告

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REPORTS_DIR` | 报告目录路径 | `reports` |

## 注意事项

1. 确保运行调度器时终端保持打开状态
2. 如需后台运行，可使用 `nohup` (Linux/Mac) 或配置 Windows 服务
3. 生产环境建议使用系统级定时任务（如 cron 或 Windows 任务计划程序）
