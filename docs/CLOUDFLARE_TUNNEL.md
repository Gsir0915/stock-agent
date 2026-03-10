# 使用 Cloudflare Tunnel 进行本地开发

## 方案说明

Cloudflare Tunnel 可以创建一个从 Cloudflare 边缘网络到你本地服务器的安全隧道，无需公网 IP 和域名即可生成一个 `https://xxx.trycloudflare.com` 的临时域名。

**优点**：
- ✅ 免费，无需注册账号
- ✅ 自动 HTTPS，符合飞书要求
- ✅ 配置简单，一行命令启动
- ✅ 无需安装额外客户端（使用 cloudflared）

---

## 步骤一：安装 cloudflared

### Windows

```bash
# 使用 winget（推荐）
winget install Cloudflare.cloudflared

# 或使用 chocolatey
choco install cloudflared

# 或手动下载
# 访问 https://github.com/cloudflare/cloudflared/releases
# 下载 cloudflared-windows-amd64.exe 并放到 PATH 目录
```

### macOS

```bash
brew install cloudflared
```

### Linux

```bash
# Debian/Ubuntu
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 或直接下载二进制
curl -L --output /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo chmod +x /usr/local/bin/cloudflared
```

### 验证安装

```bash
cloudflared --version
```

---

## 步骤二：启动飞书机器人和 Tunnel

### 终端 1：启动机器人

```bash
# 启动飞书机器人 HTTP 服务器
python -m app.bot --port 8080
```

机器人会监听 `http://localhost:8080`

### 终端 2：启动 Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8080
```

启动后会看到类似输出：

```
+--------------------------------------------------------------------+
|  Your quick Tunnel has been created!                               |
|                                                                    |
|  Visit it at:                                                      |
|  https://abc123-xyz-456-def-789.trycloudflare.com                  |
+--------------------------------------------------------------------+
```

**记住这个 https 地址**，这就是飞书开放平台需要配置的事件订阅 URL。

---

## 步骤三：配置飞书开放平台

1. 进入 [飞书开放平台](https://open.feishu.cn/)
2. 选择你的应用 → 事件订阅
3. 配置事件接收 URL：
   ```
   https://abc123-xyz-456-def-789.trycloudflare.com/feishu/event
   ```
   （替换为你实际的 cloudflare URL）

4. 点击 **保存**，飞书会发送 challenge 请求进行验证

5. 验证通过后，订阅 `im.message.receive_v1` 事件

---

## 步骤四：测试

1. 确保机器人和 tunnel 都在运行
2. 在飞书群聊中 @机器人并发送股票代码
3. 查看 tunnel 终端的日志输出
4. 机器人应该回复分析报告

---

## 进阶配置

### 使用固定域名（可选）

如果你有自己的域名并绑定到 Cloudflare，可以创建持久化 Tunnel：

```bash
# 1. 登录 Cloudflare Dashboard 创建 Tunnel
# 2. 获取 tunnel token
# 3. 配置 tunnel

cloudflared tunnel run --token YOUR_TOKEN
```

### 配置本地 hosts（可选）

如果想使用自定义本地域名：

```bash
# 1. 创建 tunnel 配置文件
cloudflared tunnel create my-tunnel

# 2. 配置 config.yml
tunnel: my-tunnel
credentials-file: C:\Users\你的用户名\.cloudflared\YOUR_TUNNEL_ID.json
ingress:
  - hostname: bot.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404

# 3. 启动
cloudflared tunnel run my-tunnel
```

### 后台运行（可选）

```bash
# Linux/macOS
nohup cloudflared tunnel --url http://localhost:8080 > tunnel.log 2>&1 &

# Windows PowerShell
Start-Job -ScriptBlock { cloudflared tunnel --url http://localhost:8080 }
```

---

## 故障排查

### Tunnel 启动失败

```bash
# 检查端口是否被占用
netstat -ano | findstr :8080

# 更换端口
python -m app.bot --port 9000
cloudflared tunnel --url http://localhost:9000
```

### 飞书验证失败

1. 确保 robot 和 tunnel 都在运行
2. 检查 URL 是否正确（包含 `/feishu/event`）
3. 查看 tunnel 日志是否有请求进入
4. 确认机器人代码能正确处理 challenge 请求

### Tunnel 连接不稳定

Cloudflare Tunnel 免费版本可能会有连接中断，建议：
- 保持终端运行，不要关闭
- 如果断开，重新运行 `cloudflared tunnel --url` 命令
- URL 会变化，需要更新飞书开放平台配置

---

## 快捷脚本

### Windows PowerShell

创建 `start-bot.ps1`：

```powershell
# 启动机器人
Start-Process python -ArgumentList "-m", "app.bot", "--port", "8080"

# 等待 2 秒
Start-Sleep -Seconds 2

# 启动 tunnel
cloudflared tunnel --url http://localhost:8080
```

### Linux/macOS

创建 `start-bot.sh`：

```bash
#!/bin/bash

# 启动机器人
python -m app.bot --port 8080 &
BOT_PID=$!

# 等待 2 秒
sleep 2

# 启动 tunnel
cloudflared tunnel --url http://localhost:8080

# 清理
kill $BOT_PID
```

---

## 参考链接

- [Cloudflare Tunnel 官方文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [cloudflared GitHub](https://github.com/cloudflare/cloudflared)
- [飞书事件订阅文档](https://open.feishu.cn/document/server-docs/event-subscription-event/overview)
