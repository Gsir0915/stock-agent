# -*- coding: utf-8 -*-
"""
配置管理模块
使用 dataclass 实现类型安全的配置管理
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """
    应用配置类
    支持从 .env 文件加载配置
    """

    # API Keys
    anthropic_api_key: Optional[str] = None
    feishu_webhook_url: Optional[str] = None

    # 飞书机器人配置
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_verification_token: Optional[str] = None
    feishu_bot_port: int = 8080

    # 数据配置
    data_dir: str = "data"
    reports_dir: str = "reports"
    cache_days: int = 3  # 缓存宽容度（考虑周末/休市）

    # 分析配置
    default_news_limit: int = 5
    default_ma_windows: list = field(default_factory=lambda: [5, 10, 20, 60])

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # 功能开关
    enable_ai_analysis: bool = True
    enable_cache: bool = True

    def __post_init__(self):
        """初始化后从环境变量加载配置"""
        self._load_from_env()

    def _load_from_env(self):
        """从 .env 文件/环境变量加载配置"""
        # 尝试加载 .env 文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # 如果未安装 python-dotenv，直接使用环境变量

        # 加载配置
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic_api_key = api_key

        if webhook_url := os.getenv("FEISHU_WEBHOOK_URL"):
            self.feishu_webhook_url = webhook_url

        if app_id := os.getenv("FEISHU_APP_ID"):
            self.feishu_app_id = app_id

        if app_secret := os.getenv("FEISHU_APP_SECRET"):
            self.feishu_app_secret = app_secret

        if verification_token := os.getenv("FEISHU_VERIFICATION_TOKEN"):
            self.feishu_verification_token = verification_token

        if bot_port := os.getenv("FEISHU_BOT_PORT"):
            self.feishu_bot_port = int(bot_port)

        if data_dir := os.getenv("DATA_DIR"):
            self.data_dir = data_dir

        if reports_dir := os.getenv("REPORTS_DIR"):
            self.reports_dir = reports_dir

        if log_level := os.getenv("LOG_LEVEL"):
            self.log_level = log_level

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置实例"""
        return cls()

    @property
    def has_ai_api(self) -> bool:
        """是否有可用的 AI API"""
        return bool(self.anthropic_api_key)

    @property
    def has_feishu_webhook(self) -> bool:
        """是否有可用的飞书 Webhook"""
        return bool(self.feishu_webhook_url)

    @property
    def has_feishu_bot_config(self) -> bool:
        """是否有可用的飞书机器人配置"""
        return bool(
            self.feishu_app_id and
            self.feishu_app_secret and
            self.feishu_verification_token
        )


# 全局配置实例
_config: Optional[Config] = None


# ConfigHandler 是 Config 的别名，用于向后兼容
ConfigHandler = Config


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config):
    """设置全局配置实例"""
    global _config
    _config = config
