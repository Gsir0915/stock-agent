# -*- coding: utf-8 -*-
"""
AkShare 数据源适配器
使用 akshare 库获取 A 股数据
"""

from typing import Optional, Dict, Any, List
import pandas as pd

from .base import BaseDataSource
from ...exceptions import DataSourceError


class AkShareSource(BaseDataSource):
    """AkShare 数据源"""

    name = "akshare"

    def __init__(self, timeout: int = 10, retry_times: int = 3):
        super().__init__(timeout, retry_times)

    def get_stock_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """获取股票历史行情数据"""
        import akshare as ak

        code_clean = self._clean_code(code)

        try:
            # 使用 akshare 获取 A 股历史行情数据（不复权，使用实际价格）
            # adjust="" 表示不复权，返回实际交易价格
            # 前复权 (qfq) 会导致价格失真，不适合展示给用户
            df = ak.stock_zh_a_hist(
                symbol=code_clean,
                period=period,
                adjust=""  # 不复权，使用实际价格
            )

            if df is None or len(df) == 0:
                raise DataSourceError("AkShare 返回空数据", {"code": code_clean})

            # 标准化列名
            df = self._normalize_dataframe(df)

            return df

        except Exception as e:
            raise DataSourceError(
                f"AkShare 获取历史数据失败：{str(e)}",
                {"code": code_clean, "source": self.name}
            )

    def get_fundamentals(self, code: str) -> Optional[Dict[str, Any]]:
        """获取股票基本面数据"""
        import akshare as ak

        code_clean = self._clean_code(code)
        result = {
            "code": code_clean,
            "name": "",
            "pe": None,
            "pb": None,
            "profit_growth": None,
            "source": self.name
        }

        # 方案 1：从实时行情获取
        try:
            df_spot = ak.stock_zh_a_spot_em()
            if df_spot is not None and len(df_spot) > 0:
                stock_data = df_spot[df_spot["代码"] == code_clean]
                if len(stock_data) > 0:
                    row = stock_data.iloc[0]
                    name = row.get("名称", "")
                    if name and name != "-":
                        result["name"] = name
                        # 同步更新到股票名称服务
                        from ..utils.stock_names import StockNameService
                        StockNameService.add_name(code_clean, name)

                    # 获取 PE（动态市盈率）
                    pe = row.get("市盈率 - 动态", None)
                    if pe and pe != "-":
                        try:
                            result["pe"] = float(pe)
                        except (ValueError, TypeError):
                            pass

                    # 获取 PB
                    pb = row.get("市净率", None)
                    if pb and pb != "-":
                        try:
                            result["pb"] = float(pb)
                        except (ValueError, TypeError):
                            pass

                    return result

        except Exception:
            pass  # 继续尝试方案 2

        # 方案 2：从财务指标接口获取
        try:
            df_financial = ak.stock_financial_analysis_indicator(
                symbol=code_clean,
                start_year="2024"
            )

            if df_financial is not None and len(df_financial) > 0:
                latest = df_financial.iloc[0]

                # 查找 PE 列
                for col in df_financial.columns:
                    if "市盈率" in col and result["pe"] is None:
                        try:
                            result["pe"] = float(latest[col])
                        except (ValueError, TypeError):
                            pass
                        break

                # 查找 PB 列
                for col in df_financial.columns:
                    if "市净率" in col and result["pb"] is None:
                        try:
                            result["pb"] = float(latest[col])
                        except (ValueError, TypeError):
                            pass
                        break

                # 查找净利润增长率列
                for col in df_financial.columns:
                    if "净利润增长率" in col and result["profit_growth"] is None:
                        try:
                            result["profit_growth"] = float(latest[col])
                        except (ValueError, TypeError):
                            pass
                        break

                # 使用 ROE 估算 PE（简化方法）
                if result["pe"] is None:
                    for col in df_financial.columns:
                        if "净资产收益率" in col and "(%)" in col:
                            try:
                                roe = float(latest[col])
                                if roe > 0:
                                    result["pe"] = 100 / roe
                                    result["pe_estimated"] = True
                            except (ValueError, TypeError):
                                pass
                            break

                result["source"] = "financial"
                return result

        except Exception:
            pass

        return result

    def get_news(self, code: str, limit: int = 10) -> Optional[List[Dict[str, str]]]:
        """
        获取股票相关新闻

        Args:
            code: 股票代码
            limit: 获取新闻数量（实际会返回更多以供去重）

        Returns:
            新闻列表
        """
        import akshare as ak

        code_clean = self._clean_code(code)

        try:
            # 获取所有可用新闻（akshare 默认返回约 10-20 条）
            df = ak.stock_news_em(symbol=code_clean)

            if df is not None and len(df) > 0:
                news_list = []
                for idx, row in df.iterrows():
                    # 获取更多新闻以供去重（最多 50 条）
                    if idx >= max(limit * 5, 50):
                        break

                    title = row.iloc[1] if len(row) > 1 else ""
                    publish_time = row.iloc[3] if len(row) > 3 else ""
                    url = row.iloc[5] if len(row) > 5 else ""

                    if title and len(str(title).strip()) > 0:
                        news_list.append({
                            "title": str(title).strip(),
                            "publish_time": str(publish_time).strip() if publish_time else "",
                            "url": str(url).strip() if url else ""
                        })

                return news_list

        except Exception as e:
            raise DataSourceError(
                f"AkShare 获取新闻失败：{str(e)}",
                {"code": code_clean, "source": self.name}
            )

        return []
