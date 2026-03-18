# -*- coding: utf-8 -*-
"""缓存配置管理"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class TTLConfig:
    """TTL 配置"""
    base_ttl: int  # 基础 TTL（秒）
    refresh_time: Optional[str] = None  # 强制刷新时间（如 "20:00"）
    max_age: Optional[int] = None  # 最大年龄（秒）
    refresh_day: Optional[str] = None  # 强制刷新星期（如 "Sunday"）

    # 技术面特殊配置（根据市场状态动态调整）
    market_hours_ttl: int = 300  # 盘中 TTL（5 分钟）
    after_market_ttl: int = 3600  # 盘后 TTL（1 小时）
    pre_market_ttl: int = 43200  # 盘前 TTL（12 小时）


@dataclass
class CacheConfig:
    """缓存配置"""

    # 启用开关
    enable_cache: bool = True

    # L1 内存缓存配置
    memory_cache_enabled: bool = True
    memory_cache_max_size: int = 10000  # 最大缓存条目数
    memory_cache_default_ttl: int = 300  # 默认 TTL（5 分钟）

    # L2 SQLite 缓存配置
    sqlite_cache_enabled: bool = True
    sqlite_db_path: str = "data/cache.db"
    sqlite_wal_mode: bool = True  # 启用 WAL 模式提高并发

    # L3 批量预取配置
    batch_fetcher_enabled: bool = True
    batch_size: int = 5000  # 批量获取大小
    batch_max_workers: int = 4  # 最大工作线程数

    # TTL 配置
    ttl: Dict[str, TTLConfig] = field(default_factory=lambda: {
        "fundamentals": TTLConfig(base_ttl=86400, refresh_time="20:00"),  # 24 小时
        "technicals": TTLConfig(base_ttl=300),  # 5 分钟（盘中）
        "news": TTLConfig(base_ttl=1800, max_age=86400),  # 30 分钟，最多 24 小时
        "concepts": TTLConfig(base_ttl=604800, refresh_day="Sunday"),  # 7 天
    })

    # 降级配置
    fallback_enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0

    # 监控配置
    stats_enabled: bool = True
    alert_on_low_hit_rate: float = 0.5  # 命中率低于 50% 告警
    alert_on_high_fallback_rate: float = 0.2  # 降级率高于 20% 告警

    @classmethod
    def from_yaml(cls, config_path: str) -> "CacheConfig":
        """从 YAML 文件加载配置"""
        path = Path(config_path)
        if not path.exists():
            print(f"[WARN] 缓存配置文件不存在：{config_path}，使用默认配置")
            return cls()

        with open(path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)

        return cls._from_dict(yaml_data)

    @classmethod
    def _from_dict(cls, data: Dict) -> "CacheConfig":
        """从字典创建配置"""
        if not data:
            return cls()

        # 处理 TTL 配置
        ttl_configs = {}
        if "ttl" in data:
            for key, ttl_data in data["ttl"].items():
                if isinstance(ttl_data, dict):
                    ttl_configs[key] = TTLConfig(**ttl_data)

        return cls(
            enable_cache=data.get("enable_cache", True),
            memory_cache_enabled=data.get("memory_cache", {}).get("enabled", True),
            memory_cache_max_size=data.get("memory_cache", {}).get("max_size", 10000),
            memory_cache_default_ttl=data.get("memory_cache", {}).get("default_ttl", 300),
            sqlite_cache_enabled=data.get("sqlite_cache", {}).get("enabled", True),
            sqlite_db_path=data.get("sqlite_cache", {}).get("db_path", "data/cache.db"),
            sqlite_wal_mode=data.get("sqlite_cache", {}).get("wal_mode", True),
            batch_fetcher_enabled=data.get("batch_fetcher", {}).get("enabled", True),
            batch_size=data.get("batch_fetcher", {}).get("batch_size", 5000),
            batch_max_workers=data.get("batch_fetcher", {}).get("max_workers", 4),
            ttl=ttl_configs if ttl_configs else cls.__dataclass_fields__["ttl"].default_factory(),
            fallback_enabled=data.get("fallback_enabled", True),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1.0),
            stats_enabled=data.get("stats_enabled", True),
            alert_on_low_hit_rate=data.get("alert_on_low_hit_rate", 0.5),
            alert_on_high_fallback_rate=data.get("alert_on_high_fallback_rate", 0.2),
        )


# 全局配置实例
_cache_config: Optional[CacheConfig] = None


def get_cache_config(config_path: Optional[str] = None) -> CacheConfig:
    """获取全局缓存配置实例"""
    global _cache_config

    if _cache_config is None:
        # 默认从 config/cache.yaml 加载
        default_path = Path(__file__).parent.parent / "config" / "cache.yaml"

        if config_path:
            _cache_config = CacheConfig.from_yaml(config_path)
        elif default_path.exists():
            _cache_config = CacheConfig.from_yaml(str(default_path))
        else:
            print(f"[INFO] 使用默认缓存配置")
            _cache_config = CacheConfig()

    return _cache_config


def set_cache_config(config: CacheConfig):
    """设置全局缓存配置实例"""
    global _cache_config
    _cache_config = config
