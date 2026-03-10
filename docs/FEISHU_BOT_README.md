# 飞书机器人功能

## 功能概述

飞书机器人功能允许用户在飞书群聊中@机器人并发送股票代码，机器人会自动执行完整的股票分析并将报告发送回群聊。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```bash
# 飞书机器人配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_BOT_PORT=8080

# AI 分析（可选，用于情绪分析）
ANTHROPIC_API_KEY=sk-xxxxx

# 数据配置
DATA_DIR=data
REPORTS_DIR=reports
```

### 3. 启动机器人

```bash
python -m app.bot
```

### 4. 配置飞书开放平台

详细配置步骤请参考 [docs/FEISHU_BOT_SETUP.md](docs/FEISHU_BOT_SETUP.md)

### 5. 测试

在飞书群聊中：
- 发送：`@机器人 600519`
- 或发送：`@机器人 帮助`

## 架构设计

```
飞书群聊 → 飞书开放平台 → HTTP 服务器 (server.py)
                                    ↓
                              消息处理器 (handler.py)
                                    ↓
                              命令解析器 (commands.py)
                                    ↓
                              股票分析引擎 (StockAnalyzer)
                                    ↓
                              飞书 API 客户端 (feishu_client.py)
                                    ↓
飞书群聊 ← 交互式卡片消息 ←────────────────┘
```

## 模块说明

### app/bot/

| 文件 | 说明 |
|------|------|
| `__init__.py` | 模块入口 |
| `__main__.py` | CLI 启动入口 |
| `server.py` | FastAPI HTTP 服务器，接收飞书事件推送 |
| `handler.py` | 消息处理器，协调分析和回复 |
| `feishu_client.py` | 飞书 API 客户端，发送消息和卡片 |
| `commands.py` | 命令解析器，识别股票代码和命令 |

## 支持的命令

| 命令格式 | 说明 |
|----------|------|
| `@bot 600519` | 直接发送股票代码 |
| `@bot 分析 600519` | 带命令前缀 |
| `@bot 贵州茅台` | 发送股票名称 |
| `@bot 帮助` | 查看使用指南 |

## 消息处理流程

1. **接收事件**: 飞书开放平台将群聊消息推送到 `/feishu/event` 端点
2. **验证请求**: 验证飞书签名和 challenge
3. **解析命令**: 从消息中提取股票代码
4. **执行分析**: 调用 `StockAnalyzer` 执行技术分析、基本面分析、情绪分析
5. **生成报告**: 生成交互式卡片消息
6. **发送回复**: 通过飞书 API 将报告发送到群聊

## 配置详解

### FEISHU_APP_ID

飞书应用 ID，在飞书开放平台创建应用后获取。

### FEISHU_APP_SECRET

飞书应用密钥，用于获取 `tenant_access_token`。

### FEISHU_VERIFICATION_TOKEN

事件订阅验证 token，用于验证请求来源。

### FEISHU_BOT_PORT

HTTP 服务器监听端口，默认为 8080。

## 本地开发

### 使用内网穿透

飞书要求事件订阅 URL 必须是公网可访问的地址。本地开发时可以使用内网穿透工具：

```bash
# 使用 ngrok
ngrok http 8080

# 将生成的 https 地址配置到飞书开放平台
# 例如：https://abc123.ngrok.io/feishu/event
```

### 测试端点

```bash
# 健康检查
curl http://localhost:8080/health

# 模拟飞书事件（测试用）
curl -X POST http://localhost:8080/feishu/event \
  -H "Content-Type: application/json" \
  -d '{"challenge": "test123"}'
```

## 部署建议

### 生产环境配置

1. **使用 HTTPS**: 通过 Nginx 反向代理配置 HTTPS
2. **进程管理**: 使用 systemd 或 supervisor 管理进程
3. **日志管理**: 配置日志轮转
4. **限流保护**: 添加请求频率限制

### Nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /feishu/event {
        proxy_pass http://127.0.0.1:8080/feishu/event;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排查

### 收不到消息推送

1. 检查事件订阅 URL 是否公网可访问
2. 确认 URL 验证已通过
3. 检查机器人是否在群聊中
4. 确认消息是否@了机器人

### 无法发送消息

1. 检查 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 是否正确
2. 确认已配置 `im:message` 权限
3. 确认应用已发布

### 签名验证失败

检查 `FEISHU_VERIFICATION_TOKEN` 是否正确配置。

## 安全注意事项

1. **保护凭证**: 不要将 `.env` 文件提交到版本控制
2. **启用签名验证**: 确保请求来源可信
3. **限流保护**: 生产环境建议添加请求频率限制
4. **HTTPS**: 生产环境必须使用 HTTPS

## 参考文档

- [飞书开放平台](https://open.feishu.cn/)
- [配置指南](docs/FEISHU_BOT_SETUP.md)
- [事件订阅机制](https://open.feishu.cn/document/server-docs/event-subscription-event/overview)
- [消息发送 API](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)
