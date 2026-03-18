# GitHub Actions 选股任务使用指南

## 文件说明

- `.github/workflows/selector-scan.yml` - 选股扫描任务的 GitHub Actions 配置文件

## 配置 Secrets

在 GitHub 仓库中设置以下 Secrets：

1. 进入仓库页面 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret** 添加以下密钥：

| Secret 名称 | 说明 | 示例值 |
|-------------|------|--------|
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook URL | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` |
| `STOCK_POOL_CODES` | 股票代码列表（逗号分隔） | `600519,000858,002415,300750` |

### 获取飞书 Webhook URL

1. 在飞书群聊中添加「自定义机器人」
2. 复制机器人的 Webhook 地址
3. 添加到 GitHub Secrets

## 手动触发 Workflow

1. 进入仓库的 **Actions** 标签页
2. 选择 **Stock Selector Scan** workflow
3. 点击 **Run workflow** 按钮
4. 填写参数：
   - **Top N**: 返回前 N 只股票（默认：10）
   - **使用 Secrets 股票池**: true/false

## Workflow 执行流程

```
1. 检出代码
2. 设置 Python 3.12 环境
3. 缓存并安装 pip 依赖
4. 运行选股命令：python -m app.main stock-selector scan --top-n N
5. 发送飞书通知（包含选股结果）
```

## 输出示例

飞书群将收到如下格式的消息：

```
✅ 选股扫描结果
━━━━━━━━━━━━━━━━

选股扫描完成

参数:
• Top N: 10
• 使用 Secrets 股票池：true

执行时间：2026-03-18 10:30:00
运行链接：[查看 GitHub Actions 日志]

━━━━━━━━━━━━━━━━

选股结果:
当前市场模式：震荡市
因子权重：{'quality': 0.4, 'momentum': 0.3, 'dividend': 0.2, 'valuation': 0.1}
[选股结果列表]

━━━━━━━━━━━━━━━━

⚠️ 投资有风险，入市需谨慎
```

### 飞书消息卡片效果

- **成功执行**: 绿色标题栏 + ✅ 图标
- **执行失败**: 红色标题栏 + ❌ 图标
- 包含完整的选股结果摘要
- 提供直达 GitHub Actions 日志的链接

## 注意事项

1. **API 限流**: akshare 数据源有请求频率限制，建议不要频繁触发
2. **执行时间**: 全市场扫描可能需要 5-10 分钟
3. **超时设置**: Workflow 超时时间为 15 分钟
4. **依赖安装**: 首次运行可能需要较长时间安装依赖
5. **外部 API 依赖**:
   - akshare 需要访问东方财富等外部 API
   - GitHub Actions 运行在云端，需确保网络可达
6. **并发限制**: 避免同时触发多个 workflow，防止被数据源封禁

## 故障排查

### Workflow 失败

1. 检查 **Actions** 标签页中的运行日志
2. 常见错误：
   - 依赖安装失败 → 检查 requirements.txt
   - API 请求超时 → akshare 限流，稍后重试
   - Secrets 未配置 → 检查 Settings → Secrets
   - 数据源不可用 → 检查 akshare 服务状态

### 飞书通知未收到

1. 检查 Webhook URL 是否正确
2. 确认机器人已在群聊中
3. 检查 GitHub Actions outbound 网络是否被限制
4. 确认飞书 Webhook URL 未过期

### 选股结果为空

1. 检查股票池是否有效
2. 确认数据源返回数据正常
3. 检查日志中的报错信息

## 高级用法

### 定时触发（可选）

如需每天自动运行，可在 workflow 中添加：

```yaml
on:
  workflow_dispatch:
    inputs:
      ...
  schedule:
    # 每个交易日 9:30 运行（UTC 时间 1:30）
    - cron: '30 1 * * 1-5'
```

### 自定义股票池文件

如果股票池较大，可以提交一个股票池文件到仓库：

```bash
# 在仓库根目录创建 data/stock_pool.txt
echo "600519
000858
002415" > data/stock_pool.txt

# 修改 workflow 中的命令
python -m app.main stock-selector scan --top-n 10 --pool data/stock_pool.txt
```

### 自定义因子权重

修改 `agents/stock_selector/config.yaml` 中的因子权重配置。

## 自定义修改

如需修改选股逻辑或通知格式，编辑：
- `.github/workflows/selector-scan.yml` - Workflow 配置
- `agents/stock_selector/engine.py` - 选股引擎
- `app/main.py` - CLI 入口
