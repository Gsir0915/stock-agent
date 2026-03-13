# Stock Agent 重构计划

## 目标架构

将当前单体应用重构为 **主 Agent + 子 Agent** 的多 Agent 架构，提升模块化程度和可扩展性。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    stock-agent (主 Agent)                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              CLI 入口 (main.py)                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            路由协调器 (core/router.py)               │    │
│  │  - 命令解析  - Agent 分发  - 结果聚合                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│ turtle-       │   │ stock-          │   │ selector-     │
│ screener      │   │ analyzer        │   │ agent         │
├───────────────┤   ├─────────────────┤   ├───────────────┤
│ 海龟交易选股  │   │ 个股深度分析    │   │ 多因子选股    │
│ • 全市场扫描  │   │ • 技术分析      │   │ • 市场环境判断│
│ • 持仓监控    │   │ • 基本面分析    │   │ • 动态权重    │
│ • 买卖信号    │   │ • 情绪分析      │   │ • Top N 推荐  │
└───────────────┘   │ • 报告生成      │   └───────────────┘
                    └─────────────────┘
```

---

## 目录结构

```
stock-agent/
├── main.py                     # 主入口 CLI
├── config.py                   # 全局配置
├── REFACTOR_PLAN.md            # 重构计划 (本文档)
│
├── core/                       # 核心层 (新增)
│   ├── __init__.py
│   ├── router.py               # 路由协调器
│   ├── agent_base.py           # Agent 基类
│   └── exceptions.py           # 通用异常
│
├── agents/                     # 子 Agent 模块
│   ├── __init__.py
│   │
│   ├── turtle_screener/        # 海龟选股 Agent
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 实现
│   │   ├── screener.py         # 选股逻辑 (现有迁移)
│   │   ├── monitor.py          # 持仓监控 (现有迁移)
│   │   └── signals.py          # 买卖信号 (现有迁移)
│   │
│   ├── stock_analyzer/         # 个股分析 Agent
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 实现
│   │   ├── analyzer.py         # 分析引擎 (现有迁移)
│   │   ├── report.py           # 报告生成 (现有迁移)
│   │   └── technical.py        # 技术分析
│   │
│   └── stock_selector/         # 多因子选股 Agent
│       ├── __init__.py
│       ├── agent.py            # Agent 实现 (新增)
│       ├── engine.py           # 选股引擎 (现有)
│       └── factors/            # 因子库 (现有)
│
├── shared/                     # 共享模块
│   ├── __init__.py
│   ├── data/                   # 数据访问层
│   │   ├── downloader.py
│   │   ├── repository.py
│   │   └── sources/
│   ├── utils/                  # 工具类
│   │   ├── logger.py
│   │   ├── stock_names.py
│   │   └── helpers.py
│   └── services/               # 服务层
│       ├── notification.py     # 飞书通知
│       └── config_handler.py   # 配置处理
│
└── cli/                        # CLI 命令定义 (新增)
    ├── __init__.py
    ├── commands.py             # 命令注册
    └── handlers.py             # 命令处理
```

---

## Agent 基类定义

```python
# core/agent_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None

class BaseAgent(ABC):
    """Agent 基类"""

    name: str = "base"
    description: str = "Base Agent"

    @abstractmethod
    def execute(self, command: str, **kwargs) -> AgentResult:
        """
        执行命令

        Args:
            command: 命令名称
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表"""
        pass

    def help(self) -> str:
        """返回帮助信息"""
        return f"{self.name}: {self.description}\n支持的命令：{', '.join(self.get_capabilities())}"
```

---

## 路由协调器

```python
# core/router.py
from typing import Dict, List
from .agent_base import BaseAgent, AgentResult

class AgentRouter:
    """
    Agent 路由协调器

    职责:
    1. 注册/管理所有子 Agent
    2. 解析用户命令，分发到对应 Agent
    3. 聚合多个 Agent 的结果 (如需)
    4. 处理 Agent 间通信
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._register_builtin_agents()

    def _register_builtin_agents(self):
        """注册内置子 Agent"""
        # 延迟导入，避免循环依赖
        from agents.turtle_screener.agent import TurtleScreenerAgent
        from agents.stock_analyzer.agent import StockAnalyzerAgent
        from agents.stock_selector.agent import SelectorAgent

        self.register(TurtleScreenerAgent())
        self.register(StockAnalyzerAgent())
        self.register(SelectorAgent())

    def register(self, agent: BaseAgent):
        """注册子 Agent"""
        self.agents[agent.name] = agent

    def list_agents(self) -> List[str]:
        """列出所有已注册的 Agent"""
        return list(self.agents.keys())

    def dispatch(self, agent_name: str, command: str, **kwargs) -> AgentResult:
        """
        分发命令到指定 Agent

        Args:
            agent_name: 目标 Agent 名称
            command: 命令名称
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        if agent_name not in self.agents:
            return AgentResult(
                success=False,
                error=f"Unknown agent: {agent_name}"
            )

        agent = self.agents[agent_name]
        return agent.execute(command, **kwargs)

    def broadcast(self, command: str, **kwargs) -> Dict[str, AgentResult]:
        """广播命令到所有 Agent"""
        results = {}
        for name, agent in self.agents.items():
            try:
                results[name] = agent.execute(command, **kwargs)
            except Exception as e:
                results[name] = AgentResult(success=False, error=str(e))
        return results
```

---

## CLI 命令规范

### 命令格式

```bash
python -m app.main <agent> <command> [options]
```

### 命令映射表

| 命令 | 目标 Agent | 说明 |
|------|-----------|------|
| `turtle scan [options]` | turtle-screener | 海龟选股扫描 |
| `turtle monitor <subcmd>` | turtle-screener | 持仓监控 |
| `analyze <stock> [opts]` | stock-analyzer | 个股分析 |
| `selector scan [options]` | selector-agent | 多因子选股 |
| `selector regime` | selector-agent | 市场环境 |

### CLI 入口

```python
# main.py
import argparse
from core.router import AgentRouter

def main():
    parser = argparse.ArgumentParser(description="Stock Agent - 智能股票分析系统")
    parser.add_argument("agent", nargs="?", help="目标 Agent")
    parser.add_argument("command", nargs="?", help="命令")
    parser.add_argument("--args", nargs="*", help="命令参数")

    # 兼容旧命令 (临时)
    parser.add_argument("--analyze", help="[兼容] 分析股票代码")

    args = parser.parse_args()

    if args.analyze:
        # 兼容旧命令
        args.agent = "stock-analyzer"
        args.command = "analyze"
        args.args = [args.analyze]

    if not args.agent or not args.command:
        parser.print_help()
        return

    # 路由分发
    router = AgentRouter()
    result = router.dispatch(args.agent, args.command, args=args.args)

    if result.success:
        print(result.data)
    else:
        print(f"Error: {result.error or result.message}")

if __name__ == "__main__":
    main()
```

---

## 迁移步骤

### 第一阶段：基础架构

- [ ] 创建 `core/` 目录和基类
- [ ] 创建 `agents/` 目录结构
- [ ] 创建 `shared/` 目录并迁移共享代码
- [ ] 创建 `cli/` 命令定义

### 第二阶段：Agent 迁移

#### turtle-screener
- [ ] 迁移 `turtle_screener/` 到 `agents/turtle_screener/`
- [ ] 创建 `agents/turtle_screener/agent.py`
- [ ] 创建 `agents/turtle_screener/__init__.py`
- [ ] 测试独立运行

#### stock-analyzer
- [ ] 迁移 `core/analyzer.py` 到 `agents/stock_analyzer/`
- [ ] 迁移 `core/technical.py` 到 `agents/stock_analyzer/`
- [ ] 迁移 `core/fundamental.py` 到 `agents/stock_analyzer/`
- [ ] 迁移 `core/sentiment.py` 到 `agents/stock_analyzer/`
- [ ] 迁移 `services/report.py` 到 `agents/stock_analyzer/`
- [ ] 创建 `agents/stock_analyzer/agent.py`
- [ ] 测试独立运行

#### stock-selector
- [ ] 移动 `agents/stock_selector/` (已存在)
- [ ] 创建 `agents/stock_selector/agent.py`
- [ ] 测试独立运行

### 第三阶段：CLI 整合

- [ ] 更新 `main.py` 为新入口
- [ ] 实现路由分发逻辑
- [ ] 移除旧 CLI 入口 (`python -m app.turtle_screener` 等)
- [ ] 更新命令帮助信息

### 第四阶段：测试与优化

- [ ] 单元测试：各 Agent
- [ ] 集成测试：CLI 命令
- [ ] 性能优化：数据加载
- [ ] 文档更新

---

## 兼容性说明

### 环境变量保持不变

```bash
ANTHROPIC_API_KEY=xxx
FEISHU_WEBHOOK_URL=xxx
DATA_DIR=data
REPORTS_DIR=reports
```

### 配置文件保持不变

- `agents/stock_selector/config.yaml` - 多因子选股配置
- `.env` - 环境变量

### 数据格式保持不变

- CSV 数据格式
- 报告格式
- 日志格式

---

## 验收标准

1. **功能完整性**
   - [ ] 所有原有功能正常工作
   - [ ] CLI 命令响应正确

2. **代码质量**
   - [ ] 无循环依赖
   - [ ] 单元测试通过率 100%
   - [ ] 类型注解完整

3. **文档**
   - [ ] README.md 更新
   - [ ] 各 Agent 有使用说明
   - [ ] 迁移指南完成

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 循环依赖 | 使用延迟导入，清晰定义依赖方向 |
| 数据不一致 | 共享数据层统一由 `shared/data/` 管理 |
| CLI 参数解析复杂 | 使用 argparse 子命令模式 |
| 测试覆盖率下降 | 先写测试用例，确保迁移后通过 |

---

## 时间估算

| 阶段 | 预计时间 |
|------|---------|
| 基础架构 | 1-2 小时 |
| Agent 迁移 | 3-4 小时 |
| CLI 整合 | 1-2 小时 |
| 测试优化 | 2-3 小时 |
| **总计** | **7-11 小时** |

---

## 下一步

1. 确认本重构计划
2. 创建基础架构代码
3. 逐个 Agent 迁移
4. 测试验证
