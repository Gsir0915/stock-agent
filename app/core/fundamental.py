# -*- coding: utf-8 -*-
"""
基本面分析模块
计算 PE、PB、净利润增长率等指标，生成价值评分
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..exceptions import FundamentalAnalysisError
from ..utils.logger import get_logger

logger = get_logger("core.fundamental")


@dataclass
class FundamentalIndicators:
    """基本面指标数据类"""
    pe: Optional[float]  # 市盈率
    pb: Optional[float]  # 市净率
    profit_growth: Optional[float]  # 净利润增长率（百分比）
    pe_estimated: bool = False  # PE 是否为估算值


@dataclass
class ValueScore:
    """价值评分数据类"""
    score: int  # 总分 0-100
    rating: str  # 评级
    details: List[str]  # 详细评分说明
    pe_score: int = 0  # PE 分项得分
    pb_score: int = 0  # PB 分项得分
    growth_score: int = 0  # 增长率分项得分


class FundamentalAnalyzer:
    """基本面分析器"""

    def __init__(self):
        """初始化基本面分析器"""
        pass

    def analyze(self, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行基本面分析

        Args:
            fundamentals: 基本面数据字典，包含 pe、pb、profit_growth 等

        Returns:
            包含 indicators、score、rating 的字典

        Raises:
            FundamentalAnalysisError: 分析失败时抛出
        """
        try:
            # 提取指标
            pe = fundamentals.get("pe")
            pb = fundamentals.get("pb")
            profit_growth = fundamentals.get("profit_growth")
            pe_estimated = fundamentals.get("pe_estimated", False)

            # 计算价值评分
            value_score = self.calculate_value_score(
                pe, pb, profit_growth, pe_estimated
            )

            return {
                "success": True,
                "indicators": {
                    "pe": pe,
                    "pb": pb,
                    "profit_growth": profit_growth
                },
                "score": value_score.score,
                "rating": value_score.rating,
                "details": value_score.details,
                "score_breakdown": {
                    "pe_score": value_score.pe_score,
                    "pb_score": value_score.pb_score,
                    "growth_score": value_score.growth_score
                }
            }

        except Exception as e:
            logger.error(f"基本面分析失败：{e}")
            if isinstance(e, FundamentalAnalysisError):
                raise
            raise FundamentalAnalysisError(f"基本面分析失败：{str(e)}")

    def calculate_value_score(
        self,
        pe: Optional[float],
        pb: Optional[float],
        profit_growth: Optional[float],
        pe_estimated: bool = False
    ) -> ValueScore:
        """
        计算价值评估分数（0-100 分）

        评分标准：
        - PE 分数（40 分）：PE<10 得 40 分，10-20 得 30 分，20-30 得 20 分，30-50 得 10 分，>50 得 0 分
        - PB 分数（30 分）：PB<1 得 30 分，1-2 得 25 分，2-3 得 20 分，3-5 得 10 分，>5 得 0 分
        - 净利润增长率分数（30 分）：>30% 得 30 分，20-30% 得 25 分，10-20% 得 20 分，0-10% 得 15 分，负增长得 5 分

        Args:
            pe: 市盈率
            pb: 市净率
            profit_growth: 净利润增长率（百分比）
            pe_estimated: PE 是否为估算值

        Returns:
            ValueScore 数据类实例
        """
        details = []

        # PE 评分（40 分）
        pe_score = 0
        if pe is not None and pe > 0:
            if pe < 10:
                pe_score = 40
                pe_level = "很低"
            elif pe < 20:
                pe_score = 30
                pe_level = "较低"
            elif pe < 30:
                pe_score = 20
                pe_level = "中等"
            elif pe < 50:
                pe_score = 10
                pe_level = "较高"
            else:
                pe_score = 0
                pe_level = "很高"

            note = " (估算)" if pe_estimated else ""
            details.append(f"PE={pe:.2f}{note}({pe_level}, {pe_score}/40 分)")
        else:
            details.append("PE 无数据 (0/40 分)")

        # PB 评分（30 分）
        pb_score = 0
        if pb is not None and pb > 0:
            if pb < 1:
                pb_score = 30
                pb_level = "很低"
            elif pb < 2:
                pb_score = 25
                pb_level = "较低"
            elif pb < 3:
                pb_score = 20
                pb_level = "中等"
            elif pb < 5:
                pb_score = 10
                pb_level = "较高"
            else:
                pb_score = 0
                pb_level = "很高"

            details.append(f"PB={pb:.2f}({pb_level}, {pb_score}/30 分)")
        else:
            details.append("PB 无数据 (0/30 分)")

        # 净利润增长率评分（30 分）
        growth_score = 0
        if profit_growth is not None:
            if profit_growth > 30:
                growth_score = 30
                growth_level = "优秀"
            elif profit_growth > 20:
                growth_score = 25
                growth_level = "良好"
            elif profit_growth > 10:
                growth_score = 20
                growth_level = "中等"
            elif profit_growth > 0:
                growth_score = 15
                growth_level = "较慢"
            else:
                growth_score = 5
                growth_level = "负增长"

            details.append(
                f"净利润增长率={profit_growth:.2f}%({growth_level}, {growth_score}/30 分)"
            )
        else:
            details.append("净利润增长率无数据 (0/30 分)")

        # 计算总分
        score = pe_score + pb_score + growth_score

        # 评级
        rating = self._get_rating(score)

        return ValueScore(
            score=score,
            rating=rating,
            details=details,
            pe_score=pe_score,
            pb_score=pb_score,
            growth_score=growth_score
        )

    def _get_rating(self, score: int) -> str:
        """
        根据分数获取评级

        Args:
            score: 分数

        Returns:
            评级字符串
        """
        if score >= 80:
            return "★★★★★ 极具投资价值"
        elif score >= 60:
            return "★★★★ 具有投资价值"
        elif score >= 40:
            return "★★★ 中等"
        elif score >= 20:
            return "★★ 偏高"
        else:
            return "★ 估值过高"


def get_fundamental_indicators(code: str) -> Optional[Dict[str, Any]]:
    """
    获取股票基本面指标（便捷函数）

    Args:
        code: 股票代码

    Returns:
        基本面指标字典
    """
    from ..data.downloader import DataDownloader

    downloader = DataDownloader()
    return downloader.get_fundamentals(code)
