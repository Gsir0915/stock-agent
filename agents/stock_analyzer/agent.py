# -*- coding: utf-8 -*-
"""个股深度分析 Agent

封装 StockAnalyzer，提供个股全面分析能力。
"""

from pathlib import Path
import sys
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agent_base import BaseAgent, AgentResult
from app.core.analyzer import StockAnalyzer, AnalysisResult
from app.core.technical import TechnicalAnalyzer
from app.core.fundamental import FundamentalAnalyzer
from app.core.sentiment import SentimentAnalyzer
from app.data.repository import get_repository
from app.data.downloader import DataDownloader
from app.utils.stock_names import StockNameService
from app.services.report import ReportService


class StockAnalyzerAgent(BaseAgent):
    """个股深度分析 Agent

    支持的命令:
    - analyze: 完整分析
    - technical: 技术分析
    - fundamental: 基本面分析
    - sentiment: 情绪分析
    """

    name = "stock-analyzer"
    description = "个股深度分析 Agent，提供技术面、基本面、情绪面全面分析"

    def __init__(
        self,
        data_dir: str = "data",
        use_ai: bool = True,
        api_key: Optional[str] = None
    ):
        """初始化个股分析 Agent

        Args:
            data_dir: 数据目录
            use_ai: 是否使用 AI 分析
            api_key: Anthropic API Key
        """
        self.data_dir = data_dir
        self.use_ai = use_ai
        self.api_key = api_key
        self.analyzer = StockAnalyzer(data_dir, use_ai, api_key)

    def execute(self, command: str, **kwargs) -> AgentResult:
        """执行命令

        Args:
            command: 命令名称 (analyze/technical/fundamental/sentiment)
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        if command == "analyze":
            return self._execute_analyze(**kwargs)
        elif command == "technical":
            return self._execute_technical(**kwargs)
        elif command == "fundamental":
            return self._execute_fundamental(**kwargs)
        elif command == "sentiment":
            return self._execute_sentiment(**kwargs)
        else:
            return AgentResult.fail(f"Unknown command: {command}")

    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表"""
        return ["analyze", "technical", "fundamental", "sentiment"]

    def _execute_analyze(
        self,
        code: str,
        download: bool = True,
        **kwargs
    ) -> AgentResult:
        """执行完整分析

        Args:
            code: 股票代码
            download: 是否下载最新数据
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        try:
            name = StockNameService.get_name(code)

            # 执行完整分析
            result = self.analyzer.analyze(code, name, download)

            if not result.success:
                return AgentResult.fail(f"分析失败：{result.errors}")

            # 生成分析报告
            report_service = ReportService(output_dir="reports")
            report_path = report_service.generate_markdown_report(
                code=code,
                stock_name=name,
                technical={
                    "success": result.technical_success,
                    "indicators": result.technical_indicators,
                    "signals": result.technical_signals,
                },
                fundamental={
                    "success": result.fundamental_success,
                    "indicators": result.fundamental_indicators,
                    "score": result.fundamental_score,
                    "rating": result.fundamental_rating,
                    "details": result.fundamental_details,
                },
                news={
                    "success": result.sentiment_success,
                    "news": result.sentiment_news,
                    "summary": result.sentiment_summary,
                }
            )

            return AgentResult.ok(
                data={
                    "code": code,
                    "name": name,
                    "technical": {
                        "success": result.technical_success,
                        "indicators": result.technical_indicators,
                        "signals": result.technical_signals,
                    },
                    "fundamental": {
                        "success": result.fundamental_success,
                        "score": result.fundamental_score,
                        "rating": result.fundamental_rating,
                    },
                    "sentiment": {
                        "success": result.sentiment_success,
                        "summary": result.sentiment_summary,
                    },
                    "report_path": report_path,
                },
                message=f"分析完成，报告已保存至：{report_path}"
            )

        except Exception as e:
            return AgentResult.fail(f"分析失败：{e}")

    def _execute_technical(
        self,
        code: str,
        download: bool = True,
        **kwargs
    ) -> AgentResult:
        """执行技术分析

        Args:
            code: 股票代码
            download: 是否下载最新数据
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        try:
            name = StockNameService.get_name(code)

            # 获取股票数据
            df = self._get_stock_data(code, download)

            if df is None:
                return AgentResult.fail("无法获取股票数据")

            # 执行技术分析
            tech_analyzer = TechnicalAnalyzer()
            result = tech_analyzer.analyze(df)

            if not result.get('success', True):
                return AgentResult.fail(f"技术分析失败：{result.get('error', '未知错误')}")

            return AgentResult.ok(
                data={
                    "code": code,
                    "name": name,
                    "indicators": result.get('indicators', {}),
                    "signals": result.get('signals', []),
                },
                message=f"技术分析完成：{name} ({code})"
            )

        except Exception as e:
            return AgentResult.fail(f"技术分析失败：{e}")

    def _execute_fundamental(
        self,
        code: str,
        **kwargs
    ) -> AgentResult:
        """执行基本面分析

        Args:
            code: 股票代码
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        try:
            name = StockNameService.get_name(code)

            # 获取基本面数据
            downloader = DataDownloader()
            fundamentals = downloader.get_fundamentals(code)

            if not fundamentals:
                return AgentResult.fail("无法获取基本面数据")

            # 执行基本面分析
            fund_analyzer = FundamentalAnalyzer()
            result = fund_analyzer.analyze(fundamentals)

            if not result.get('success', True):
                return AgentResult.fail(f"基本面分析失败：{result.get('error', '未知错误')}")

            return AgentResult.ok(
                data={
                    "code": code,
                    "name": name,
                    "indicators": result.get('indicators', {}),
                    "score": result.get('score', 0),
                    "rating": result.get('rating', 'N/A'),
                    "details": result.get('details', []),
                },
                message=f"基本面分析完成：{name} 评分 {result.get('score', 0)}/100"
            )

        except Exception as e:
            return AgentResult.fail(f"基本面分析失败：{e}")

    def _execute_sentiment(
        self,
        code: str,
        limit: int = 5,
        use_ai: Optional[bool] = None,
        **kwargs
    ) -> AgentResult:
        """执行情绪分析

        Args:
            code: 股票代码
            limit: 新闻数量
            use_ai: 是否使用 AI 分析
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        try:
            name = StockNameService.get_name(code)

            # 获取新闻
            downloader = DataDownloader()
            news = downloader.get_news(code, limit=limit * 2, target_count=limit)

            if not news:
                return AgentResult.ok(
                    data={"news": [], "summary": {"overall": "无新闻数据"}},
                    message="未获取到相关新闻"
                )

            # 执行情绪分析
            use_ai = use_ai if use_ai is not None else self.use_ai
            sentiment_analyzer = SentimentAnalyzer(api_key=self.api_key, use_ai=use_ai)
            result = sentiment_analyzer.analyze(code, news)

            if not result.get('success', False):
                return AgentResult.fail(f"情绪分析失败：{result.get('error', '未知错误')}")

            return AgentResult.ok(
                data={
                    "code": code,
                    "name": name,
                    "news": result.get('analysis', []),
                    "summary": result.get('summary', {}),
                },
                message=f"情绪分析完成：{result.get('summary', {}).get('overall', 'N/A')}"
            )

        except Exception as e:
            return AgentResult.fail(f"情绪分析失败：{e}")

    def _get_stock_data(self, code: str, download: bool = True):
        """获取股票数据

        Args:
            code: 股票代码
            download: 是否下载最新数据

        Returns:
            DataFrame 股票数据
        """
        repository = get_repository(self.data_dir)
        df = repository.load_stock_data(code)

        if df is None or len(df) < 60:
            if download:
                downloader = DataDownloader()
                df = downloader.download_stock_history(code)
                repository.save_stock_data(code, df)
            else:
                return None

        return df
