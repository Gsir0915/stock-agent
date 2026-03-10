# -*- coding: utf-8 -*-
"""
海龟交易法则选股器
基于原版海龟交易规则，结合 A 股市场特点进行优化

核心规则：
1. 股价创 20 日新高（突破信号）
2. ATR 处于低位震荡后开始向上（波动率扩张）
3. 基于 2% 风险敞口计算初始建仓头寸
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from ..exceptions import TechnicalAnalysisError
from ..utils.logger import get_logger

logger = get_logger("core.turtle")


@dataclass
class TurtleSignal:
    """海龟交易信号"""
    code: str  # 股票代码
    name: str  # 股票名称
    success: bool = True  # 是否成功

    # 突破信号
    breakout: bool = False  # 是否创 20 日新高
    current_price: float = 0.0  # 当前价格
    twenty_day_high: float = 0.0  # 20 日最高价
    days_since_high: int = 0  # 距离新高天数

    # ATR 信号
    atr_current: float = 0.0  # 当前 ATR
    atr_prev_5: float = 0.0  # 前 5 日平均 ATR
    atr_prev_10: float = 0.0  # 前 10 日平均 ATR
    atr_trend: str = ""  # ATR 趋势：rising/falling/stable

    # ATR 低位震荡判断
    atr_consolidation: bool = False  # 是否处于低位震荡
    consolidation_details: str = ""  # 详细说明

    # 头寸计算
    position_size: int = 0  # 建议建仓股数
    position_value: float = 0.0  # 建仓金额
    risk_amount: float = 0.0  # 风险金额 (2%)
    stop_loss_price: float = 0.0  # 止损价格
    unit_risk: float = 0.0  # 每单位风险 (1N)

    # 加仓窗口
    add_unit_window: float = 0.0  # 加仓窗口 (0.5N)
    add_unit_prices: List[float] = field(default_factory=list)  # 加仓价格点位
    max_units: int = 4  # 最大单位数
    current_unit: int = 1  # 当前应持有单位数

    # 移动止损/止盈
    trailing_stop_n: int = 2  # 移动止损 N 值 (默认 2N)
    current_trailing_stop: float = 0.0  # 当前移动止损价
    highest_since_entry: float = 0.0  # 建仓后最高价

    # 退出信号
    exit_signal: str = ""  # 退出信号描述
    exit_price: float = 0.0  # 建议退出价格

    # 错误信息
    error: str = ""


@dataclass
class TurtleConfig:
    """海龟交易配置"""
    # 突破周期
    breakout_window: int = 20  # 20 日新高

    # ATR 周期
    atr_period: int = 14  # ATR 计算周期
    atr_consolidation_window: int = 10  # ATR 震荡判断周期

    # ATR 低位判断阈值
    atr_consolidation_threshold: float = 0.05  # ATR 震荡幅度阈值 (5%)

    # ATR 向上判断
    atr_rising_threshold: float = 0.1  # ATR 上升阈值 (10%)

    # 风险管理
    risk_per_trade: float = 0.02  # 每笔交易风险 (2%)
    stop_loss_multiple: float = 2.0  # 止损倍数 (2N)

    # 最小资本要求
    min_capital: float = 100000  # 最小资金量 (10 万)

    # 数据要求
    min_history_days: int = 60  # 最少历史数据天数


class TurtleScreener:
    """海龟交易法则选股器"""

    def __init__(self, config: Optional[TurtleConfig] = None):
        """
        初始化选股器

        Args:
            config: 配置参数
        """
        self.config = config or TurtleConfig()

    def check_stock(
        self,
        code: str,
        name: str,
        df: pd.DataFrame,
        capital: float = 100000
    ) -> TurtleSignal:
        """
        检查单只股票是否符合海龟交易买入条件

        Args:
            code: 股票代码
            name: 股票名称
            df: 包含日线数据的 DataFrame
            capital: 可用资金

        Returns:
            TurtleSignal 交易信号
        """
        signal = TurtleSignal(code=code, name=name)

        try:
            # 数据验证
            if df is None or len(df) < self.config.min_history_days:
                signal.success = False
                signal.error = f"数据量不足，至少需要 {self.config.min_history_days} 条记录"
                return signal

            # 计算 ATR
            df = self._calculate_atr(df)

            # 检查突破信号 (20 日新高)
            breakout_result = self._check_breakout(df, self.config.breakout_window)
            signal.breakout = breakout_result["breakout"]
            signal.current_price = float(df.iloc[-1]["收盘"])
            signal.twenty_day_high = breakout_result["high"]
            signal.days_since_high = breakout_result["days_since_high"]

            # 检查 ATR 信号
            atr_result = self._check_atr_signal(df)
            signal.atr_current = atr_result["atr_current"]
            signal.atr_prev_5 = atr_result["atr_prev_5"]
            signal.atr_prev_10 = atr_result["atr_prev_10"]
            signal.atr_trend = atr_result["trend"]
            signal.atr_consolidation = atr_result["consolidation"]
            signal.consolidation_details = atr_result["consolidation_details"]

            # 计算头寸
            if signal.breakout and signal.atr_consolidation and atr_result["trend"] == "rising":
                position_result = self._calculate_position(
                    price=signal.current_price,
                    atr=signal.atr_current,
                    capital=capital
                )
                signal.position_size = position_result["shares"]
                signal.position_value = position_result["value"]
                signal.risk_amount = position_result["risk_amount"]
                signal.stop_loss_price = position_result["stop_loss"]
                signal.unit_risk = position_result["unit_risk"]

                # 计算加仓窗口
                add_result = self._calculate_add_unit_prices(
                    price=signal.current_price,
                    atr=signal.atr_current,
                    base_shares=signal.position_size
                )
                signal.add_unit_window = add_result["window"]
                signal.add_unit_prices = add_result["prices"]

                # 计算移动止损/止盈
                trail_result = self._calculate_trailing_stop(
                    entry_price=signal.current_price,
                    atr=signal.atr_current,
                    current_price=signal.current_price
                )
                signal.trailing_stop_n = trail_result["stop_n"]
                signal.current_trailing_stop = trail_result["stop_price"]
                signal.highest_since_entry = trail_result["highest"]
                signal.exit_signal = trail_result["signal"]

            return signal

        except Exception as e:
            logger.error(f"海龟选股分析失败：{e}")
            signal.success = False
            signal.error = str(e)
            return signal

    def _calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 ATR (Average True Range)

        Args:
            df: 包含日线数据的 DataFrame

        Returns:
            添加了 ATR 列的 DataFrame
        """
        df = df.copy()

        # 确保有必需列
        required_cols = ["最高", "最低", "收盘"]
        for col in required_cols:
            if col not in df.columns:
                raise TechnicalAnalysisError(f"缺少必需列：{col}")

        # 计算真实波幅 (True Range)
        high = df["最高"]
        low = df["最低"]
        prev_close = df["收盘"].shift(1)

        # TR = max(high-low, |high-prev_close|, |low-prev_close|)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算 ATR (使用 Wilder 平滑方法)
        period = self.config.atr_period

        # 初始 ATR 使用简单平均
        df["ATR"] = df["TR"].rolling(window=period).mean()

        # Wilder 平滑：ATR = (前一日 ATR * (n-1) + 当日 TR) / n
        # 从第 period+1 个数据开始应用
        for i in range(period, len(df)):
            if pd.notna(df["ATR"].iloc[i-1]):
                df.iloc[i, df.columns.get_loc("ATR")] = (
                    df["ATR"].iloc[i-1] * (period - 1) + df["TR"].iloc[i]
                ) / period

        return df

    def _check_breakout(
        self,
        df: pd.DataFrame,
        window: int
    ) -> Dict[str, Any]:
        """
        检查是否创 N 日新高

        Args:
            df: 日线数据
            window: 突破周期

        Returns:
            突破检查结果
        """
        current_price = float(df.iloc[-1]["收盘"])

        # 计算 N 日最高价 (不包含当日)
        recent_data = df.iloc[-window:-1] if len(df) > window else df.iloc[:-1]
        n_day_high = float(recent_data["最高"].max())

        # 判断是否突破
        breakout = current_price > n_day_high

        # 计算距离新高的天数
        if breakout:
            days_since_high = 0
        else:
            # 找到最近一次新高的位置
            high_series = df["最高"].iloc[-window:]
            max_price = high_series.max()
            max_idx = high_series.idxmax()
            days_since_high = len(high_series) - high_series.index.get_loc(max_idx) - 1

        return {
            "breakout": breakout,
            "high": n_day_high,
            "days_since_high": days_since_high
        }

    def _check_atr_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        检查 ATR 信号：低位震荡后向上

        Args:
            df: 包含 ATR 数据的 DataFrame

        Returns:
            ATR 信号检查结果
        """
        if "ATR" not in df.columns:
            df = self._calculate_atr(df)

        atr_series = df["ATR"].dropna()

        if len(atr_series) < self.config.atr_consolidation_window + 5:
            return {
                "atr_current": 0.0,
                "atr_prev_5": 0.0,
                "atr_prev_10": 0.0,
                "trend": "unknown",
                "consolidation": False,
                "consolidation_details": "数据不足"
            }

        # 当前 ATR
        atr_current = float(atr_series.iloc[-1])

        # 前 5 日平均 ATR
        atr_prev_5 = float(atr_series.iloc[-6:-1].mean()) if len(atr_series) >= 6 else atr_current

        # 前 10 日平均 ATR
        atr_prev_10 = float(atr_series.iloc[-11:-1].mean()) if len(atr_series) >= 11 else atr_prev_5

        # 判断 ATR 趋势
        atr_change_5 = (atr_current - atr_prev_5) / atr_prev_5 if atr_prev_5 > 0 else 0
        atr_trend = "stable"

        if atr_change_5 > self.config.atr_rising_threshold:
            atr_trend = "rising"
        elif atr_change_5 < -self.config.atr_rising_threshold:
            atr_trend = "falling"

        # 判断 ATR 是否处于低位震荡
        consolidation_window = self.config.atr_consolidation_window
        recent_atr = atr_series.iloc[-consolidation_window:-1]

        # 计算震荡指标
        atr_mean = recent_atr.mean()
        atr_std = recent_atr.std()
        atr_cv = atr_std / atr_mean if atr_mean > 0 else 0  # 变异系数

        # 判断是否低位：当前 ATR 低于前 N 日均值，且震荡幅度小
        is_low = atr_current < atr_mean * 1.0  # 接近或低于均值
        is_consolidating = atr_cv < self.config.atr_consolidation_threshold

        # 低位震荡判断：变异系数小表示震荡
        consolidation = is_consolidating

        # 构建详细说明
        details_parts = [
            f"ATR 变异系数：{atr_cv:.2%}",
            f"震荡阈值：{self.config.atr_consolidation_threshold:.0%}"
        ]

        if consolidation:
            details_parts.append(f"ATR 处于{consolidation_window}日低位震荡")
            if atr_trend == "rising":
                details_parts.append("且开始向上")
        else:
            details_parts.append("ATR 未处于明显震荡状态")

        return {
            "atr_current": atr_current,
            "atr_prev_5": atr_prev_5,
            "atr_prev_10": atr_prev_10,
            "trend": atr_trend,
            "consolidation": consolidation,
            "consolidation_details": " | ".join(details_parts)
        }

    def _calculate_position(
        self,
        price: float,
        atr: float,
        capital: float
    ) -> Dict[str, Any]:
        """
        计算基于 2% 风险敞口的建仓头寸

        海龟交易法则头寸计算公式：
        - 1N = ATR (当前波动率)
        - 止损距离 = 2N = 2 * ATR
        - 风险金额 = 总资金 * 2%
        - 股数 = 风险金额 / 止损距离

        Args:
            price: 当前股价
            atr: ATR 值
            capital: 可用资金

        Returns:
            头寸计算结果
        """
        # 风险金额 (2% 总资金)
        risk_amount = capital * self.config.risk_per_trade

        # 单位风险 (1N = ATR)
        unit_risk = atr

        # 止损距离 (2N)
        stop_distance = atr * self.config.stop_loss_multiple

        # 止损价格
        stop_loss_price = price - stop_distance

        # 计算股数：风险金额 / 每股风险
        if stop_distance > 0:
            shares = int(risk_amount / stop_distance)
            # A 股最小交易单位 100 股
            shares = (shares // 100) * 100
            shares = max(0, shares)
        else:
            shares = 0

        # 建仓金额
        position_value = shares * price

        # 验证：实际风险不超过 2%
        actual_risk = shares * stop_distance
        risk_ratio = actual_risk / capital if capital > 0 else 0

        return {
            "shares": shares,
            "value": position_value,
            "risk_amount": risk_amount,
            "stop_loss": stop_loss_price,
            "unit_risk": unit_risk,
            "actual_risk": actual_risk,
            "risk_ratio": risk_ratio
        }

    def _calculate_add_unit_prices(
        self,
        price: float,
        atr: float,
        base_shares: int
    ) -> Dict[str, Any]:
        """
        计算加仓窗口和加仓价格点位

        海龟交易法则加仓规则：
        - 加仓窗口：0.5N (0.5 × ATR)
        - 加仓次数：最多 3 次（总仓位 4 个单位）
        - 每次加仓数量：与初始仓位相同
        - 统一止损：2N

        Args:
            price: 当前股价
            atr: ATR 值
            base_shares: 初始建仓股数

        Returns:
            加仓计算结果
        """
        # 加仓窗口 = 0.5N
        add_unit_window = atr * 0.5

        # 计算 3 个加仓价格点位
        add_prices = []
        for i in range(1, 4):  # 加仓 3 次
            add_price = price + (add_unit_window * i)
            add_prices.append(round(add_price, 2))

        return {
            "window": round(add_unit_window, 2),
            "prices": add_prices,
            "base_shares": base_shares,
            "max_units": 4,
            "stop_loss": round(price - atr * 2, 2)
        }

    def _calculate_trailing_stop(
        self,
        entry_price: float,
        atr: float,
        current_price: float
    ) -> Dict[str, Any]:
        """
        计算移动止损/止盈价格

        海龟交易法则移动止损规则：
        - 初始止损：2N (从入场价计算)
        - 移动止损：当股价创新高后，止损价 = 最高价 - 2N
        - 止损价只上移，不下移
        - 跌破移动止损价时，全部仓位退出

        止盈退出信号：
        - 股价跌破 10 日均线（趋势转弱）
        - 股价从最高点回落 2N

        Args:
            entry_price: 入场价格
            atr: ATR 值
            current_price: 当前价格

        Returns:
            移动止损计算结果
        """
        stop_n = 2  # 2N 止损
        stop_distance = atr * stop_n

        # 初始止损价
        initial_stop = entry_price - stop_distance

        # 当前价格即建仓后最高价（假设刚建仓）
        highest = current_price

        # 移动止损价 = 最高价 - 2N
        trailing_stop = highest - stop_distance

        # 确保移动止损不低于初始止损
        trailing_stop = max(trailing_stop, initial_stop)

        # 判断退出信号
        if current_price > entry_price * 1.2:
            signal = "🟢 盈利 > 20%, 可用移动止损保护利润"
        elif current_price > entry_price * 1.1:
            signal = "🟡 盈利 > 10%, 关注移动止损"
        else:
            signal = "⚪ 持有中，止损跟随上移"

        return {
            "stop_n": stop_n,
            "stop_price": round(trailing_stop, 2),
            "initial_stop": round(initial_stop, 2),
            "highest": round(highest, 2),
            "signal": signal,
            "atr": round(atr, 2)
        }

    def scan_stocks(
        self,
        stock_list: List[Dict[str, Any]],
        get_data_func=None,
        capital: float = 100000
    ) -> List[TurtleSignal]:
        """
        批量扫描股票

        Args:
            stock_list: 股票列表 [{"code": "600519", "name": "贵州茅台"}, ...]
            get_data_func: 获取数据的函数
            capital: 每只股票可用资金

        Returns:
            符合条件的股票信号列表
        """
        results = []

        for stock in stock_list:
            code = stock["code"]
            name = stock.get("name", "")

            try:
                # 获取数据
                df = get_data_func(code) if get_data_func else None

                if df is None:
                    logger.warning(f"无法获取股票数据：{code}")
                    continue

                # 检查是否符合条件
                signal = self.check_stock(code, name, df, capital)

                if signal.success and signal.breakout and signal.atr_consolidation:
                    results.append(signal)
                    logger.info(f"✓ {code} ({name}) 符合海龟买入条件")

            except Exception as e:
                logger.error(f"扫描股票 {code} 失败：{e}")
                continue

        return results


def get_turtle_screener(config: Optional[TurtleConfig] = None) -> TurtleScreener:
    """
    获取海龟选股器单例

    Args:
        config: 配置参数

    Returns:
        TurtleScreener 实例
    """
    return TurtleScreener(config)
