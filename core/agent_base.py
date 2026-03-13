# -*- coding: utf-8 -*-
"""Agent 基类定义"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Optional[Any] = None, message: Optional[str] = None, **metadata) -> "AgentResult":
        """创建成功结果"""
        return cls(success=True, data=data, message=message, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata) -> "AgentResult":
        """创建失败结果"""
        return cls(success=False, error=error, metadata=metadata)


class BaseAgent(ABC):
    """Agent 基类

    所有子 Agent 必须继承此类并实现抽象方法。

    Attributes:
        name: Agent 名称，用于路由识别
        description: Agent 描述信息
    """

    name: str = "base"
    description: str = "Base Agent"

    @abstractmethod
    def execute(self, command: str, **kwargs) -> AgentResult:
        """执行命令

        Args:
            command: 命令名称
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表

        Returns:
            命令名称列表
        """
        pass

    def help(self) -> str:
        """返回帮助信息

        Returns:
            帮助文本
        """
        capabilities = self.get_capabilities()
        return f"{self.name}: {self.description}\n支持的命令：{', '.join(capabilities) if capabilities else '无'}"
