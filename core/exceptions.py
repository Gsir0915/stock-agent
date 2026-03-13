# -*- coding: utf-8 -*-
"""Agent 通用异常类"""


class AgentError(Exception):
    """Agent 基础异常类"""
    pass


class UnknownCommandError(AgentError):
    """未知命令异常"""
    pass


class AgentExecutionError(AgentError):
    """Agent 执行异常"""
    pass


class AgentConfigError(AgentError):
    """Agent 配置异常"""
    pass


class AgentDataError(AgentError):
    """Agent 数据异常"""
    pass
