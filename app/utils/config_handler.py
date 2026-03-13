# -*- coding: utf-8 -*-
"""
配置处理模块

用于读取并解析 config.yaml 配置文件，支持：
1. 文件缺失时报错提醒
2. 通过对象属性直接访问参数（如 config.global_settings.cache_path）
3. 配置项不存在时返回 None 或默认值
"""

import os
from pathlib import Path
from typing import Any, Optional, Dict, List

import yaml


class ConfigNode:
    """
    配置节点类

    支持通过属性访问嵌套的字典数据，例如：
    config.strategy_weights.defensive -> 访问 nested dict 中的值
    """

    def __init__(self, data: Dict[str, Any], parent_path: str = ""):
        """
        初始化配置节点

        Args:
            data: 配置数据字典
            parent_path: 当前节点在配置树中的路径（用于错误提示）
        """
        self._data = data
        self._parent_path = parent_path

    def __getattr__(self, key: str) -> Any:
        """
        通过属性访问配置项

        Args:
            key: 配置项名称

        Returns:
            配置值，如果是字典则返回 ConfigNode 对象

        Raises:
            AttributeError: 配置项不存在时抛出
        """
        if key.startswith('_'):
            # 内部属性直接访问
            return object.__getattribute__(self, key)

        if key not in self._data:
            path = f"{self._parent_path}.{key}" if self._parent_path else key
            raise AttributeError(f"配置项不存在：'{path}'")

        value = self._data[key]

        # 嵌套字典自动转换为 ConfigNode
        if isinstance(value, dict):
            child_path = f"{self._parent_path}.{key}" if self._parent_path else key
            return ConfigNode(value, parent_path=child_path)

        return value

    def __contains__(self, key: str) -> bool:
        """支持 `in` 操作符检查配置项是否存在"""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """
        安全获取配置项，不存在时返回默认值

        Args:
            key: 配置项名称，支持路径式访问如 "filters.min_market_cap"
            default: 默认值

        Returns:
            配置值或默认值
        """
        # 支持路径式访问
        if '.' in key:
            keys = key.split('.')
            current_dict = self._data

            for i, k in enumerate(keys):
                if not isinstance(current_dict, dict):
                    return default

                if k not in current_dict:
                    return default

                value = current_dict[k]

                # 如果是字典且还有后续 keys，继续向下遍历
                if isinstance(value, dict) and i < len(keys) - 1:
                    current_dict = value
                else:
                    # 是叶子节点或最后一个 key
                    if i < len(keys) - 1:
                        # 还有剩余 keys 但已经是叶子节点
                        return default
                    return value

        # 单级 key 访问
        if key not in self._data:
            return default

        value = self._data[key]

        # 嵌套字典自动转换为 ConfigNode
        if isinstance(value, dict):
            child_path = f"{self._parent_path}.{key}" if self._parent_path else key
            return ConfigNode(value, parent_path=child_path)

        return value

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为普通字典

        Returns:
            原始配置字典
        """
        return self._data

    def __repr__(self) -> str:
        """调试时表示配置节点"""
        return f"ConfigNode(path='{self._parent_path or 'root'}', keys={list(self._data.keys())})"


class ConfigHandler:
    """
    配置处理器

    单例模式，负责加载和管理配置文件
    """

    _instance: Optional['ConfigHandler'] = None
    _config: Optional[ConfigNode] = None

    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        config_path: Optional[str] = None,
        auto_load: bool = True
    ):
        """
        初始化配置处理器

        Args:
            config_path: 配置文件路径，默认在当前模块目录下查找 config.yaml
            auto_load: 是否自动加载配置
        """
        if self._config is not None:
            # 已加载过，跳过
            return

        self._config_path = config_path
        self._config_file_missing = False

        if auto_load:
            self.load()

    def _find_config_file(self) -> Path:
        """
        查找配置文件

        搜索顺序：
        1. 构造函数传入的路径
        2. 当前模块目录下的 config.yaml
        3. 项目根目录下的 config.yaml

        Returns:
            配置文件路径

        Raises:
            FileNotFoundError: 配置文件不存在
        """
        # 1. 检查构造函数传入的路径
        if self._config_path:
            path = Path(self._config_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"配置文件不存在：{path}")

        # 2. 在当前模块目录下查找
        module_dir = Path(__file__).parent
        config_path = module_dir / "config.yaml"
        if config_path.exists():
            return config_path

        # 3. 在项目根目录下查找（向上一级）
        project_root = module_dir.parent.parent
        config_path = project_root / "config.yaml"
        if config_path.exists():
            return config_path

        # 4. 在 agents/stock_selector 目录下查找
        stock_selector_dir = project_root / "agents" / "stock_selector"
        config_path = stock_selector_dir / "config.yaml"
        if config_path.exists():
            return config_path

        raise FileNotFoundError(
            "配置文件 config.yaml 未找到\n"
            "请确保配置文件位于以下位置之一：\n"
            f"  - {Path(__file__).parent / 'config.yaml'}\n"
            f"  - {project_root / 'config.yaml'}\n"
            f"  - {stock_selector_dir / 'config.yaml'}"
        )

    def load(self, config_path: Optional[str] = None) -> ConfigNode:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径，None 则使用默认路径

        Returns:
            ConfigNode 配置根节点

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析失败
        """
        if config_path:
            self._config_path = config_path

        file_path = self._find_config_file()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            self._config = ConfigNode(data, parent_path="")
            self._config_path = str(file_path)
            self._config_file_missing = False

            return self._config

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"配置文件解析失败：{file_path}\n错误信息：{e}")

    @property
    def config(self) -> ConfigNode:
        """
        获取配置对象

        Returns:
            ConfigNode 配置根节点

        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            raise RuntimeError("配置未加载，请先调用 load() 方法")
        return self._config

    @property
    def config_path(self) -> str:
        """获取当前加载的配置文件路径"""
        return self._config_path

    def reload(self) -> ConfigNode:
        """
        重新加载配置文件

        Returns:
            ConfigNode 配置根节点
        """
        self._config = None
        return self.load()

    def __getattr__(self, key: str) -> Any:
        """
        支持直接通过 config_handler.key 访问配置项

        Args:
            key: 配置项名称

        Returns:
            配置值
        """
        if self._config is None:
            raise RuntimeError("配置未加载，请先调用 load() 方法")
        return getattr(self._config, key)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过路径字符串获取配置项

        Args:
            key_path: 配置项路径，如 "global.cache.path"
            default: 默认值

        Returns:
            配置值或默认值
        """
        if self._config is None:
            return default

        keys = key_path.split('.')
        current_dict = self._config._data

        for i, key in enumerate(keys):
            if not isinstance(current_dict, dict):
                return default

            if key not in current_dict:
                return default

            value = current_dict[key]

            # 如果是字典且还有后续 keys，继续向下遍历
            if isinstance(value, dict) and i < len(keys) - 1:
                current_dict = value
            else:
                # 是叶子节点或最后一个 key
                if i < len(keys) - 1:
                    # 还有剩余 keys 但已经是叶子节点
                    return default
                return value

    def validate(self, required_keys: List[str]) -> bool:
        """
        验证配置是否包含必需的键

        Args:
            required_keys: 必需的键列表，如 ["global.data_source", "filters.min_market_cap"]

        Returns:
            True 如果所有必需键都存在

        Raises:
            ValueError: 缺少必需的配置项
        """
        if self._config is None:
            raise RuntimeError("配置未加载")

        missing_keys = []

        for key_path in required_keys:
            value = self.get(key_path)
            if value is None:
                missing_keys.append(key_path)

        if missing_keys:
            raise ValueError(f"缺少必需的配置项：{', '.join(missing_keys)}")

        return True

    def print_summary(self) -> None:
        """打印配置摘要信息"""
        if self._config is None:
            print("配置未加载")
            return

        print(f"\n{'='*50}")
        print(f"配置文件：{self._config_path}")
        print(f"{'='*50}")

        # 打印顶层键
        for key in self._config.to_dict().keys():
            value = getattr(self._config, key)
            if isinstance(value, ConfigNode):
                sub_keys = list(value.to_dict().keys())
                print(f"\n{key}:")
                for sub_key in sub_keys[:5]:  # 只显示前 5 个子键
                    print(f"  - {sub_key}")
                if len(sub_keys) > 5:
                    print(f"  ... 共 {len(sub_keys)} 项")
            else:
                print(f"  {key}: {value}")

        print(f"{'='*50}\n")


# 全局便捷访问实例
_config_handler: Optional[ConfigHandler] = None


def get_config(config_path: Optional[str] = None, auto_load: bool = True) -> ConfigNode:
    """
    获取配置对象（便捷函数）

    Args:
        config_path: 配置文件路径
        auto_load: 是否自动加载

    Returns:
        ConfigNode 配置根节点

    Example:
        config = get_config()
        data_source = config.global_settings.data_source
        min_cap = config.filters.min_market_cap
    """
    global _config_handler

    if _config_handler is None:
        _config_handler = ConfigHandler(config_path, auto_load)
    elif config_path and _config_handler.config_path != config_path:
        _config_handler.load(config_path)

    return _config_handler.config


def reload_config(config_path: Optional[str] = None) -> ConfigNode:
    """
    重新加载配置（便捷函数）

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigNode 配置根节点
    """
    global _config_handler

    if _config_handler is None:
        _config_handler = ConfigHandler(config_path, auto_load=True)
    else:
        _config_handler.reload(config_path)

    return _config_handler.config


# 便捷的模块级访问方式
def __getattr__(name: str) -> Any:
    """
    支持直接从模块导入配置项

    Example:
        from utils.config_handler import global_settings
        print(global_settings.data_source)
    """
    if name in ('get_config', 'reload_config'):
        # 这些是函数，不应该在这里处理
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    config = get_config()
    try:
        return getattr(config, name)
    except AttributeError:
        raise AttributeError(f"配置中不存在顶级键：'{name}'")
