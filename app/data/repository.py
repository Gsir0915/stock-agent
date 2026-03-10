# -*- coding: utf-8 -*-
"""
本地数据仓库
管理 CSV 文件的读写、缓存策略、数据验证
"""

import os
import datetime
import pandas as pd
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..exceptions import DataNotFoundError
from ..utils.logger import get_logger

logger = get_logger("data.repository")


class DataRepository:
    """本地数据仓库"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化数据仓库

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, code: str) -> Path:
        """
        获取股票数据文件路径

        Args:
            code: 股票代码

        Returns:
            文件路径
        """
        code_clean = code.replace("sh", "").replace("sz", "").strip()
        return self.data_dir / f"{code_clean}_daily.csv"

    def save_stock_data(self, code: str, df: pd.DataFrame) -> str:
        """
        保存股票数据到 CSV

        Args:
            code: 股票代码
            df: 股票数据 DataFrame

        Returns:
            保存的文件路径
        """
        file_path = self._get_file_path(code)

        try:
            df.to_csv(file_path, index=False, encoding="utf-8-sig")
            logger.info(f"保存股票数据到 {file_path}，共 {len(df)} 条记录")
            return str(file_path)

        except Exception as e:
            logger.error(f"保存数据失败：{e}")
            raise

    def load_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """
        从 CSV 加载股票数据

        Args:
            code: 股票代码

        Returns:
            股票数据 DataFrame，如果文件不存在则返回 None
        """
        file_path = self._get_file_path(code)

        if not file_path.exists():
            logger.debug(f"数据文件不存在：{file_path}")
            return None

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
            logger.debug(f"加载股票数据：{file_path}，共 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"加载数据失败：{e}")
            return None

    def is_data_fresh(self, code: str, skip_days: int = 3) -> bool:
        """
        检查数据是否足够新

        Args:
            code: 股票代码
            skip_days: 允许的天数宽容度（考虑周末/休市）

        Returns:
            True 如果数据足够新
        """
        df = self.load_stock_data(code)

        if df is None or len(df) == 0:
            return False

        try:
            # 获取最新日期
            latest_date_str = df.iloc[-1]["日期"]
            latest_date = datetime.datetime.strptime(
                latest_date_str, "%Y-%m-%d"
            ).date()
            today = datetime.date.today()

            # 检查日期差
            days_diff = (today - latest_date).days
            is_fresh = days_diff <= skip_days

            if is_fresh:
                logger.debug(
                    f"数据已是最新（最新日期：{latest_date_str}，相差{days_diff}天）"
                )
            else:
                logger.debug(
                    f"数据可能过期（最新日期：{latest_date_str}，相差{days_diff}天）"
                )

            return is_fresh

        except Exception as e:
            logger.warning(f"检查数据新鲜度失败：{e}")
            return False

    def get_cached_codes(self) -> List[str]:
        """
        获取所有已缓存的股票代码

        Returns:
            股票代码列表
        """
        codes = []

        for file_path in self.data_dir.glob("*_daily.csv"):
            # 从文件名提取代码
            code = file_path.stem.replace("_daily", "")
            codes.append(code)

        return codes

    def clear_cache(self, code: Optional[str] = None) -> bool:
        """
        清除缓存数据

        Args:
            code: 股票代码，如果为 None 则清除所有缓存

        Returns:
            True 如果清除成功
        """
        if code:
            file_path = self._get_file_path(code)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"清除缓存：{file_path}")
                return True
            return False
        else:
            count = 0
            for file_path in self.data_dir.glob("*_daily.csv"):
                file_path.unlink()
                count += 1
            logger.info(f"清除所有缓存，共 {count} 个文件")
            return True

    def get_cache_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存信息

        Args:
            code: 股票代码

        Returns:
            缓存信息字典
        """
        file_path = self._get_file_path(code)

        if not file_path.exists():
            return None

        try:
            stat = file_path.stat()
            df = self.load_stock_data(code)

            return {
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "record_count": len(df) if df is not None else 0,
                "created_at": datetime.datetime.fromtimestamp(
                    stat.st_ctime
                ).isoformat(),
                "modified_at": datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat(),
            }

        except Exception as e:
            logger.warning(f"获取缓存信息失败：{e}")
            return None


# 全局默认仓库实例
_default_repository: Optional[DataRepository] = None


def get_repository(data_dir: str = "data") -> DataRepository:
    """获取全局默认仓库实例"""
    global _default_repository
    if _default_repository is None:
        _default_repository = DataRepository(data_dir)
    return _default_repository
