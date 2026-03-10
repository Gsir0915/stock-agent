# -*- coding: utf-8 -*-
"""
技术分析模块单元测试
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.core.technical import TechnicalAnalyzer, calculate_moving_averages
from app.exceptions import TechnicalAnalysisError


class TestTechnicalAnalyzer(unittest.TestCase):
    """技术分析器测试类"""

    def setUp(self):
        """测试前准备"""
        self.analyzer = TechnicalAnalyzer()
        self.sample_df = self._create_sample_data()

    def _create_sample_data(self, days: int = 100) -> pd.DataFrame:
        """创建示例数据"""
        dates = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(days - 1, -1, -1)
        ]

        # 生成随机股价数据（随机游走）
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(days) * 2)

        df = pd.DataFrame({
            '日期': dates,
            '收盘': prices,
            '开盘': prices * (1 + np.random.randn(days) * 0.01),
            '最高': prices * (1 + np.abs(np.random.randn(days) * 0.02)),
            '最低': prices * (1 - np.abs(np.random.randn(days) * 0.02)),
            '成交量': np.random.randint(1000, 10000, days)
        })

        return df

    def test_analyze_success(self):
        """测试分析成功"""
        result = self.analyzer.analyze(self.sample_df)

        self.assertTrue(result['success'])
        self.assertIn('indicators', result)
        self.assertIn('signals', result)
        self.assertIn('data', result)

    def test_indicators_structure(self):
        """测试指标结构"""
        result = self.analyzer.analyze(self.sample_df)
        indicators = result['indicators']

        # 检查必需指标
        required_fields = ['close', 'ma5', 'ma10', 'ma20', 'ma60',
                          'dif', 'dea', 'macd', 'rsi', 'date']

        for field in required_fields:
            self.assertIn(field, indicators)

    def test_signals_generation(self):
        """测试信号生成"""
        result = self.analyzer.analyze(self.sample_df)
        signals = result['signals']

        # 应该有信号生成
        self.assertIsInstance(signals, list)
        self.assertGreater(len(signals), 0)

        # 检查信号结构
        for signal in signals:
            self.assertIn('type', signal)
            self.assertIn('signal', signal)
            self.assertIn('desc', signal)

    def test_insufficient_data(self):
        """测试数据量不足"""
        small_df = self._create_sample_data(days=30)

        with self.assertRaises(TechnicalAnalysisError):
            self.analyzer.analyze(small_df)

    def test_ma_calculation(self):
        """测试均线计算"""
        df_with_ma = calculate_moving_averages(self.sample_df, [5, 10, 20])

        # 检查均线列是否存在
        self.assertIn('MA5', df_with_ma.columns)
        self.assertIn('MA10', df_with_ma.columns)
        self.assertIn('MA20', df_with_ma.columns)

        # 检查均线值是否正确（非 NaN）
        # 注意：前 19 行可能有 NaN
        self.assertFalse(df_with_ma['MA5'].iloc[-1] !=
                         df_with_ma['MA5'].iloc[-1])  # NaN check

    def test_custom_ma_windows(self):
        """测试自定义均线周期"""
        analyzer = TechnicalAnalyzer(ma_windows=[5, 10, 30])
        result = analyzer.analyze(self.sample_df)

        indicators = result['indicators']
        self.assertIn('ma5', indicators)
        self.assertIn('ma10', indicators)
        # 30 日均线应该存在，60 日均线应该不存在
        self.assertNotIn('ma60', indicators)


class TestRSICalculation(unittest.TestCase):
    """RSI 计算测试"""

    def setUp(self):
        self.analyzer = TechnicalAnalyzer()

    def test_rsi_range(self):
        """测试 RSI 范围"""
        df = self._create_trend_data('up')
        result = self.analyzer.analyze(df)

        rsi = result['indicators']['rsi']
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)

    def test_rsi_uptrend(self):
        """测试上涨趋势 RSI"""
        df = self._create_trend_data('up')
        result = self.analyzer.analyze(df)
        rsi = result['indicators']['rsi']

        # 上涨趋势 RSI 应该较高
        self.assertGreater(rsi, 50)

    def test_rsi_downtrend(self):
        """测试下跌趋势 RSI"""
        df = self._create_trend_data('down')
        result = self.analyzer.analyze(df)
        rsi = result['indicators']['rsi']

        # 下跌趋势 RSI 应该较低
        self.assertLess(rsi, 50)

    def _create_trend_data(self, trend: str, days: int = 60) -> pd.DataFrame:
        """创建趋势数据"""
        dates = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(days - 1, -1, -1)
        ]

        np.random.seed(42)
        base_price = 100

        if trend == 'up':
            # 上涨趋势
            prices = [base_price * (1 + i * 0.02 + np.random.randn() * 0.5)
                     for i in range(days)]
        else:
            # 下跌趋势
            prices = [base_price * (1 - i * 0.02 + np.random.randn() * 0.5)
                     for i in range(days)]

        return pd.DataFrame({
            '日期': dates,
            '收盘': prices,
            '成交量': np.random.randint(1000, 10000, days)
        })


if __name__ == '__main__':
    unittest.main()
