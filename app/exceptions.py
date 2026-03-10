# -*- coding: utf-8 -*-
"""
自定义异常体系
所有股票分析相关的异常都继承自 StockAgentError
"""


class StockAgentError(Exception):
    """股票分析器基类异常"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class DataDownloadError(StockAgentError):
    """数据下载失败异常"""
    pass


class DataNotFoundError(StockAgentError):
    """数据不存在异常"""
    pass


class DataSourceError(StockAgentError):
    """数据源异常"""
    pass


class AnalysisError(StockAgentError):
    """分析计算异常"""
    pass


class TechnicalAnalysisError(AnalysisError):
    """技术分析异常"""
    pass


class FundamentalAnalysisError(AnalysisError):
    """基本面分析异常"""
    pass


class SentimentAnalysisError(AnalysisError):
    """情绪分析异常"""
    pass


class ReportGenerationError(StockAgentError):
    """报告生成异常"""
    pass


class NotificationError(StockAgentError):
    """通知发送异常"""
    pass


class ConfigError(StockAgentError):
    """配置异常"""
    pass
