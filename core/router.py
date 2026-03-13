# -*- coding: utf-8 -*-
"""Agent 路由协调器"""

from typing import Dict, List, Optional
from .agent_base import BaseAgent, AgentResult
from .exceptions import AgentError, UnknownCommandError, AgentExecutionError


class AgentRouter:
    """Agent 路由协调器

    职责:
    1. 注册/管理所有子 Agent
    2. 解析用户命令，分发到对应 Agent
    3. 聚合多个 Agent 的结果 (如需)
    4. 处理 Agent 间通信

    Attributes:
        agents: 已注册的子 Agent 字典
    """

    def __init__(self, auto_register: bool = True):
        """初始化路由

        Args:
            auto_register: 是否自动注册内置 Agent，默认 True
        """
        self.agents: Dict[str, BaseAgent] = {}
        if auto_register:
            self._register_builtin_agents()

    def _register_builtin_agents(self):
        """注册内置子 Agent"""
        # 延迟导入，避免循环依赖
        try:
            from agents.turtle_screener.agent import TurtleScreenerAgent
            self.register(TurtleScreenerAgent())
        except ImportError as e:
            print(f"[WARN] 无法加载 TurtleScreenerAgent: {e}")

        try:
            from agents.stock_analyzer.agent import StockAnalyzerAgent
            self.register(StockAnalyzerAgent())
        except ImportError as e:
            print(f"[WARN] 无法加载 StockAnalyzerAgent: {e}")

        try:
            from agents.stock_selector.agent import SelectorAgent
            self.register(SelectorAgent())
        except ImportError as e:
            print(f"[WARN] 无法加载 SelectorAgent: {e}")

    def register(self, agent: BaseAgent):
        """注册子 Agent

        Args:
            agent: Agent 实例
        """
        self.agents[agent.name] = agent

    def unregister(self, agent_name: str):
        """注销子 Agent

        Args:
            agent_name: Agent 名称
        """
        if agent_name in self.agents:
            del self.agents[agent_name]

    def list_agents(self) -> List[str]:
        """列出所有已注册的 Agent

        Returns:
            Agent 名称列表
        """
        return list(self.agents.keys())

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """获取指定 Agent

        Args:
            agent_name: Agent 名称

        Returns:
            Agent 实例，不存在则返回 None
        """
        return self.agents.get(agent_name)

    def dispatch(self, agent_name: str, command: str, **kwargs) -> AgentResult:
        """分发命令到指定 Agent

        Args:
            agent_name: 目标 Agent 名称
            command: 命令名称
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果

        Raises:
            AgentError: Agent 不存在
            UnknownCommandError: 命令不支持
            AgentExecutionError: 执行出错
        """
        if agent_name not in self.agents:
            raise AgentError(f"Unknown agent: {agent_name}. Available: {list(self.agents.keys())}")

        agent = self.agents[agent_name]

        # 检查命令是否支持
        capabilities = agent.get_capabilities()
        if command not in capabilities:
            raise UnknownCommandError(
                f"Unknown command '{command}' for agent '{agent_name}'. "
                f"Supported: {capabilities}"
            )

        try:
            return agent.execute(command, **kwargs)
        except Exception as e:
            raise AgentExecutionError(f"Agent '{agent_name}' execution failed: {e}")

    def broadcast(self, command: str, **kwargs) -> Dict[str, AgentResult]:
        """广播命令到所有 Agent

        Args:
            command: 命令名称
            **kwargs: 命令参数

        Returns:
            Dict[agent_name, AgentResult] 各 Agent 执行结果
        """
        results = {}
        for name, agent in self.agents.items():
            try:
                results[name] = agent.execute(command, **kwargs)
            except Exception as e:
                results[name] = AgentResult.fail(str(e))
        return results

    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """获取所有 Agent 的能力列表

        Returns:
            Dict[agent_name, capabilities]
        """
        return {name: agent.get_capabilities() for name, agent in self.agents.items()}
