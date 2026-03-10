# -*- coding: utf-8 -*-
"""
股票名称映射服务
提供股票代码到名称的映射
"""

from typing import Optional


class StockNameService:
    """股票名称服务类"""

    # 常见股票名称映射
    STOCK_NAMES = {
        "600519": "贵州茅台",
        "000001": "平安银行",
        "002498": "汉得信息",
        "002050": "三花智控",
        "601318": "中国平安",
        "000858": "五粮液",
        "600036": "招商银行",
        "601888": "中国中免",
        "000333": "美的集团",
        "600276": "恒瑞医药",
        "002594": "比亚迪",
    }

    @classmethod
    def get_code(cls, name: str) -> Optional[str]:
        """
        根据股票名称获取代码

        Args:
            name: 股票名称

        Returns:
            股票代码，如果找不到则返回 None
        """
        for code, stock_name in cls.STOCK_NAMES.items():
            if stock_name == name:
                return code
        return None

    @classmethod
    def clean_code(cls, code: str) -> str:
        """
        清理股票代码，去除市场前缀和空格

        Args:
            code: 原始股票代码

        Returns:
            清理后的股票代码
        """
        return code.replace("sh", "").replace("sz", "").strip()

    @classmethod
    def add_name(cls, code: str, name: str):
        """
        添加股票名称映射

        Args:
            code: 股票代码
            name: 股票名称
        """
        code_clean = cls.clean_code(code)
        cls.STOCK_NAMES[code_clean] = name

    @classmethod
    def is_known_stock(cls, code: str) -> bool:
        """
        判断是否是已知股票

        Args:
            code: 股票代码

        Returns:
            True 如果是已知股票
        """
        code_clean = cls.clean_code(code)
        return code_clean in cls.STOCK_NAMES

    @classmethod
    def fetch_name_from_akshare(cls, code: str) -> Optional[str]:
        """
        从 AkShare 获取股票名称

        Args:
            code: 股票代码

        Returns:
            股票名称，如果获取失败则返回 None
        """
        code_clean = cls.clean_code(code)

        try:
            import akshare as ak

            # 从实时行情获取股票名称
            df_spot = ak.stock_zh_a_spot_em()
            if df_spot is not None and len(df_spot) > 0:
                stock_data = df_spot[df_spot["代码"] == code_clean]
                if len(stock_data) > 0:
                    name = stock_data.iloc[0]["名称"]
                    if name and name != "-":
                        # 缓存到内存中
                        cls.STOCK_NAMES[code_clean] = name
                        return name
        except Exception:
            pass  # 获取失败返回 None

        return None

    @classmethod
    def get_name(cls, code: str, fetch_remote: bool = True) -> str:
        """
        获取股票名称（支持远程获取）

        Args:
            code: 股票代码
            fetch_remote: 是否尝试从远程获取（默认 True）

        Returns:
            股票名称，如果找不到则返回代码本身
        """
        code_clean = cls.clean_code(code)

        # 先从本地缓存查找
        name = cls.STOCK_NAMES.get(code_clean)
        if name:
            return name

        # 尝试从 AkShare 获取
        if fetch_remote:
            name = cls.fetch_name_from_akshare(code_clean)
            if name:
                return name

        # 找不到返回代码本身
        return code_clean
