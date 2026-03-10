# -*- coding: utf-8 -*-
"""
分析引擎模块
协调技术分析、基本面分析、情绪分析模块
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import pandas as pd

from .technical import TechnicalAnalyzer, TechnicalIndicators
from .fundamental import FundamentalAnalyzer, FundamentalIndicators
from .sentiment import SentimentAnalyzer
from ..data.downloader import DataDownloader
from ..data.repository import DataRepository, get_repository
from ..exceptions import AnalysisError, DataNotFoundError
from ..utils.logger import get_logger

logger = get_logger("core.analyzer")


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    code: str  # 股票代码
    name: str  # 股票名称
    success: bool = True  # 是否成功

    # 技术分析结果
    technical_success: bool = False
    technical_indicators: Dict[str, Any] = field(default_factory=dict)
    technical_signals: List[Dict[str, str]] = field(default_factory=list)

    # 基本面分析结果
    fundamental_success: bool = False
    fundamental_indicators: Dict[str, Any] = field(default_factory=dict)
    fundamental_score: int = 0
    fundamental_rating: str = ""
    fundamental_details: List[str] = field(default_factory=list)

    # 情绪分析结果
    sentiment_success: bool = False
    sentiment_news: List[Dict[str, str]] = field(default_factory=list)
    sentiment_summary: Dict[str, Any] = field(default_factory=dict)

    # 错误信息
    errors: Dict[str, str] = field(default_factory=dict)


class StockAnalyzer:
    """股票分析引擎"""

    def __init__(
        self,
        data_dir: str = "data",
        use_ai: bool = True,
        api_key: Optional[str] = None
    ):
        """
        初始化分析引擎

        Args:
            data_dir: 数据目录
            use_ai: 是否使用 AI 分析
            api_key: API Key
        """
        self.data_dir = data_dir
        self.use_ai = use_ai
        self.api_key = api_key

        # 初始化各模块
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer(api_key=api_key, use_ai=use_ai)

        # 数据服务
        self.downloader = DataDownloader()
        self.repository = get_repository(data_dir)

    def analyze(
        self,
        code: str,
        name: str,
        download: bool = True,
        skip_days: int = 3
    ) -> AnalysisResult:
        """
        执行完整分析

        Args:
            code: 股票代码
            name: 股票名称
            download: 是否下载最新数据
            skip_days: 数据缓存宽容度

        Returns:
            AnalysisResult 分析结果

        Raises:
            AnalysisError: 分析失败时抛出
        """
        logger.info(f"开始分析股票：{code} ({name})")

        result = AnalysisResult(code=code, name=name)

        try:
            # 步骤 1: 准备数据
            df = self._prepare_data(code, download, skip_days)

            if df is None:
                result.success = False
                result.errors["data"] = "无法获取股票数据"
                return result

            # 步骤 2: 技术分析
            logger.info("执行技术分析...")
            tech_result = self._run_technical_analysis(df)
            result.technical_success = tech_result.get("success", False)
            if result.technical_success:
                result.technical_indicators = tech_result.get("indicators", {})
                # signals 已经是字典列表
                result.technical_signals = tech_result.get("signals", [])
            else:
                result.errors["technical"] = tech_result.get("error", "未知错误")

            # 步骤 3: 基本面分析
            logger.info("执行基本面分析...")
            fund_result = self._run_fundamental_analysis(code)
            result.fundamental_success = fund_result.get("success", False)
            if result.fundamental_success:
                result.fundamental_indicators = fund_result.get("indicators", {})
                result.fundamental_score = fund_result.get("score", 0)
                result.fundamental_rating = fund_result.get("rating", "")
                result.fundamental_details = fund_result.get("details", [])
            else:
                result.errors["fundamental"] = fund_result.get("error", "未知错误")

            # 步骤 4: 情绪分析
            logger.info("执行情绪分析...")
            sent_result = self._run_sentiment_analysis(code)
            result.sentiment_success = sent_result.get("success", False)
            if result.sentiment_success:
                result.sentiment_news = sent_result.get("analysis", [])
                result.sentiment_summary = sent_result.get("summary", {})
            else:
                result.errors["sentiment"] = sent_result.get("error", "未知错误")

            # 检查总体成功状态
            result.success = (
                result.technical_success or
                result.fundamental_success or
                result.sentiment_success
            )

            logger.info(f"分析完成：{code} ({name})")
            return result

        except Exception as e:
            logger.error(f"分析失败：{e}")
            result.success = False
            result.errors["general"] = str(e)
            return result

    def _prepare_data(
        self,
        code: str,
        download: bool,
        skip_days: int
    ) -> Optional[pd.DataFrame]:
        """
        准备数据

        Args:
            code: 股票代码
            download: 是否下载
            skip_days: 缓存宽容度

        Returns:
            DataFrame 或 None
        """
        # 检查缓存
        if not download or self.repository.is_data_fresh(code, skip_days):
            df = self.repository.load_stock_data(code)
            if df is not None:
                logger.info(f"使用缓存数据：{code}")
                return df

        # 下载数据
        if download:
            try:
                logger.info(f"下载新数据：{code}")
                df = self.downloader.download_stock_history(code)
                self.repository.save_stock_data(code, df)
                return df
            except Exception as e:
                logger.warning(f"下载失败：{e}，尝试使用缓存...")
                # 下载失败时尝试使用旧缓存
                return self.repository.load_stock_data(code)

        # 尝试直接加载缓存
        return self.repository.load_stock_data(code)

    def _run_technical_analysis(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        执行技术分析

        Args:
            df: 行情数据

        Returns:
            分析结果
        """
        try:
            return self.technical_analyzer.analyze(df)
        except Exception as e:
            logger.error(f"技术分析失败：{e}")
            return {"success": False, "error": str(e)}

    def _run_fundamental_analysis(
        self,
        code: str
    ) -> Dict[str, Any]:
        """
        执行基本面分析

        Args:
            code: 股票代码

        Returns:
            分析结果
        """
        try:
            # 获取基本面数据
            fundamentals = self.downloader.get_fundamentals(code)

            if fundamentals is None:
                return {"success": False, "error": "获取基本面数据失败"}

            return self.fundamental_analyzer.analyze(fundamentals)

        except Exception as e:
            logger.error(f"基本面分析失败：{e}")
            return {"success": False, "error": str(e)}

    def _run_sentiment_analysis(
        self,
        code: str
    ) -> Dict[str, Any]:
        """
        执行情绪分析

        Args:
            code: 股票代码

        Returns:
            分析结果
        """
        try:
            # 获取新闻（自动去重并补充到 5 条）
            news_list = self.downloader.get_news(code, limit=5, target_count=5)

            if not news_list:
                return {"success": False, "error": "获取新闻失败"}

            return self.sentiment_analyzer.analyze(news_list)

        except Exception as e:
            logger.error(f"情绪分析失败：{e}")
            return {"success": False, "error": str(e)}

    def analyze_technical(self, code: str) -> Dict[str, Any]:
        """
        仅执行技术分析

        Args:
            code: 股票代码

        Returns:
            技术分析结果
        """
        df = self.repository.load_stock_data(code)

        if df is None:
            return {"success": False, "error": "数据不存在"}

        return self._run_technical_analysis(df)

    def analyze_fundamental(self, code: str) -> Dict[str, Any]:
        """
        仅执行基本面分析

        Args:
            code: 股票代码

        Returns:
            基本面分析结果
        """
        return self._run_fundamental_analysis(code)

    def analyze_sentiment(self, code: str) -> Dict[str, Any]:
        """
        仅执行情绪分析

        Args:
            code: 股票代码

        Returns:
            情绪分析结果
        """
        return self._run_sentiment_analysis(code)
