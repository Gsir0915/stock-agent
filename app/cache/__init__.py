# -*- coding: utf-8 -*-
"""缓存模块

三层缓存架构：
- L1: 内存缓存 (MemoryCache) - 秒级访问，命中率 80%
- L2: SQLite 缓存 (SQLiteCache) - 毫秒级访问，命中率 15%
- L3: 批量预取 (BatchFetcher) - 批量获取，命中率 5%
"""

from .config import CacheConfig, get_cache_config
from .cache_entry import CacheEntry

__all__ = [
    "CacheConfig",
    "get_cache_config",
    "CacheEntry",
]
