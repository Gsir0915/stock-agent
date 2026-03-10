# -*- coding: utf-8 -*-
"""
日志配置模块
统一使用 logging 模块，支持控制台和文件输出
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "stock_agent",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回 logger 实例

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径，如果为 None 则只输出到控制台
        format_string: 日志格式字符串

    Returns:
        配置好的 logger 实例
    """
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    date_format = "%Y-%m-%d %H:%M:%S"

    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建 formatter
    formatter = logging.Formatter(format_string, datefmt=date_format)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（可选）
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"创建日志文件失败：{e}，将只输出到控制台")

    return logger


# 全局默认 logger
_default_logger: Optional[logging.Logger] = None


def get_logger(name: str = "stock_agent") -> logging.Logger:
    """获取全局默认 logger"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger(name)
    return _default_logger
