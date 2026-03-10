# 海龟交易监控系统 - Web 界面使用指南

## 快速启动

### Windows

双击运行启动脚本：

```
scripts\start_web_ui.bat
```

或使用命令行：

```bash
python -m app.web_ui --port 8080
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--port` | HTTP 服务器端口 | 8080 |
| `--host` | 监听地址 | 0.0.0.0 |
| `--reload` | 启用热重载（开发模式） | 关闭 |
| `--log-level` | 日志级别 (debug/info/warning/error) | info |

### 访问界面

启动后在浏览器打开：

```
http://localhost:8080
```

---

## 功能界面

### 1. 仪表盘总览

顶部显示 5 个汇总卡片：

| 卡片 | 说明 |
|------|------|
| 📊 持仓数量 | 当前持仓股票数量 |
| 💰 总成本 | 所有持仓的总成本 |
| 📈 总市值 | 所有持仓的当前总市值 |
| 📉 总盈亏 | 总盈亏金额（绿色为正，红色为负） |
| 👁️ 关注股票 | 关注列表中的股票数量 |

### 2. 持仓列表

**显示内容：**
- 代码、名称、现价、成本价
- 盈亏百分比（自动着色：盈利绿色，亏损红色）
- 当前止损价
- 状态标签（持有/盈利/大盈/亏损/止损）

**操作：**
- 点击「移除」按钮可删除已卖出的持仓

**状态标签：**
| 状态 | 条件 |
|------|------|
| ➖ 持有 | 正常持有中 |
| ✅ 盈利 | 盈利 > 10% |
| 🎯 大盈 | 盈利 > 20% |
| ⚠️ 亏损 | 亏损 > 5% |
| ❌ 止损 | 已触及止损价 |

### 3. 关注列表

**显示内容：**
- 代码、名称、现价、突破价
- 状态（🚀 已突破 / ⏳ 等待突破）

**操作：**
- 点击「移除」按钮可从关注列表删除

### 4. 实时提醒

**提醒类型：**

| 级别 | 图标 | 说明 |
|------|------|------|
| 🚨 CRITICAL | 红色 | 止损触发，建议立即退出 |
| ⚠️ WARNING | 橙色 | 接近止损（距离 ≤ 3%） |
| ℹ️ INFO | 蓝色 | 加仓机会、大幅盈利等 |

**操作：**
- 点击「检查提醒」按钮刷新提醒列表

---

## 添加持仓

1. 点击右上角「➕ 添加持仓」按钮
2. 输入股票代码（如：002053）
3. 输入资金量（默认 100,000 元）
4. 点击「确定」

**系统自动计算：**
- 入场价：当前市场价格
- 股数：基于 2% 风险规则和 ATR 计算
- 止损价：入场价 - 2×ATR
- 加仓价：3 个加仓点位（0.5N 递增）

**示例输出：**
```
已添加持仓：002053 云南能投
入场价：¥13.01
股数：2,700
止损价：¥12.29
```

---

## 添加关注

1. 切换到「关注列表」标签
2. 点击列表上方的「➕ 添加关注」按钮
3. 输入股票代码（如：600519）
4. 点击「确定」

**系统自动计算：**
- 突破价：20 日最高价
- 当前价：最新收盘价
- 止损价：当前价 - 2×ATR

---

## API 接口

Web 界面提供 REST API，可用于程序化访问：

### 获取仪表盘数据

```bash
curl http://localhost:8080/api/dashboard
```

**返回示例：**
```json
{
  "positions": [
    {
      "code": "002053",
      "name": "云南能投",
      "current_price": 13.01,
      "entry_price": 13.01,
      "profit_loss_pct": 0.0,
      "current_stop": 12.53,
      "market_value": 35127,
      "total_cost": 35127
    }
  ],
  "watchlist": [...],
  "position_count": 1,
  "watchlist_count": 1,
  "total_cost": 35127,
  "total_value": 35127,
  "total_profit": 0
}
```

### 获取实时提醒

```bash
curl http://localhost:8080/api/alerts
```

### 添加持仓

```bash
curl -X POST http://localhost:8080/api/position/add \
  -H "Content-Type: application/json" \
  -d '{"code": "002053", "capital": 100000}'
```

### 移除持仓

```bash
curl -X POST http://localhost:8080/api/position/remove \
  -H "Content-Type: application/json" \
  -d '{"code": "002053"}'
```

### 添加关注

```bash
curl -X POST http://localhost:8080/api/watchlist/add \
  -H "Content-Type: application/json" \
  -d '{"code": "600519"}'
```

### 移除关注

```bash
curl -X POST http://localhost:8080/api/watchlist/remove \
  -H "Content-Type: application/json" \
  -d '{"code": "600519"}'
```

---

## 数据持久化

所有数据保存在 JSON 文件中：

| 文件 | 说明 | 路径 |
|------|------|------|
| `turtle_positions.json` | 持仓数据 | `data/turtle_positions.json` |
| `turtle_watchlist.json` | 关注列表 | `data/turtle_watchlist.json` |

**持仓数据结构：**
```json
{
  "code": "002053",
  "name": "云南能投",
  "entry_price": 13.01,
  "units": 1,
  "shares_per_unit": 2700,
  "total_shares": 2700,
  "total_cost": 35127,
  "initial_stop": 12.29,
  "current_stop": 12.53,
  "stop_n": 2,
  "atr": 0.36,
  "add_unit_window": 0.18,
  "add_prices": [13.19, 13.37, 13.55],
  "filled_add_prices": []
}
```

---

## 自动更新

Web 界面在以下情况会自动更新数据：

1. **页面加载时** - 自动获取最新数据
2. **点击刷新按钮** - 重新获取所有数据
3. **添加/删除操作后** - 自动刷新列表

**手动刷新：**
- 点击顶部「🔄 刷新」按钮
- 或按浏览器刷新快捷键（F5）

---

## 移动止损计算

系统在每个价格更新时自动计算移动止损：

```python
# 移动止损 = 最高价 - 2×ATR
highest = max(入场价，当前价，近 20 日最高价)
current_stop = highest - atr * 2
```

**特点：**
- 止损价只上移，不下移
- 股价创新高时，止损价自动跟随上移
- 保护已实现利润

---

## 常见问题

### Q1: 端口被占用怎么办？

使用 `--port` 参数指定其他端口：

```bash
python -m app.web_ui --port 9000
```

### Q2: 如何在后台运行？

**Windows (PowerShell):**
```powershell
Start-Job -ScriptBlock { python -m app.web_ui --port 8080 }
```

**Linux/Mac:**
```bash
nohup python -m app.web_ui --port 8080 &
```

### Q3: 如何停止服务器？

在运行终端按 `Ctrl+C`

### Q4: 数据从哪里获取？

系统优先使用本地缓存数据（`data/` 目录），如果缓存不存在或数据不足，会自动从 AkShare 下载最新数据。

### Q5: 可以在手机上访问吗？

可以。确保手机和电脑在同一局域网，使用电脑 IP 地址访问：

```
http://192.168.x.x:8080
```

---

## 相关文档

- [命令行监控使用指南](TURTLE_MONITOR.md)
- [海龟交易法则选股器](TURTLE_SCREENER.md)
- [项目主文档](CLAUDE.md)
