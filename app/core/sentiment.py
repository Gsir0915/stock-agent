# -*- coding: utf-8 -*-
"""
情绪分析模块
获取新闻并分析情绪（支持 AI 和本地规则）
"""

import os
import json
import re
import difflib
from typing import Dict, Any, List, Optional

from ..exceptions import SentimentAnalysisError
from ..utils.logger import get_logger

logger = get_logger("core.sentiment")


# 新闻情绪分析 Prompt 模板
NEWS_ANALYSIS_PROMPT = """
你是一位专业的证券分析师，请根据以下新闻标题判断其对股价的潜在影响。

## 分析规则
1. **正面**：利好消息，如业绩增长、回购增持、重大合同、政策扶持、产品涨价、并购重组等
2. **负面**：利空消息，如业绩下滑、减持套现、违规处罚、诉讼纠纷、产品降价、行业调控等
3. **中性**：常规公告、人事变动、无明显利好或利空的消息

## 输出格式
请严格按照以下 JSON 格式输出（仅输出 JSON，不要其他内容）：
{
    "analysis": [
        {
            "title": "新闻标题原文",
            "url": "新闻链接",
            "emotion": "正面/负面/中性",
            "reason": "简短分析理由（20 字以内）"
        }
    ],
    "summary": {
        "positive_count": 正面新闻数量，
        "negative_count": 负面新闻数量，
        "neutral_count": 中性新闻数量，
        "overall": "整体偏正面/整体偏负面/中性偏多/中性偏空/中性",
        "comment": "一句话总结（30 字以内）"
    }
}

## 新闻标题
{news_titles}

请开始分析：
"""


class SentimentAnalyzer:
    """情绪分析器"""

    def __init__(self, api_key: Optional[str] = None, use_ai: bool = True):
        """
        初始化情绪分析器

        Args:
            api_key: Anthropic API Key，如果为 None 则从环境变量获取
            use_ai: 是否使用 AI 分析
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_ai = use_ai and bool(self.api_key)

    def analyze(
        self,
        news_list: List[Dict[str, str]],
        target_count: int = 5
    ) -> Dict[str, Any]:
        """
        分析新闻情绪

        Args:
            news_list: 新闻列表，每条包含 title 和 url
            target_count: 目标新闻数量（用于日志记录）

        Returns:
            包含 analysis 和 summary 的字典

        Raises:
            SentimentAnalysisError: 分析失败时抛出
        """
        try:
            if not news_list:
                return {
                    "success": False,
                    "error": "无新闻数据",
                    "analysis": [],
                    "summary": {}
                }

            logger.info(f"分析 {len(news_list)} 条新闻的情绪...")

            # 选择分析方法
            if self.use_ai:
                result = self._analyze_with_ai(news_list)
            else:
                result = self._analyze_local(news_list)

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"情绪分析失败：{e}")
            if isinstance(e, SentimentAnalysisError):
                raise
            raise SentimentAnalysisError(f"情绪分析失败：{str(e)}")

    def _deduplicate_news(
        self,
        news_list: List[Dict[str, str]],
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, str]]:
        """
        去重新闻列表，移除内容高度相似的新闻

        Args:
            news_list: 原始新闻列表
            similarity_threshold: 相似度阈值，超过此值认为是重复新闻

        Returns:
            去重后的新闻列表
        """
        if len(news_list) <= 1:
            return news_list

        unique_news = []
        seen_titles = []

        for news in news_list:
            title = news.get("title", "").strip()
            if not title:
                continue

            # 检查是否与已有新闻重复
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = self._calculate_title_similarity(title, seen_title)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    logger.debug(
                        f"检测到重复新闻（相似度{similarity:.2f}）: {title}"
                    )
                    break

            if not is_duplicate:
                unique_news.append(news)
                seen_titles.append(title)

        if len(unique_news) < len(news_list):
            logger.info(
                f"新闻去重：{len(news_list)} -> {len(unique_news)} 条"
            )

        return unique_news

    def _calculate_title_similarity(
        self,
        title1: str,
        title2: str
    ) -> float:
        """
        计算两个标题的相似度

        结合关键词相似度与字符串相似度

        Args:
            title1: 标题 1
            title2: 标题 2

        Returns:
            相似度 (0-1)
        """
        # 如果一个是另一个的子串，直接使用字符串相似度
        if title1 in title2 or title2 in title1:
            return 0.85

        # 使用字符串相似度作为主要指标（更适合中文）
        string_sim = self._string_similarity(title1, title2)

        # 如果字符串相似度已经很高，直接返回
        if string_sim >= 0.8:
            return string_sim

        # 否则结合关键词相似度
        keyword_sim = self._calculate_keyword_similarity(title1, title2)

        # 加权平均：字符串相似度权重 70%，关键词相似度权重 30%
        return string_sim * 0.7 + keyword_sim * 0.3

    def _calculate_keyword_similarity(
        self,
        title1: str,
        title2: str
    ) -> float:
        """
        基于关键词计算相似度

        Args:
            title1: 标题 1
            title2: 标题 2

        Returns:
            相似度 (0-1)
        """
        # 移除常见停用词
        stopwords = {
            '的', '了', '和', '与', '及', '在', '已', '将', '等', '：',
            ',', '，', '。', '！', '？', '（', '）', '(', ')', ' '
        }

        # 提取关键词（按标点和数字分割）
        def extract_keywords(title):
            # 先按数字分割（保留数字）
            parts = re.split(r'(\d+\.?\d*)', title)
            words = []
            for part in parts:
                # 对非数字部分按标点分割
                if re.match(r'^\d+\.?\d*$', part):
                    words.append(part)
                else:
                    # 按常见中文分隔符分割
                    sub_words = re.split(r'[,\s:;.!?.!(),，。！？（）()\u3000]+', part)
                    words.extend([w for w in sub_words if w])

            return set(w for w in words if w and w not in stopwords)

        words1 = extract_keywords(title1)
        words2 = extract_keywords(title2)

        if not words1 or not words2:
            return 0

        # 计算 Jaccard 相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        计算字符串相似度（基于编辑距离）

        Args:
            s1: 字符串 1
            s2: 字符串 2

        Returns:
            相似度 (0-1)
        """
        if not s1 or not s2:
            return 0

        # 使用 difflib 计算相似度
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def _analyze_with_ai(
        self,
        news_list: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """使用 AI 分析新闻情绪"""
        try:
            # 保存原始新闻的 publish_time
            news_meta = {
                news['title']: news.get('publish_time', '')
                for news in news_list
            }

            # 构建 Prompt
            news_text = "\n".join([
                f"{i+1}. {news['title']} ({news.get('url', '')})"
                for i, news in enumerate(news_list)
            ])
            prompt = NEWS_ANALYSIS_PROMPT.format(news_titles=news_text)

            # 调用 Claude API
            response = self._call_claude_api(prompt)

            if response:
                # 补充 publish_time 到分析结果
                if 'analysis' in response:
                    for item in response['analysis']:
                        title = item.get('title', '')
                        if title in news_meta:
                            item['publish_time'] = news_meta[title]
                return response

            # AI 分析失败，降级到本地规则
            logger.warning("AI 分析失败，降级到本地规则分析")
            return self._analyze_local(news_list)

        except Exception as e:
            logger.warning(f"AI 分析异常：{e}，降级到本地规则分析")
            return self._analyze_local(news_list)

    def _call_claude_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用 Claude API

        Args:
            prompt: 提示词

        Returns:
            分析结果字典
        """
        import requests

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1024,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result["content"][0]["text"]

                # 解析 JSON 结果（可能包含在代码块中）
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group()
                    return json.loads(json_str)

                logger.warning("无法解析 AI 响应")
                return None

            else:
                logger.warning(f"Claude API 调用失败：{response.text}")
                return None

        except Exception as e:
            logger.warning(f"Claude API 调用异常：{e}")
            return None

    def _analyze_local(
        self,
        news_list: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        本地规则分析新闻情绪（备用方案）

        使用关键词匹配方法分析情绪
        """
        # 正面关键词
        positive_keywords = [
            '增长', '上涨', '盈利', '收益', '利好', '突破', '创新高', '回购',
            '增持', '中标', '签约', '合作', '涨价', '扩张', '重组', '并购',
            '分红', '预增', '扭亏', '大单', '订单', '政策扶持', '补贴',
            '减持股份', '回购股份', '业绩增长', '净利增长', '收入增长',
            '超额完成', '超预期', '历史新高', '行业龙头', '领先', '优势'
        ]

        # 负面关键词
        negative_keywords = [
            '下跌', '下滑', '亏损', '下降', '利空', '暴跌', '跳水', '减持',
            '套现', '处罚', '违规', '诉讼', '调查', '退市', '警示', '降薪',
            '裁员', '欠薪', '违约', '纠纷', '降价', '调控', '限售', '解禁',
            '预亏', '预减', '业绩下滑', '净利下滑', '收入下降', '亏损扩大',
            '被立案', '被处罚', '被警示', '不及预期', '暴雷', '风险', '危机'
        ]

        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for news in news_list:
            title = news.get("title", "")
            sentiment = "中性"
            reason = "无明显利好或利空"

            # 计算正面和负面得分
            pos_score = sum(1 for kw in positive_keywords if kw in title)
            neg_score = sum(1 for kw in negative_keywords if kw in title)

            if pos_score > neg_score:
                sentiment = "正面"
                reason = f"包含{pos_score}个利好关键词"
                positive_count += 1
            elif neg_score > pos_score:
                sentiment = "负面"
                reason = f"包含{neg_score}个利空关键词"
                negative_count += 1
            else:
                neutral_count += 1

            results.append({
                "title": title,
                "publish_time": news.get("publish_time", ""),
                "url": news.get("url", ""),
                "emotion": sentiment,
                "reason": reason
            })

        # 判断整体倾向
        overall = self._get_overall_sentiment(
            positive_count, negative_count, neutral_count
        )

        comment = (
            f"共{len(news_list)}条新闻，"
            f"{positive_count}条正面，{negative_count}条负面，{neutral_count}条中性"
        )

        return {
            "analysis": results,
            "summary": {
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "overall": overall,
                "comment": comment
            }
        }

    def _get_overall_sentiment(
        self,
        positive: int,
        negative: int,
        neutral: int
    ) -> str:
        """
        判断整体情绪倾向

        Args:
            positive: 正面新闻数
            negative: 负面新闻数
            neutral: 中性新闻数

        Returns:
            整体情绪描述
        """
        total = positive + negative

        if total == 0:
            return "中性"

        positive_ratio = positive / total

        if positive > negative + 1:
            return "整体偏正面"
        elif negative > positive + 1:
            return "整体偏负面"
        elif positive > negative:
            return "中性偏多"
        elif negative > positive:
            return "中性偏空"
        else:
            return "中性"


def fetch_stock_news(
    code: str,
    limit: int = 5
) -> List[Dict[str, str]]:
    """
    获取股票新闻（便捷函数）

    Args:
        code: 股票代码
        limit: 获取新闻数量

    Returns:
        新闻列表
    """
    from ..data.downloader import DataDownloader

    downloader = DataDownloader()
    return downloader.get_news(code, limit) or []


def analyze_news_emotion(
    news_list: List[Dict[str, str]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析新闻情绪（便捷函数）

    Args:
        news_list: 新闻列表
        api_key: API Key

    Returns:
        分析结果
    """
    analyzer = SentimentAnalyzer(api_key=api_key)
    return analyzer.analyze(news_list)
