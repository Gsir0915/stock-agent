"""
数据访问层
包含数据下载、本地仓库、数据源适配器
"""

from .downloader import DataDownloader
from .repository import DataRepository
from .sources.base import BaseDataSource
from .sources.akshare import AkShareSource
from .sources.eastmoney import EastMoneySource

__all__ = [
    "DataDownloader",
    "DataRepository",
    "BaseDataSource",
    "AkShareSource",
    "EastMoneySource",
]
