# -*- coding: utf-8 -*-
"""
情绪分析模块单元测试
"""

import unittest
from typing import List, Dict

from app.core.sentiment import SentimentAnalyzer, analyze_news_emotion
from app.exceptions import SentimentAnalysisError


class TestSentimentAnalyzer(unittest.TestCase):
    """情绪分析器测试类"""

    def setUp(self):
        """测试前准备"""
        # 不使用 AI（避免 API 调用）
        self.analyzer = SentimentAnalyzer(api_key=None, use_ai=False)

    def test_analyze_empty_news(self):
        """测试空新闻列表"""
        result = self.analyzer.analyze([])

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], '无新闻数据')

    def test_analyze_positive_news(self):
        """测试正面新闻"""
        news_list = [
            {"title": "公司业绩大幅增长，净利润创新高", "url": "http://example.com/1"}
        ]

        result = self.analyzer.analyze(news_list)

        self.assertTrue(result['success'])
        self.assertEqual(result['summary']['positive_count'], 1)
        self.assertEqual(result['summary']['negative_count'], 0)

    def test_analyze_negative_news(self):
        """测试负面新闻"""
        news_list = [
            {"title": "公司业绩下滑，净利润出现亏损", "url": "http://example.com/1"}
        ]

        result = self.analyzer.analyze(news_list)

        self.assertTrue(result['success'])
        self.assertEqual(result['summary']['positive_count'], 0)
        self.assertEqual(result['summary']['negative_count'], 1)

    def test_analyze_neutral_news(self):
        """测试中性新闻"""
        news_list = [
            {"title": "公司发布人事变动公告", "url": "http://example.com/1"}
        ]

        result = self.analyzer.analyze(news_list)

        self.assertTrue(result['success'])
        self.assertEqual(result['summary']['neutral_count'], 1)

    def test_analyze_mixed_news(self):
        """测试混合新闻"""
        news_list = [
            {"title": "公司业绩增长 20%", "url": "http://example.com/1"},
            {"title": "公司收到监管处罚", "url": "http://example.com/2"},
            {"title": "公司发布日常公告", "url": "http://example.com/3"}
        ]

        result = self.analyzer.analyze(news_list)

        self.assertTrue(result['success'])
        self.assertEqual(result['summary']['positive_count'], 1)
        self.assertEqual(result['summary']['negative_count'], 1)
        self.assertEqual(result['summary']['neutral_count'], 1)

    def test_local_analysis_keywords(self):
        """测试本地关键词分析"""
        # 正面关键词测试
        positive_titles = [
            "业绩增长", "净利润创新高", "回购股份", "中标大单",
            "业绩预增", "扭亏为盈", "股价创新高"
        ]

        for title in positive_titles:
            result = self._analyze_single_news(title)
            self.assertEqual(
                result['analysis'][0]['emotion'],
                "正面",
                f"标题 '{title}' 应该被判断为正面"
            )

        # 负面关键词测试
        negative_titles = [
            "业绩下滑", "净利润亏损", "股东减持", "产品降价",
            "业绩预亏", "被监管处罚", "股价暴跌"
        ]

        for title in negative_titles:
            result = self._analyze_single_news(title)
            self.assertEqual(
                result['analysis'][0]['emotion'],
                "负面",
                f"标题 '{title}' 应该被判断为负面"
            )

    def test_overall_sentiment判断(self):
        """测试整体情绪判断"""
        # 正面多于负面
        news_list = [
            {"title": "业绩增长", "url": ""},
            {"title": "业绩增长", "url": ""},
            {"title": "业绩下滑", "url": ""}
        ]
        result = self.analyzer.analyze(news_list)
        self.assertIn("正面", result['summary']['overall'])

        # 负面多于正面
        news_list = [
            {"title": "业绩增长", "url": ""},
            {"title": "业绩下滑", "url": ""},
            {"title": "业绩下滑", "url": ""}
        ]
        result = self.analyzer.analyze(news_list)
        self.assertIn("负面", result['summary']['overall'])

    def test_news_analysis_structure(self):
        """测试分析结果结构"""
        news_list = [
            {"title": "测试新闻", "url": "http://example.com/1"}
        ]

        result = self.analyzer.analyze(news_list)

        self.assertIn('analysis', result)
        self.assertIn('summary', result)

        # 检查分析结果结构
        analysis = result['analysis'][0]
        self.assertIn('title', analysis)
        self.assertIn('emotion', analysis)
        self.assertIn('reason', analysis)

        # 检查汇总结构
        summary = result['summary']
        self.assertIn('positive_count', summary)
        self.assertIn('negative_count', summary)
        self.assertIn('neutral_count', summary)
        self.assertIn('overall', summary)
        self.assertIn('comment', summary)

    def _analyze_single_news(self, title: str) -> dict:
        """分析单条新闻"""
        news_list = [{"title": title, "url": ""}]
        return self.analyzer.analyze(news_list)


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def test_analyze_news_emotion_function(self):
        """测试 analyze_news_emotion 函数"""
        news_list = [
            {"title": "业绩增长", "url": ""}
        ]

        result = analyze_news_emotion(news_list, api_key=None)

        self.assertTrue(result['success'])
        self.assertEqual(result['summary']['positive_count'], 1)


if __name__ == '__main__':
    unittest.main()
