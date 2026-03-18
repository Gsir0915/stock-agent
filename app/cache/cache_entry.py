# -*- coding: utf-8 -*-
"""缓存记录数据结构"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """缓存记录条目

    Attributes:
        key: 缓存键，格式为 {data_type}:{stock_code}:{date}:{version}
        data: 实际缓存的数据
        ttl_seconds: 生存时间（秒）
        created_at: 创建时间
        expires_at: 过期时间
        version: 缓存版本号（用于失效旧缓存）
        source: 数据来源（api/cache/batch）
        checksum: 数据校验和（用于检测数据损坏）
    """

    key: str
    data: Dict[str, Any]
    ttl_seconds: int
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(init=False)
    version: int = 1
    source: str = "api"
    checksum: str = field(init=False)

    def __post_init__(self):
        """初始化后处理"""
        # 计算过期时间
        self.expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)
        # 计算校验和
        self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """计算数据校验和（MD5）"""
        data_str = json.dumps(self.data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()

    def is_expired(self) -> bool:
        """检查是否已过期

        Returns:
            True 表示已过期，False 表示未过期
        """
        return datetime.now() > self.expires_at

    def is_fresh(self, freshness_threshold: int = 60) -> bool:
        """检查数据是否新鲜

        Args:
            freshness_threshold: 新鲜度阈值（秒），默认 60 秒

        Returns:
            True 表示数据新鲜，False 表示数据较旧
        """
        age = (datetime.now() - self.created_at).total_seconds()
        return age < freshness_threshold

    def checksum_valid(self) -> bool:
        """验证校验和是否有效

        Returns:
            True 表示校验和匹配，False 表示数据可能被篡改
        """
        current_checksum = self._compute_checksum()
        return current_checksum == self.checksum

    def refresh_ttl(self, new_ttl: int) -> None:
        """刷新 TTL

        Args:
            new_ttl: 新的 TTL 值（秒）
        """
        self.ttl_seconds = new_ttl
        self.expires_at = datetime.now() + timedelta(seconds=new_ttl)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典

        Returns:
            包含所有字段的字典
        """
        return {
            "key": self.key,
            "data": self.data,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "version": self.version,
            "source": self.source,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """从字典反序列化

        Args:
            data: 包含缓存记录字段的字典

        Returns:
            CacheEntry 实例
        """
        # 解析时间字段
        created_at = datetime.fromisoformat(data["created_at"])
        expires_at = datetime.fromisoformat(data["expires_at"])

        # 创建实例
        entry = cls(
            key=data["key"],
            data=data["data"],
            ttl_seconds=data["ttl_seconds"],
            version=data.get("version", 1),
            source=data.get("source", "api"),
        )

        # 覆盖计算的时间字段
        entry.created_at = created_at
        entry.expires_at = expires_at
        entry.checksum = data.get("checksum", entry._compute_checksum())

        return entry
