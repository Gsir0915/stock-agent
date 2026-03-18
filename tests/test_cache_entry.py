# -*- coding: utf-8 -*-
"""缓存记录单元测试"""

import pytest
import time
from datetime import datetime, timedelta
from app.cache.cache_entry import CacheEntry


class TestCacheEntry:
    """测试 CacheEntry 类"""

    def test_create_entry(self):
        """测试创建缓存记录"""
        data = {"stock_code": "600519", "price": 1800.5}
        entry = CacheEntry(
            key="technical:600519:20260317",
            data=data,
            ttl_seconds=300
        )

        assert entry.key == "technical:600519:20260317"
        assert entry.data == data
        assert entry.ttl_seconds == 300
        assert entry.version == 1
        assert entry.source == "api"
        assert entry.checksum is not None

    def test_is_expired(self):
        """测试过期检测"""
        # 未过期
        entry = CacheEntry(
            key="test:1",
            data={"value": 1},
            ttl_seconds=300
        )
        assert not entry.is_expired()

        # 手动设置过期时间（模拟已过期）
        entry.expires_at = datetime.now() - timedelta(seconds=10)
        assert entry.is_expired()

    def test_is_fresh(self):
        """测试新鲜度检测"""
        entry = CacheEntry(
            key="test:1",
            data={"value": 1},
            ttl_seconds=300
        )

        # 刚创建，应该是新鲜的
        assert entry.is_fresh(freshness_threshold=60)

        # 模拟创建时间较早
        entry.created_at = datetime.now() - timedelta(seconds=120)
        entry.expires_at = datetime.now() + timedelta(seconds=180)
        assert not entry.is_fresh(freshness_threshold=60)

    def test_to_dict(self):
        """测试序列化为字典"""
        data = {"stock_code": "600519", "price": 1800.5}
        entry = CacheEntry(
            key="technical:600519:20260317",
            data=data,
            ttl_seconds=300,
            source="cache"
        )

        result = entry.to_dict()

        assert result["key"] == "technical:600519:20260317"
        assert result["data"] == data
        assert result["ttl_seconds"] == 300
        assert result["source"] == "cache"
        assert result["version"] == 1
        assert "created_at" in result
        assert "expires_at" in result
        assert "checksum" in result

    def test_from_dict(self):
        """测试从字典反序列化"""
        now = datetime.now()
        original = {
            "key": "technical:600519:20260317",
            "data": {"stock_code": "600519", "price": 1800.5},
            "ttl_seconds": 300,
            "source": "cache",
            "version": 2,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "checksum": "abc123"
        }

        entry = CacheEntry.from_dict(original)

        assert entry.key == "technical:600519:20260317"
        assert entry.data == {"stock_code": "600519", "price": 1800.5}
        assert entry.ttl_seconds == 300
        assert entry.source == "cache"
        assert entry.version == 2
        assert entry.checksum == "abc123"

    def test_checksum_valid(self):
        """测试校验和验证"""
        data = {"stock_code": "600519", "price": 1800.5}
        entry = CacheEntry(
            key="technical:600519:20260317",
            data=data,
            ttl_seconds=300
        )

        # 初始校验和应该有效
        assert entry.checksum_valid()

        # 篡改数据后校验和应该失效
        entry.data["price"] = 2000.0
        assert not entry.checksum_valid()

    def test_refresh_ttl(self):
        """测试刷新 TTL"""
        entry = CacheEntry(
            key="test:1",
            data={"value": 1},
            ttl_seconds=60
        )

        original_expires = entry.expires_at

        # 刷新 TTL
        entry.refresh_ttl(300)

        # 过期时间应该延长
        assert entry.expires_at > original_expires
        assert entry.ttl_seconds == 300
