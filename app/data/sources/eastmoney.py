# -*- coding: utf-8 -*-
"""
东方财富数据源适配器
使用 EastMoney API 获取 A 股数据
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import requests

from .base import BaseDataSource
from ...exceptions import DataSourceError


class EastMoneySource(BaseDataSource):
    """东方财富数据源"""

    name = "eastmoney"

    def __init__(self, timeout: int = 10, retry_times: int = 3):
        super().__init__(timeout, retry_times)
        self.base_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        # 模拟浏览器请求头，避免被反爬拦截
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

    def _get_secid(self, code: str) -> str:
        """
        获取证券 ID（市场代码。股票代码）

        Args:
            code: 股票代码

        Returns:
            证券 ID 格式
        """
        # 1=沪 A，0=深 A
        if code.startswith("6"):
            return f"1.{code}"
        else:
            return f"0.{code}"

    def get_stock_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """获取股票历史行情数据"""
        code_clean = self._clean_code(code)
        secid = self._get_secid(code_clean)

        # 如果未指定日期，获取全部历史数据
        if start_date is None:
            start_date = "19700101"
        if end_date is None:
            end_date = "20991231"

        # 移除日期中的横线
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")

        params = {
            "secid": secid,
            "klt": 101,  # 日线
            "fqt": 1,    # 前复权
            "beg": start_date,
            "end": end_date
        }

        try:
            resp = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            resp.raise_for_status()

            data = resp.json()
            if data.get("data") is None or len(data.get("data", {}).get("klines", [])) == 0:
                raise DataSourceError("EastMoney 返回空数据", {"code": code_clean})

            # 解析 K 线数据
            klines = data["data"]["klines"]
            records = []

            for line in klines:
                parts = line.split(",")
                if len(parts) >= 11:
                    records.append({
                        "日期": parts[0],
                        "开盘": float(parts[1]),
                        "收盘": float(parts[2]),
                        "最高": float(parts[3]),
                        "最低": float(parts[4]),
                        "成交量": int(parts[5]),
                        "成交额": float(parts[6]),
                        "振幅": float(parts[7]),
                        "涨跌幅": float(parts[8]),
                        "涨跌额": float(parts[9]),
                        "换手": float(parts[10])
                    })

            df = pd.DataFrame(records)
            return df

        except requests.RequestException as e:
            raise DataSourceError(
                f"EastMoney 网络请求失败：{str(e)}",
                {"code": code_clean, "source": self.name}
            )
        except Exception as e:
            raise DataSourceError(
                f"EastMoney 解析数据失败：{str(e)}",
                {"code": code_clean, "source": self.name}
            )

    def get_fundamentals(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本面数据

        注意：EastMoney API 主要通过 akshare 封装获取财务数据，
        此方法作为备用，主要依赖 akshare 实现
        """
        # EastMoney 数据源主要提供行情数据，基本面数据通过 akshare 获取
        return None

    def get_news(self, code: str, limit: int = 10) -> Optional[List[Dict[str, str]]]:
        """
        获取股票相关新闻

        注意：EastMoney 新闻 API 需要通过 akshare 调用
        """
        # EastMoney 数据源主要提供行情数据，新闻数据通过 akshare 获取
        return None
