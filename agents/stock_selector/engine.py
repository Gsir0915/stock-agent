"""
选股引擎核心模块

负责协调各因子库，执行股票筛选逻辑。
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import akshare as ak
import pandas as pd

from .factors import FactorLibrary


@dataclass
class ScreeningResult:
    """筛选结果"""

    stock_code: str
    stock_name: str
    score: float
    factors_passed: List[str]
    details: Dict


@dataclass
class MarketRegime:
    """市场环境状态"""

    volume_level: str           # 成交量水平：extremely_low/low/normal/high/extremely_high
    trend_type: str             # 趋势类型：bull/bear/range
    regime_name: str            # 模式名称：缩量防御/放量进攻等
    total_turnover: float       # 两市总成交额（亿元）
    sh_index_close: float       # 上证指数收盘价
    sh_ma120: float             # 上证指数 120 日均线


class StockSelectorEngine:
    """股票筛选引擎"""

    # 趋势类型常量
    TREND_BULL = "bull"
    TREND_BEAR = "bear"
    TREND_RANGE = "range"

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化选股引擎

        Args:
            config_path: 配置文件路径，None 则使用默认路径
        """
        self.factor_library = FactorLibrary()
        self._results: List[ScreeningResult] = []
        self._config = None
        self._config_path = config_path
        self._current_regime: Optional[MarketRegime] = None

    def _load_config(self):
        """加载配置文件"""
        if self._config is None:
            from app.utils.config_handler import get_config
            self._config = get_config()

    def get_market_turnover(self, date: Optional[str] = None) -> float:
        """
        获取两市总成交额

        Args:
            date: 日期字符串 (YYYYMMDD)，None 表示最新交易日

        Returns:
            两市总成交额（亿元）
        """
        try:
            # 获取 A 股实时行情
            df = ak.stock_zh_a_spot_em()

            if df is None or len(df) == 0:
                return 0.0

            # 获取成交额列（单位：元）
            # 东方财富接口返回的成交额列名为 "成交额"
            if "成交额" in df.columns:
                total_turnover = df["成交额"].sum()
            elif "turnover" in df.columns:
                total_turnover = df["turnover"].sum()
            else:
                # 尝试其他可能的列名
                for col in df.columns:
                    if "成交" in col or "turnover" in col.lower():
                        total_turnover = df[col].sum()
                        break
                else:
                    return 0.0

            # 转换为亿元（原始数据单位是元）
            total_turnover_yi = total_turnover / 1_0000_0000

            return round(total_turnover_yi, 2)

        except Exception as e:
            print(f"[WARN] 获取两市成交额失败：{e}")
            return 0.0

    def get_sh_index_data(self) -> Tuple[float, float, pd.DataFrame]:
        """
        获取上证指数数据

        Returns:
            (收盘价，120 日均线，历史数据 DataFrame)
        """
        try:
            # 获取上证指数历史数据
            df = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="qfq")

            if df is None or len(df) < 120:
                return 0.0, 0.0, pd.DataFrame()

            # 计算 120 日均线
            df["MA120"] = df["收盘"].rolling(window=120).mean()

            latest = df.iloc[-1]
            close = float(latest["收盘"])
            ma120 = float(latest["MA120"])

            return close, ma120, df

        except Exception as e:
            print(f"[WARN] 获取上证指数数据失败：{e}")
            return 0.0, 0.0, pd.DataFrame()

    def determine_market_regime(self) -> MarketRegime:
        """
        判断当前市场环境

        根据两市总成交额和上证指数趋势，判断当前市场所处的环境

        Returns:
            MarketRegime 市场环境状态

        Raises:
            RuntimeError: 配置未加载或配置中缺少必要参数
        """
        self._load_config()

        # 获取市场数据
        total_turnover = self.get_market_turnover()
        sh_close, sh_ma120, _ = self.get_sh_index_data()

        # 从配置中读取阈值（严禁写死）
        volume_thresholds = self._config.market_regime.volume_thresholds.to_dict()
        trend_thresholds = self._config.market_regime.trend_thresholds.to_dict()
        regime_mapping = self._config.market_regime.regime_mapping.to_dict()

        # 判断成交量水平
        if total_turnover < volume_thresholds["extremely_low"]:
            volume_level = "extremely_low"
        elif total_turnover < volume_thresholds["low"]:
            volume_level = "low"
        elif total_turnover < volume_thresholds["normal"]:
            volume_level = "normal"
        elif total_turnover < volume_thresholds["high"]:
            volume_level = "high"
        else:
            volume_level = "extremely_high"

        # 判断趋势类型
        if sh_ma120 > 0:
            price_ratio = sh_close / sh_ma120
            if price_ratio > trend_thresholds["bull_threshold"]:
                trend_type = self.TREND_BULL
            elif price_ratio < trend_thresholds["bear_threshold"]:
                trend_type = self.TREND_BEAR
            else:
                trend_type = self.TREND_RANGE
        else:
            trend_type = self.TREND_RANGE

        # 根据成交量和趋势，查找对应的模式名称
        mapping_key = f"{trend_type}_{volume_level}_volume"
        regime_name = regime_mapping.get(mapping_key, "结构性行情")

        self._current_regime = MarketRegime(
            volume_level=volume_level,
            trend_type=trend_type,
            regime_name=regime_name,
            total_turnover=total_turnover,
            sh_index_close=sh_close,
            sh_ma120=sh_ma120
        )

        return self._current_regime

    def get_current_weights(self) -> Dict[str, float]:
        """
        根据当前市场环境获取因子权重

        Returns:
            因子权重量典：{"quality": 0.25, "momentum": 0.1, "dividend": 0.4, "valuation": 0.25}

        Raises:
            RuntimeError: 配置未加载
            AttributeError: 配置中不存在当前市场模式对应的权重配置
        """
        self._load_config()

        # 获取当前市场环境
        if self._current_regime is None:
            self.determine_market_regime()

        regime_name = self._current_regime.regime_name

        # 从配置中读取权重（严禁写死）
        weights_node = getattr(self._config.factor_weights, regime_name)
        return weights_node.to_dict()

    def get_weights_for_mode(self, mode_name: str) -> Dict[str, float]:
        """
        获取指定市场模式的因子权重

        Args:
            mode_name: 模式名称，如 "缩量防御"、"放量进攻"

        Returns:
            因子权重量典

        Raises:
            RuntimeError: 配置未加载
            AttributeError: 配置中不存在指定模式的权重配置
        """
        self._load_config()

        # 从配置中读取权重（严禁写死）
        weights_node = getattr(self._config.factor_weights, mode_name)
        return weights_node.to_dict()

    def print_market_regime(self) -> None:
        """打印当前市场环境分析"""
        regime = self.determine_market_regime()
        weights = self.get_current_weights()

        print("\n" + "=" * 60)
        print("市场环境分析")
        print("=" * 60)
        print(f"两市成交额：{regime.total_turnover:.2f} 亿元")
        print(f"成交量水平：{regime.volume_level}")
        print(f"上证指数：{regime.sh_index_close:.2f} 点")
        print(f"120 日均线：{regime.sh_ma120:.2f} 点")
        print(f"趋势类型：{regime.trend_type}")
        print(f"市场模式：{regime.regime_name}")
        print(f"\n当前因子权重:")
        for factor, weight in weights.items():
            print(f"  {factor}: {weight:.0%}")
        print("=" * 60 + "\n")

    def screen(
        self,
        stock_list: List[str],
        factors: Optional[List[str]] = None,
        min_score: Optional[float] = None,
    ) -> List[ScreeningResult]:
        """
        执行股票筛选

        Args:
            stock_list: 待筛选的股票代码列表
            factors: 要使用的因子名称列表，None 表示使用所有因子
            min_score: 最低分数阈值，None 则从 config.yaml 读取 execution.min_total_score

        Returns:
            筛选结果列表
        """
        self._load_config()
        self._results = []

        # 从配置读取默认最低分数
        if min_score is None:
            min_score = self._config.execution.min_total_score

        factors_to_use = factors or self.factor_library.get_all_factors()

        for stock_code in stock_list:
            result = self._evaluate_stock(stock_code, factors_to_use)
            if result.score >= min_score:
                self._results.append(result)

        # 按分数降序排序
        self._results.sort(key=lambda x: x.score, reverse=True)
        return self._results

    def _evaluate_stock(
        self, stock_code: str, factors: List[str]
    ) -> ScreeningResult:
        """
        评估单只股票

        Args:
            stock_code: 股票代码
            factors: 要评估的因子列表

        Returns:
            筛选结果
        """
        passed_factors = []
        total_score = 0.0
        details = {}

        for factor_name in factors:
            factor_func = getattr(self.factor_library, factor_name, None)
            if factor_func is None:
                continue

            try:
                score, passed, detail = factor_func(stock_code)
                total_score += score
                if passed:
                    passed_factors.append(factor_name)
                details[factor_name] = detail
            except Exception as e:
                details[factor_name] = {"error": str(e)}

        return ScreeningResult(
            stock_code=stock_code,
            stock_name="",  # TODO: 获取股票名称
            score=total_score,
            factors_passed=passed_factors,
            details=details,
        )

    def get_top_stocks(self, n: int = 10) -> List[ScreeningResult]:
        """获取前 N 只股票"""
        return self._results[:n]

    def export_results(self, output_path: str) -> None:
        """导出筛选结果到文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("股票代码，股票名称，分数，通过因子\n")
            for result in self._results:
                f.write(
                    f"{result.stock_code},{result.stock_name},{result.score:.2f},"
                    f"{';'.join(result.factors_passed)}\n"
                )
