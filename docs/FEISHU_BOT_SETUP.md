# 飞书机器人配置指南

本指南帮助您完成飞书开放平台的配置，使股票分析机器人能够接收群聊消息并自动回复。

## 前置准备

1. 拥有飞书企业账号（个人或企业均可）
2. 能够访问飞书开放平台：https://open.feishu.cn/

## 步骤一：创建企业自建应用

### 1. 进入开放平台

访问 [飞书开放平台](https://open.feishu.cn/) 并登录

### 2. 创建新应用

1. 点击控制台中的 **创建企业自建应用**
2. 填写应用信息：
   - **应用名称**：股票分析机器人（可自定义）
   - **应用图标**：可选上传
   - **应用描述**：A 股投资分析助手
3. 点击 **创建**

### 3. 获取凭证

创建成功后，在应用详情页获取：
- **App ID**（例如：`cli_a1b2c3d4e5f6`）
- **App Secret**（点击 **查看** 获取）

将这两个值记录好，后续需要配置到 `.env` 文件中。

## 步骤二：配置机器人

### 1. 添加机器人功能

1. 在应用管理页面，点击左侧 **添加应用能力**
2. 找到 **机器人** 并点击添加

### 2. 配置机器人信息

1. 进入机器人配置页面
2. 设置机器人名称和头像
3. 记录 **Bot ID**（后续可能用到）

## 步骤三：配置事件订阅

### 1. 启用事件订阅

1. 在左侧菜单找到 **事件订阅**
2. 点击 **开通** 事件订阅功能

### 2. 配置事件接收 URL

**注意**：飞书要求事件接收 URL 必须是公网可访问的地址。

如果您在本地开发，可以使用以下方案之一：

**方案 A：使用内网穿透工具（推荐用于测试）**
```bash
# 使用 ngrok
ngrok http 8080

# 使用 frp
# 配置 frpc.ini 后启动
```

**方案 B：部署到云服务器**
- 将应用部署到具有公网 IP 的服务器
- 使用 Nginx 反向代理并配置 HTTPS

填写 URL 格式：`https://your-domain.com/feishu/event`

### 3. 获取 Verification Token

开通事件订阅后，系统会生成一个 **Verification Token**，点击 **查看** 并记录。

### 4. 订阅事件

1. 点击 **订阅事件**
2. 搜索并订阅以下事件：
   - `im.message.receive_v1` - 接收消息事件
3. 点击 **提交** 保存

### 5. URL 验证

飞书会向您配置的 URL 发送验证请求，确保服务器能正确响应 challenge。

启动本地服务器测试：
```bash
python -m app.bot --port 8080
```

然后在飞书开放平台点击 **重新验证**

## 步骤四：配置权限

### 1. 添加权限

1. 在左侧菜单进入 **权限管理**
2. 点击 **申请权限**
3. 搜索并添加以下权限：
   - `im:message` - 发送和读取消息
   - `im:chat` - 获取群聊信息
   - `auth:tenant_access_token` - 获取访问令牌

### 2. 发布应用

权限配置完成后，点击 **发布应用** 使配置生效。

## 步骤五：将机器人添加到群聊

### 方式一：通过群聊邀请

1. 在飞书群聊中，点击右上角 **...**
2. 选择 **添加成员**
3. 找到您的机器人并添加

### 方式二：通过私信

1. 在飞书中搜索您的机器人名称
2. 打开与机器人的私信
3. 点击 **添加到群聊**

## 步骤六：配置环境变量

将获取到的配置信息填入 `.env` 文件：

```bash
# .env
FEISHU_APP_ID=cli_a1b2c3d4e5f6
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_BOT_PORT=8080

# 其他配置
ANTHROPIC_API_KEY=sk-xxxxx
DATA_DIR=data
REPORTS_DIR=reports
```

## 步骤七：启动并测试

### 1. 启动服务器

```bash
# 安装依赖
pip install -r requirements.txt

# 启动机器人
python -m app.bot
```

### 2. 测试消息

在飞书群聊中：
1. @机器人并发送股票代码，例如：`@股票机器人 600519`
2. 等待分析完成（约 10-30 秒）
3. 查看机器人发送的分析报告卡片

### 3. 测试帮助命令

发送：`@股票机器人 帮助`

## 常见问题

### Q: 收不到消息推送？

**检查清单**：
- [ ] 事件订阅 URL 是否公网可访问
- [ ] URL 验证是否通过
- [ ] 是否订阅了 `im.message.receive_v1` 事件
- [ ] 机器人是否在群聊中
- [ ] 消息是否@了机器人

### Q: 无法发送消息？

**检查清单**：
- [ ] `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 是否正确
- [ ] 是否配置了 `im:message` 权限
- [ ] 应用是否已发布

### Q: 签名验证失败？

检查 `FEISHU_VERIFICATION_TOKEN` 是否正确配置。

### Q: 本地开发如何测试？

使用 ngrok 等内网穿透工具：
```bash
# 安装 ngrok
# 访问 https://ngrok.com/ 下载

# 启动
ngrok http 8080

# 将生成的 https 地址配置到飞书开放平台
# 例如：https://abc123.ngrok.io/feishu/event
```

## 安全建议

1. **保护 App Secret**：不要将 `.env` 文件提交到版本控制
2. **启用签名验证**：代码中已实现签名验证逻辑，确保请求来源可信
3. **限流保护**：生产环境建议添加请求频率限制
4. **HTTPS**：生产环境必须使用 HTTPS

## 后续扩展

- 支持更多命令（如 `help`, `自选股` 等）
- 支持定时报告推送
- 支持私聊机器人
- 添加消息速率限制

## 参考文档

- [飞书开放平台文档](https://open.feishu.cn/document/home)
- [事件订阅机制](https://open.feishu.cn/document/server-docs/event-subscription-event/overview)
- [消息发送 API](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM)
- [机器人开发指南](https://open.feishu.cn/document/ukTMukTMukTM/uYjJxQjL0cjM0YjNzYjD)
