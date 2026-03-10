# -*- coding: utf-8 -*-
"""
数据下载服务
协调多个数据源，实现重试和降级策略
"""

from typing import Optional, List, Dict, Any
import difflib
import pandas as pd
import time

from .sources.base import BaseDataSource
from .sources.akshare import AkShareSource
from .sources.eastmoney import EastMoneySource
from ..exceptions import DataDownloadError, DataSourceError
from ..utils.logger import get_logger

logger = get_logger("data.downloader")


class DataDownloader:
    """数据下载服务"""

    def __init__(self, sources: Optional[List[BaseDataSource]] = None):
        """
        初始化数据下载器

        Args:
            sources: 数据源列表，如果为 None 则使用默认数据源
        """
        if sources is None:
            # 默认数据源优先级：AkShare -> EastMoney
            self.sources: List[BaseDataSource] = [
                AkShareSource(),
                EastMoneySource(),
            ]
        else:
            self.sources = sources

    def download_stock_history(
        self,
        code: str,
        skip_days: int = 3
    ) -> pd.DataFrame:
        """
        下载股票历史行情数据

        Args:
            code: 股票代码
            skip_days: 跳过下载的天数宽容度

        Returns:
            包含行情数据的 DataFrame

        Raises:
            DataDownloadError: 当所有数据源都失败时抛出
        """
        code_clean = self._clean_code(code)
        logger.info(f"开始下载 {code_clean} 的历史数据")

        last_error = None

        # 遍历所有数据源
        for source in self.sources:
            logger.info(f"尝试从 {source.name} 获取数据...")

            try:
                df = self._download_with_retry(source, code_clean)

                if df is not None and len(df) > 0:
                    logger.info(
                        f"成功从 {source.name} 获取 {len(df)} 条数据"
                    )
                    return df

                logger.warning(f"{source.name} 返回空数据，尝试下一个...")

            except Exception as e:
                logger.warning(f"{source.name} 获取失败：{type(e).__name__}: {e}")
                last_error = e

                # 短暂等待后尝试下一个数据源
                time.sleep(1)

        # 所有数据源都失败
        error_msg = f"所有数据源均下载失败"
        logger.error(error_msg)
        raise DataDownloadError(
            error_msg,
            {"code": code_clean, "last_error": str(last_error) if last_error else None}
        )

    def _download_with_retry(
        self,
        source: BaseDataSource,
        code: str,
        retry_times: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        带重试的数据下载

        Args:
            source: 数据源
            code: 股票代码
            retry_times: 重试次数

        Returns:
            行情数据 DataFrame
        """
        if retry_times is None:
            retry_times = source.retry_times

        last_error = None

        for attempt in range(retry_times + 1):
            try:
                df = source.get_stock_history(code)
                return df

            except Exception as e:
                last_error = e

                if attempt < retry_times:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"下载失败（{source.name} 第 {attempt + 1} 次），"
                        f"等待 {wait_time} 秒后重试..."
                    )
                    time.sleep(wait_time)

        # 重试全部失败
        raise DataSourceError(
            f"{source.name} 重试 {retry_times} 次后仍失败",
            {"code": code, "source": source.name}
        )

    def _clean_code(self, code: str) -> str:
        """清理股票代码"""
        return code.replace("sh", "").replace("sz", "").strip()

    def get_fundamentals(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本面数据

        Args:
            code: 股票代码

        Returns:
            基本面数据字典
        """
        code_clean = self._clean_code(code)
        logger.info(f"开始获取 {code_clean} 的基本面数据")

        for source in self.sources:
            try:
                logger.info(f"尝试从 {source.name} 获取基本面数据...")
                fundamentals = source.get_fundamentals(code_clean)

                if fundamentals is not None:
                    logger.info(f"成功从 {source.name} 获取基本面数据")
                    return fundamentals

            except Exception as e:
                logger.warning(
                    f"{source.name} 获取基本面数据失败："
                    f"{type(e).__name__}: {e}"
                )

        logger.warning("所有数据源获取基本面数据失败")
        return None

    def _fetch_news_with_offset(
        self,
        code: str,
        limit: int
    ) -> Optional[List[Dict[str, str]]]:
        """
        获取新闻（带偏移量）

        Args:
            code: 股票代码
            limit: 获取新闻数量

        Returns:
            新闻列表
        """
        for source in self.sources:
            try:
                logger.debug(f"从 {source.name} 获取新闻...")
                news_list = source.get_news(code, limit)

                if news_list is not None:
                    return news_list

            except Exception as e:
                logger.warning(
                    f"{source.name} 获取新闻失败："
                    f"{type(e).__name__}: {e}"
                )

        return []

    def get_news(
        self,
        code: str,
        limit: int = 50,
        target_count: int = 5
    ) -> Optional[List[Dict[str, str]]]:
        """
        获取股票相关新闻（自动去重并补充到目标数量）

        Args:
            code: 股票代码
            limit: 获取新闻数量（建议设置较大值以供去重）
            target_count: 目标新闻数量（去重后）

        Returns:
            新闻列表
        """
        code_clean = self._clean_code(code)
        logger.info(f"开始获取 {code_clean} 的新闻数据（目标：{target_count}条）")

        all_news = []
        seen_titles = []  # 使用列表存储已见标题，用于相似度比较

        # 一次性获取足够多的新闻
        news_list = self._fetch_news_with_offset(code_clean, limit)

        if not news_list:
            logger.warning("无法获取新闻")
            return []

        # 去重并添加新新闻
        for news in news_list:
            title = news.get("title", "").strip()
            if not title:
                continue

            # 检查是否与已有新闻重复（基于相似度）
            is_duplicate = False
            for seen_title in seen_titles:
                if self._is_duplicate_title(title, seen_title):
                    is_duplicate = True
                    logger.debug(f"检测到重复新闻：{title[:30]}...")
                    break

            if not is_duplicate:
                seen_titles.append(title)
                all_news.append(news)

            if len(all_news) >= target_count:
                break

        logger.info(
            f"成功获取 {len(all_news)} 条不重复新闻 "
            f"(原始：{len(news_list)}条，去重：{len(news_list)-len(all_news)}条)"
        )

        # 按发布时间倒序排列（最新的在前）
        sorted_news = sorted(
            all_news[:target_count],
            key=lambda x: x.get("publish_time", ""),
            reverse=True
        )
        return sorted_news

    def _is_duplicate_title(
        self,
        title1: str,
        title2: str,
        threshold: float = 0.7
    ) -> bool:
        """
        判断两个标题是否重复（基于相似度）

        Args:
            title1: 标题 1
            title2: 标题 2
            threshold: 相似度阈值

        Returns:
            True 如果是重复新闻
        """
        # 如果一个是另一个的子串，认为是重复
        if title1 in title2 or title2 in title1:
            return True

        # 使用字符串相似度
        similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
        return similarity >= threshold

    def add_source(self, source: BaseDataSource):
        """
        添加数据源

        Args:
            source: 数据源实例
        """
        self.sources.append(source)
        logger.info(f"添加数据源：{source.name}")
