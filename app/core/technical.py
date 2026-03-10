# -*- coding: utf-8 -*-
"""
技术分析模块
计算 MA、MACD、RSI 等技术指标，生成交易信号
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..exceptions import TechnicalAnalysisError
from ..utils.logger import get_logger

logger = get_logger("core.technical")


@dataclass
class TechnicalSignal:
    """技术信号数据类"""
    type: str  # 信号类型：均线/MACD/RSI/成交量
    signal: str  # 信号描述：🟢 多头排列/🔴 空头排列等
    description: str  # 详细说明


@dataclass
class TechnicalIndicators:
    """技术指标数据类"""
    close: float  # 收盘价
    ma5: float  # 5 日均线
    ma10: float  # 10 日均线
    ma20: float  # 20 日均线
    ma60: float  # 60 日均线
    dif: float  # DIF
    dea: float  # DEA
    macd: float  # MACD
    rsi: float  # RSI(14)
    date: str  # 数据日期
    volume: Optional[float] = None  # 成交量


class TechnicalAnalyzer:
    """技术分析器"""

    def __init__(self, ma_windows: Optional[List[int]] = None):
        """
        初始化技术分析器

        Args:
            ma_windows: 均线周期列表，默认 [5, 10, 20, 60]
        """
        if ma_windows is None:
            ma_windows = [5, 10, 20, 60]
        self.ma_windows = ma_windows

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行技术分析

        Args:
            df: 包含日线数据的 DataFrame，需要有'收盘'列

        Returns:
            包含 indicators 和 signals 的字典

        Raises:
            TechnicalAnalysisError: 分析失败时抛出
        """
        try:
            # 数据验证
            if df is None or len(df) < 60:
                raise TechnicalAnalysisError(
                    "数据量不足，至少需要 60 条记录",
                    {"actual_length": len(df) if df is not None else 0}
                )

            # 计算均线
            df = self._calculate_ma(df)

            # 计算 MACD
            df = self._calculate_macd(df)

            # 计算 RSI
            df = self._calculate_rsi(df)

            # 获取最新数据
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # 提取指标
            indicators = self._extract_indicators(latest)

            # 生成信号
            signals = self._generate_signals(df, latest, prev)

            # 将 dataclass 转换为字典
            indicators_dict = {
                'close': indicators.close,
                'ma5': indicators.ma5,
                'ma10': indicators.ma10,
                'ma20': indicators.ma20,
                'ma60': indicators.ma60,
                'dif': indicators.dif,
                'dea': indicators.dea,
                'macd': indicators.macd,
                'rsi': indicators.rsi,
                'date': indicators.date,
            }

            signals_list = [
                {
                    'type': s.type,
                    'signal': s.signal,
                    'desc': s.description
                }
                for s in signals
            ]

            return {
                "success": True,
                "indicators": indicators_dict,
                "signals": signals_list,
                "data": df
            }

        except Exception as e:
            logger.error(f"技术分析失败：{e}")
            if isinstance(e, TechnicalAnalysisError):
                raise
            raise TechnicalAnalysisError(f"技术分析失败：{str(e)}")

    def _calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线"""
        df = df.copy()

        for window in self.ma_windows:
            col_name = f"MA{window}"
            df[col_name] = df["收盘"].rolling(window=window).mean()

        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 MACD 指标"""
        df = df.copy()

        # 计算 EMA12 和 EMA26
        df["EMA12"] = df["收盘"].ewm(span=12, adjust=False).mean()
        df["EMA26"] = df["收盘"].ewm(span=26, adjust=False).mean()

        # 计算 DIF 和 DEA
        df["DIF"] = df["EMA12"] - df["EMA26"]
        df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()

        # 计算 MACD 柱
        df["MACD"] = 2 * (df["DIF"] - df["DEA"])

        return df

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算 RSI 指标"""
        df = df.copy()

        # 计算价格变化
        delta = df["收盘"].diff()

        # 分离涨跌
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()

        # 计算 RS 和 RSI
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        return df

    def _extract_indicators(self, latest: pd.Series) -> TechnicalIndicators:
        """提取技术指标"""
        return TechnicalIndicators(
            close=float(latest["收盘"]),
            ma5=float(latest.get("MA5", 0)),
            ma10=float(latest.get("MA10", 0)),
            ma20=float(latest.get("MA20", 0)),
            ma60=float(latest.get("MA60", 0)),
            dif=float(latest.get("DIF", 0)),
            dea=float(latest.get("DEA", 0)),
            macd=float(latest.get("MACD", 0)),
            rsi=float(latest.get("RSI", 0)),
            date=str(latest.get("日期", "")),
            volume=float(latest.get("成交量", 0)) if "成交量" in latest else None
        )

    def _generate_signals(
        self,
        df: pd.DataFrame,
        latest: pd.Series,
        prev: pd.Series
    ) -> List[TechnicalSignal]:
        """生成交易信号"""
        signals = []

        # 均线信号
        signals.extend(self._generate_ma_signals(latest))

        # 价格与均线关系
        signals.extend(self._generate_price_ma_signals(latest))

        # MACD 信号
        signals.extend(self._generate_macd_signals(latest, prev))

        # RSI 信号
        signals.extend(self._generate_rsi_signals(latest))

        # 成交量信号
        signals.extend(self._generate_volume_signals(df, latest))

        return signals

    def _generate_ma_signals(self, latest: pd.Series) -> List[TechnicalSignal]:
        """生成均线排列信号"""
        signals = []

        ma5 = latest.get("MA5", 0)
        ma10 = latest.get("MA10", 0)
        ma20 = latest.get("MA20", 0)

        # 多头排列：短期均线在长期均线上方
        if ma5 > ma10 > ma20 and ma20 > 0:
            signals.append(TechnicalSignal(
                type="均线",
                signal="🟢 多头排列",
                description="短期均线在长期均线上方"
            ))
        # 空头排列：短期均线在长期均线下方
        elif ma5 < ma10 < ma20 and ma20 > 0:
            signals.append(TechnicalSignal(
                type="均线",
                signal="🔴 空头排列",
                description="短期均线在长期均线下方"
            ))

        return signals

    def _generate_price_ma_signals(self, latest: pd.Series) -> List[TechnicalSignal]:
        """生成价格与均线关系信号"""
        signals = []

        close = latest.get("收盘", 0)
        ma20 = latest.get("MA20", 0)

        if ma20 > 0:
            if close > ma20:
                signals.append(TechnicalSignal(
                    type="趋势",
                    signal="🟢 在 20 日均线上",
                    description="股价位于 20 日均线上方"
                ))
            else:
                signals.append(TechnicalSignal(
                    type="趋势",
                    signal="🔴 在 20 日均线下方",
                    description="股价位于 20 日均线下方"
                ))

        return signals

    def _generate_macd_signals(
        self,
        latest: pd.Series,
        prev: pd.Series
    ) -> List[TechnicalSignal]:
        """生成 MACD 信号"""
        signals = []

        dif = latest.get("DIF", 0)
        dea = latest.get("DEA", 0)
        prev_dif = prev.get("DIF", 0)
        prev_dea = prev.get("DEA", 0)

        # 金叉：DIF 上穿 DEA
        if dif > dea and prev_dif <= prev_dea:
            signals.append(TechnicalSignal(
                type="MACD",
                signal="🟢 金叉",
                description="DIF 上穿 DEA"
            ))
        # 死叉：DIF 下穿 DEA
        elif dif < dea and prev_dif >= prev_dea:
            signals.append(TechnicalSignal(
                type="MACD",
                signal="🔴 死叉",
                description="DIF 下穿 DEA"
            ))

        return signals

    def _generate_rsi_signals(self, latest: pd.Series) -> List[TechnicalSignal]:
        """生成 RSI 信号"""
        signals = []

        rsi = latest.get("RSI", 0)

        if rsi > 70:
            signals.append(TechnicalSignal(
                type="RSI",
                signal="🔴 超买",
                description="RSI 高于 70，可能回调"
            ))
        elif rsi < 30:
            signals.append(TechnicalSignal(
                type="RSI",
                signal="🟢 超卖",
                description="RSI 低于 30，可能反弹"
            ))
        else:
            signals.append(TechnicalSignal(
                type="RSI",
                signal="⚪ 中性",
                description="RSI 在 30-70 区间"
            ))

        return signals

    def _generate_volume_signals(
        self,
        df: pd.DataFrame,
        latest: pd.Series
    ) -> List[TechnicalSignal]:
        """生成成交量信号"""
        signals = []

        if "成交量" not in latest:
            return signals

        current_volume = latest.get("成交量", 0)

        # 计算 20 日平均成交量
        avg_volume = df["成交量"].rolling(window=20).mean().iloc[-1]

        if avg_volume > 0:
            if current_volume > avg_volume * 1.5:
                signals.append(TechnicalSignal(
                    type="成交量",
                    signal="🟢 放量",
                    description="成交量大于 20 日均量 1.5 倍"
                ))
            elif current_volume < avg_volume * 0.5:
                signals.append(TechnicalSignal(
                    type="成交量",
                    signal="🔴 缩量",
                    description="成交量小于 20 日均量 0.5 倍"
                ))

        return signals


def calculate_moving_averages(
    df: pd.DataFrame,
    windows: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    计算移动平均线（便捷函数）

    Args:
        df: 包含日线数据的 DataFrame
        windows: 均线周期列表

    Returns:
        添加了均线列的 DataFrame
    """
    if windows is None:
        windows = [5, 10, 20]

    df = df.copy()

    for window in windows:
        col_name = f"MA{window}"
        df[col_name] = df["收盘"].rolling(window=window).mean()

    return df
