# -*- coding: utf-8 -*-
"""
基本面分析模块单元测试
"""

import unittest
from typing import Optional

from app.core.fundamental import FundamentalAnalyzer, ValueScore
from app.exceptions import FundamentalAnalysisError


class TestFundamentalAnalyzer(unittest.TestCase):
    """基本面分析器测试类"""

    def setUp(self):
        """测试前准备"""
        self.analyzer = FundamentalAnalyzer()

    def test_calculate_value_score_perfect(self):
        """测试完美评分"""
        score = self.analyzer.calculate_value_score(
            pe=8,      # PE<10: 40 分
            pb=0.8,    # PB<1: 30 分
            profit_growth=35  # >30%: 30 分
        )

        self.assertEqual(score.score, 100)
        self.assertEqual(score.pe_score, 40)
        self.assertEqual(score.pb_score, 30)
        self.assertEqual(score.growth_score, 30)
        self.assertIn("★", score.rating)

    def test_calculate_value_score_poor(self):
        """测试差评分"""
        score = self.analyzer.calculate_value_score(
            pe=60,     # PE>50: 0 分
            pb=6,      # PB>5: 0 分
            profit_growth=-10  # 负增长：5 分
        )

        self.assertEqual(score.score, 5)
        self.assertEqual(score.pe_score, 0)
        self.assertEqual(score.pb_score, 0)
        self.assertEqual(score.growth_score, 5)

    def test_calculate_value_score_medium(self):
        """测试中等评分"""
        score = self.analyzer.calculate_value_score(
            pe=25,     # 20-30: 20 分
            pb=2.5,    # 2-3: 20 分
            profit_growth=15  # 10-20%: 20 分
        )

        self.assertEqual(score.score, 60)
        self.assertEqual(score.pe_score, 20)
        self.assertEqual(score.pb_score, 20)
        self.assertEqual(score.growth_score, 20)

    def test_calculate_value_score_no_data(self):
        """测试无数据情况"""
        score = self.analyzer.calculate_value_score(
            pe=None,
            pb=None,
            profit_growth=None
        )

        self.assertEqual(score.score, 0)
        self.assertEqual(score.pe_score, 0)
        self.assertEqual(score.pb_score, 0)
        self.assertEqual(score.growth_score, 0)

    def test_calculate_value_score_estimated_pe(self):
        """测试估算 PE 情况"""
        score = self.analyzer.calculate_value_score(
            pe=20,
            pb=2,
            profit_growth=10,
            pe_estimated=True
        )

        self.assertIn("(估算)", score.details[0])

    def test_rating_levels(self):
        """测试评级等级"""
        test_cases = [
            (85, "★★★★★"),
            (70, "★★★★"),
            (50, "★★★"),
            (30, "★★"),
            (10, "★")
        ]

        for score_value, expected_stars in test_cases:
            # 构造能达到该分数的情况
            score = self.analyzer.calculate_value_score(
                pe=15 if score_value >= 60 else 40,
                pb=1.5 if score_value >= 40 else 4,
                profit_growth=20 if score_value >= 80 else 10
            )
            self.assertIn(expected_stars, score.rating)

    def test_analyze_method(self):
        """测试 analyze 方法"""
        fundamentals = {
            'pe': 20.5,
            'pb': 2.3,
            'profit_growth': 15.2
        }

        result = self.analyzer.analyze(fundamentals)

        self.assertTrue(result['success'])
        self.assertIn('indicators', result)
        self.assertIn('score', result)
        self.assertIn('rating', result)
        self.assertIn('details', result)

    def test_analyze_method_failure(self):
        """测试 analyze 方法失败情况"""
        # 空数据不应导致失败
        fundamentals = {
            'pe': None,
            'pb': None,
            'profit_growth': None
        }

        result = self.analyzer.analyze(fundamentals)
        self.assertTrue(result['success'])
        self.assertEqual(result['score'], 0)


class TestValueScoreDataclass(unittest.TestCase):
    """ValueScore 数据类测试"""

    def test_value_score_creation(self):
        """测试 ValueScore 创建"""
        score = ValueScore(
            score=75,
            rating="★★★★ 具有投资价值",
            details=["PE=20.00 (中等，20/40 分)"],
            pe_score=20,
            pb_score=25,
            growth_score=30
        )

        self.assertEqual(score.score, 75)
        self.assertEqual(score.pe_score + score.pb_score + score.growth_score,
                        score.score)


if __name__ == '__main__':
    unittest.main()
