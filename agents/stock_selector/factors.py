"""
因子库模块

定义各种选股因子，包括技术面、基本面、情绪面等。
"""

from typing import Tuple, List, Optional, Dict, Any
from abc import ABC, abstractmethod
import sys
from pathlib import Path

# 添加项目根目录到路径，以便导入现有模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================
# 因子基类
# ============================================

class BaseFactor(ABC):
    """因子基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """因子名称"""
        pass

    @abstractmethod
    def run(self, data: Dict[str, Any]) -> float:
        """
        运行因子计算，返回标准化得分

        Args:
            data: 包含财务数据、行情数据等的字典

        Returns:
            标准化得分 (0.0 - 1.0)
        """
        pass


# ============================================
# 质量因子
# ============================================

class QualityFactor(BaseFactor):
    """
    质量因子 - 基于自由现金流 (FCF) 和净利润

    评分逻辑:
    - FCF/净利润 比率越高，盈利质量越好
    - 净利润同比增长率为正，额外加分
    """

    @property
    def name(self) -> str:
        return "QualityFactor"

    def run(self, data: Dict[str, Any]) -> float:
        """
        计算质量因子得分

        Args:
            data: 包含以下键的字典:
                - fcf: 自由现金流
                - net_profit: 净利润
                - net_profit_growth: 净利润同比增长率 (%)

        Returns:
            标准化得分 (0.0 - 1.0)
        """
        fcf = data.get("fcf", 0)
        net_profit = data.get("net_profit", 0)
        net_profit_growth = data.get("net_profit_growth", 0)

        # 检查 FCF 数据是否可用（如果 fcf 和 net_profit 都是默认值 1，说明数据缺失）
        fcf_available = fcf != net_profit or fcf != 1

        if not fcf_available:
            # FCF 数据缺失，仅使用增长率评分
            if net_profit_growth >= 20:
                return 1.0
            elif net_profit_growth <= -10:
                return 0.0
            else:
                return (net_profit_growth + 10) / 30

        # 处理除零情况
        if net_profit == 0:
            return 0.0

        # FCF/净利润 比率
        fcf_to_profit_ratio = fcf / net_profit

        # 比率评分：比率越高，分数越高
        # 理想情况下 FCF 应接近或大于净利润
        # 比率 > 1.0 得满分，比率 < 0 得 0 分
        if fcf_to_profit_ratio >= 1.0:
            ratio_score = 1.0
        elif fcf_to_profit_ratio <= 0:
            ratio_score = 0.0
        else:
            ratio_score = fcf_to_profit_ratio

        # 增长评分：增长率越高，分数越高
        # 增长率 >= 20% 得满分，<= -10% 得 0 分
        if net_profit_growth >= 20:
            growth_score = 1.0
        elif net_profit_growth <= -10:
            growth_score = 0.0
        else:
            # 线性映射到 [0, 1]
            growth_score = (net_profit_growth + 10) / 30

        # 综合得分：FCF 质量占 60%，增长占 40%
        final_score = 0.6 * ratio_score + 0.4 * growth_score

        # 确保在 [0, 1] 范围内
        return max(0.0, min(1.0, final_score))


# ============================================
# 动量因子
# ============================================

class MomentumFactor(BaseFactor):
    """
    动量因子 - 基于量价突破

    评分逻辑:
    - 价格相对 N 日高点的突破程度
    - 成交量相对均量的放大程度
    - 两者结合判断动量强度
    """

    @property
    def name(self) -> str:
        return "MomentumFactor"

    def run(self, data: Dict[str, Any]) -> float:
        """
        计算动量因子得分

        Args:
            data: 包含以下键的字典:
                - current_price: 当前价格
                - high_20: 20 日最高价
                - low_20: 20 日最低价
                - current_volume: 当前成交量
                - avg_volume_20: 20 日平均成交量

        Returns:
            标准化得分 (0.0 - 1.0)
        """
        current_price = data.get("current_price", 0)
        high_20 = data.get("high_20", current_price)
        low_20 = data.get("low_20", current_price)
        current_volume = data.get("current_volume", 0)
        avg_volume_20 = data.get("avg_volume_20", current_volume)

        # 价格位置得分：计算当前价格在 20 日区间的位置
        # 接近 20 日高点表示强势
        if high_20 == low_20:
            price_position_score = 0.5
        else:
            price_position = (current_price - low_20) / (high_20 - low_20)
            # 突破 20 日高点额外加分
            if current_price >= high_20:
                price_position_score = 1.0
            else:
                price_position_score = price_position

        # 成交量得分：放量表示动量确认
        if avg_volume_20 == 0:
            volume_score = 0.0
        else:
            volume_ratio = current_volume / avg_volume_20
            # 放量 2 倍以上得满分，0.5 倍以下得 0 分
            if volume_ratio >= 2.0:
                volume_score = 1.0
            elif volume_ratio <= 0.5:
                volume_score = 0.0
            else:
                volume_score = (volume_ratio - 0.5) / 1.5

        # 综合得分：价格动量占 70%，成交量确认占 30%
        final_score = 0.7 * price_position_score + 0.3 * volume_score

        # 确保在 [0, 1] 范围内
        return max(0.0, min(1.0, final_score))


# ============================================
# 股息因子
# ============================================

class DividendFactor(BaseFactor):
    """
    股息因子 - 基于高股息率

    评分逻辑:
    - 股息率越高，得分越高
    - 股息率稳定性（连续分红年数）作为加分项
    """

    @property
    def name(self) -> str:
        return "DividendFactor"

    def run(self, data: Dict[str, Any]) -> float:
        """
        计算股息因子得分

        Args:
            data: 包含以下键的字典:
                - dividend_yield: 股息率 (%)
                - consecutive_years: 连续分红年数
                - payout_ratio: 分红率 (%)

        Returns:
            标准化得分 (0.0 - 1.0)
        """
        dividend_yield = data.get("dividend_yield", 0)
        consecutive_years = data.get("consecutive_years", 0)
        payout_ratio = data.get("payout_ratio", 0)

        # 股息率得分：股息率越高，分数越高
        # 股息率 >= 5% 得满分，<= 1% 得 0 分
        if dividend_yield >= 5:
            yield_score = 1.0
        elif dividend_yield <= 1:
            yield_score = 0.0
        else:
            yield_score = (dividend_yield - 1) / 4

        # 稳定性得分：连续分红年数越多越稳定
        # >= 10 年得满分，0 年得 0 分
        if consecutive_years >= 10:
            stability_score = 1.0
        else:
            stability_score = min(1.0, consecutive_years / 10)

        # 分红率健康度：过高分红率可能不可持续
        # 30%-60% 为健康区间
        if 30 <= payout_ratio <= 60:
            payout_score = 1.0
        elif payout_ratio < 30:
            payout_score = payout_ratio / 30 if payout_ratio > 0 else 0.5
        else:
            # 过高的分红率扣分
            payout_score = max(0.3, 1.0 - (payout_ratio - 60) / 40)

        # 综合得分：股息率 50%，稳定性 30%，健康度 20%
        final_score = 0.5 * yield_score + 0.3 * stability_score + 0.2 * payout_score

        # 确保在 [0, 1] 范围内
        return max(0.0, min(1.0, final_score))


# ============================================
# 因子库
# ============================================

class FactorLibrary:
    """因子库"""

    def __init__(self):
        pass

    def get_all_factors(self) -> List[str]:
        """获取所有因子名称"""
        return [
            "factor_ma_trend",
            "factor_volume",
            "factor_rsi",
            "factor_macd",
        ]

    def factor_ma_trend(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """
        均线趋势因子

        Args:
            stock_code: 股票代码

        Returns:
            (分数，是否通过，详情)
        """
        # TODO: 实现均线趋势分析
        # - 获取历史数据
        # - 计算 MA5/MA10/MA20
        # - 判断多头排列
        return (0.0, False, {"status": "not_implemented"})

    def factor_volume(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """
        成交量因子

        Args:
            stock_code: 股票代码

        Returns:
            (分数，是否通过，详情)
        """
        # TODO: 实现成交量分析
        # - 计算成交量均线
        # - 判断放量/缩量
        return (0.0, False, {"status": "not_implemented"})

    def factor_rsi(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """
        RSI 超买超卖因子

        Args:
            stock_code: 股票代码

        Returns:
            (分数，是否通过，详情)
        """
        # TODO: 实现 RSI 分析
        # - 计算 RSI 指标
        # - 判断是否超卖（买入机会）
        return (0.0, False, {"status": "not_implemented"})

    def factor_macd(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """
        MACD 因子

        Args:
            stock_code: 股票代码

        Returns:
            (分数，是否通过，详情)
        """
        # TODO: 实现 MACD 分析
        # - 计算 MACD 指标
        # - 判断金叉/死叉
        return (0.0, False, {"status": "not_implemented"})

    # ============================================
    # 以下是待扩展的因子示例
    # ============================================

    def factor_fundamental_pe(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """基本面 - PE 估值因子"""
        return (0.0, False, {"status": "not_implemented"})

    def factor_fundamental_roe(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """基本面 - ROE 因子"""
        return (0.0, False, {"status": "not_implemented"})

    def factor_sentiment_news(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """情绪面 - 新闻因子"""
        return (0.0, False, {"status": "not_implemented"})

    def factor_money_flow(
        self, stock_code: str
    ) -> Tuple[float, bool, dict]:
        """资金流向因子"""
        return (0.0, False, {"status": "not_implemented"})
