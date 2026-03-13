# -*- coding: utf-8 -*-
"""热点新闻 Agent

封装新闻获取和情绪分析功能，提供热点新闻推荐。
"""

from pathlib import Path
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agent_base import BaseAgent, AgentResult


class HotNewsAgent(BaseAgent):
    """热点新闻 Agent

    支持的命令:
    - fetch: 获取热点新闻
    - concepts: 获取热门概念排行
    """

    name = "hot-news"
    description = "获取并推荐 A 股市场热点新闻，支持按板块/概念筛选"

    def __init__(self, config_path: Optional[str] = None):
        """初始化热点新闻 Agent

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path

    def execute(self, command: str, **kwargs) -> AgentResult:
        """执行命令

        Args:
            command: 命令名称 (fetch/concepts)
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        if command == "fetch":
            return self._execute_fetch(**kwargs)
        elif command == "concepts":
            return self._execute_concepts(**kwargs)
        else:
            return AgentResult.fail(f"Unknown command: {command}")

    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表"""
        return ["fetch", "concepts"]

    def _execute_fetch(self, **kwargs) -> AgentResult:
        """执行获取热点新闻

        Args:
            **kwargs: 参数包括 top_n, sector, sentiment 等

        Returns:
            AgentResult 执行结果
        """
        top_n = kwargs.get("top_n", 10)
        sector = kwargs.get("sector", None)
        sentiment_filter = kwargs.get("sentiment", "all")

        try:
            # 使用 akshare 获取全市场新闻
            # 由于 akshare 只支持个股新闻，我们通过获取多只股票新闻来聚合
            import akshare as ak
            import pandas as pd

            # 获取热门股票列表（按成交额排序）
            stock_list_df = ak.stock_zh_a_spot_em()
            if stock_list_df is None or len(stock_list_df) == 0:
                return AgentResult.fail("获取股票列表失败")

            # 取前 50 只活跃股票
            stock_list = stock_list_df.head(50)["代码"].tolist()

            # 聚合新闻
            all_news = []
            for code in stock_list:
                try:
                    news_df = ak.stock_news_em(symbol=code)
                    if news_df is not None and len(news_df) > 0:
                        for _, row in news_df.iterrows():
                            news_item = {
                                "code": str(row.iloc[0]) if len(row) > 0 else "",
                                "title": row.iloc[1] if len(row) > 1 else "",
                                "content": row.iloc[2] if len(row) > 2 else "",
                                "publish_time": row.iloc[3] if len(row) > 3 else "",
                                "source": row.iloc[4] if len(row) > 4 else "",
                                "url": row.iloc[5] if len(row) > 5 else "",
                            }
                            all_news.append(news_item)
                except Exception:
                    continue

            if len(all_news) == 0:
                return AgentResult.fail("获取新闻失败")

            # 去重（按标题）
            seen_titles = set()
            unique_news = []
            for news in all_news:
                if news["title"] not in seen_titles:
                    seen_titles.add(news["title"])
                    unique_news.append(news)

            # 筛选新闻
            results = self._filter_news(unique_news, top_n, sector, sentiment_filter)

            return AgentResult.ok(
                data=results,
                message=f"获取到 {len(results)} 条热点新闻"
            )

        except Exception as e:
            return AgentResult.fail(f"获取新闻失败：{e}")

    def _filter_news(
        self,
        news_list: List[Dict],
        top_n: int,
        sector: Optional[str],
        sentiment_filter: str
    ) -> List[Dict]:
        """筛选新闻

        Args:
            news_list: 新闻列表
            top_n: 返回数量
            sector: 板块/概念筛选
            sentiment_filter: 情绪筛选

        Returns:
            筛选后的新闻列表
        """
        from app.core.sentiment import SentimentAnalyzer

        results = []
        analyzer = SentimentAnalyzer()

        # 板块/概念关键词映射
        sector_keywords = {
            "人工智能": ["人工智能", "AI", "大模型", "ChatGPT", "智能"],
            "新能源": ["新能源", "光伏", "风电", "储能", "清洁能源"],
            "半导体": ["半导体", "芯片", "集成电路", "光刻机", "晶圆"],
            "医药生物": ["医药", "生物", "医疗", "创新药", "中药"],
            "新能源汽车": ["新能源汽车", "锂电池", "电动汽车", "比亚迪", "特斯拉"],
            "5G 概念": ["5G", "通信", "基站", "物联网"],
            "房地产": ["房地产", "楼市", "房价", "万科"],
            "金融": ["银行", "保险", "券商", "金融"],
            "消费": ["消费", "白酒", "食品", "零售"],
        }

        for news in news_list[:top_n * 3]:  # 多取一些用于筛选
            title = news.get("title", "")
            content = news.get("content", "")

            # 板块筛选
            if sector:
                keywords = sector_keywords.get(sector, [sector])
                text = title + content
                if not any(kw.lower() in text.lower() for kw in keywords):
                    continue

            # 情绪分析
            try:
                sentiment_result = analyzer.analyze_text(title)
                sentiment_label = sentiment_result.get("sentiment", "neutral")
                sentiment_score = sentiment_result.get("score", 0.5)
            except Exception:
                sentiment_label = "neutral"
                sentiment_score = 0.5

            # 情绪筛选
            if sentiment_filter != "all":
                if sentiment_filter == "positive" and sentiment_label != "positive":
                    continue
                if sentiment_filter == "negative" and sentiment_label != "negative":
                    continue

            # 提取相关股票（如果有）
            related_stocks = self._extract_stocks(news.get("code", ""))

            results.append({
                "title": title,
                "source": news.get("source", "未知"),
                "publish_time": news.get("publish_time", ""),
                "url": news.get("url", ""),
                "sentiment": sentiment_label,
                "sentiment_score": sentiment_score,
                "related_stocks": related_stocks,
            })

            if len(results) >= top_n:
                break

        return results

    def _extract_stocks(self, code: str) -> List[Dict]:
        """从股票代码提取股票信息

        Args:
            code: 股票代码

        Returns:
            股票信息列表
        """
        if not code or not code.isdigit() or len(code) != 6:
            return []

        if code.startswith(("600", "601", "603", "605")):
            market = "SH"
        elif code.startswith(("000", "001", "002", "003")):
            market = "SZ"
        elif code.startswith(("300", "301")):
            market = "SZ"
        else:
            return []

        from app.utils.stock_names import StockNameService
        name = StockNameService.get_name(code)
        return [{
            "code": code,
            "name": name or code,
            "market": market,
        }]

    def _execute_concepts(self, **kwargs) -> AgentResult:
        """执行获取热门概念排行

        Returns:
            AgentResult 执行结果
        """
        try:
            # 获取概念板块数据
            import akshare as ak

            # 获取概念板块涨跌幅排行
            concept_df = ak.stock_board_concept_name_em()

            if concept_df is None or len(concept_df) == 0:
                return AgentResult.fail("获取概念板块失败")

            results = []
            for _, row in concept_df.head(20).iterrows():
                results.append({
                    "rank": len(results) + 1,
                    "concept_name": row.get("板块名称", ""),
                    "change_pct": row.get("涨跌幅", 0),
                    "total_stocks": row.get("板块家数", 0),
                    "leading_stock": row.get("领涨股票", ""),
                    "leading_code": row.get("领涨股票 - 代码", ""),
                })

            return AgentResult.ok(
                data=results,
                message="获取概念板块排行成功"
            )

        except Exception as e:
            return AgentResult.fail(f"获取概念板块失败：{e}")
