# -*- coding: utf-8 -*-
"""
数据源基类
定义标准接口，所有数据源实现必须继承此基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd


class BaseDataSource(ABC):
    """数据源基类"""

    name: str = "base"

    def __init__(self, timeout: int = 10, retry_times: int = 3):
        """
        初始化数据源

        Args:
            timeout: 请求超时时间（秒）
            retry_times: 重试次数
        """
        self.timeout = timeout
        self.retry_times = retry_times

    @abstractmethod
    def get_stock_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史行情数据

        Args:
            code: 股票代码
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD
            period: 数据周期 (daily/weekly/monthly)

        Returns:
            包含行情数据的 DataFrame
        """
        pass

    @abstractmethod
    def get_fundamentals(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本面数据

        Args:
            code: 股票代码

        Returns:
            包含基本面数据的字典
        """
        pass

    @abstractmethod
    def get_news(self, code: str, limit: int = 10) -> Optional[List[Dict[str, str]]]:
        """
        获取股票相关新闻

        Args:
            code: 股票代码
            limit: 获取新闻数量

        Returns:
            新闻列表，每条包含 title 和 url
        """
        pass

    def _clean_code(self, code: str) -> str:
        """
        清理股票代码

        Args:
            code: 原始股票代码

        Returns:
            清理后的股票代码
        """
        return code.replace("sh", "").replace("sz", "").strip()

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化 DataFrame 列名

        Args:
            df: 原始 DataFrame

        Returns:
            标准化列名的 DataFrame
        """
        # 常见列名映射
        column_mapping = {
            "日期": "日期",
            "开盘": "开盘",
            "收盘": "收盘",
            "最高": "最高",
            "最低": "最低",
            "成交量": "成交量",
            "成交额": "成交额",
            "振幅": "振幅",
            "涨跌幅": "涨跌幅",
            "涨跌额": "涨跌额",
            "换手": "换手",
        }

        # 只保留已知列
        available_columns = {
            k: v for k, v in column_mapping.items()
            if k in df.columns
        }

        if available_columns:
            df = df.rename(columns=available_columns)

        return df
