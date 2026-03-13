---
name: start-bot-with-tunnel
description: 启动飞书机器人并创建 ngrok 隧道，用于本地开发和测试
---

# 飞书机器人本地开发

启动飞书机器人 HTTP 服务器并自动创建 ngrok 隧道，用于本地开发和测试双向互动功能。

## 用法

```bash
python -m app.bot --port 8080 &
ngrok http 8080
```

或者使用快捷脚本（Windows）：
```bash
.\scripts\start_bot_with_tunnel.bat
```

## 功能

- 启动飞书机器人 HTTP 服务器
- 自动创建 ngrok 隧道，将本地服务暴露到公网
- 支持双向互动（接收和处理飞书消息）

## 配置要求

| 变量名 | 说明 |
|--------|------|
| `FEISHU_APP_ID` | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 飞书应用密钥 |
| `FEISHU_VERIFICATION_TOKEN` | 事件订阅验证 token |
| `FEISHU_BOT_PORT` | HTTP 服务器端口（默认：8080） |

## 本地开发（无公网域名）

**步骤 1: 安装 cloudflared**
```bash
winget install Cloudflare.cloudflared
```

**步骤 2: 启动机器人和隧道（两个终端）**
```bash
# 终端 1
python -m app.bot --port 8080

# 终端 2
cloudflared tunnel --url http://localhost:8080
```
