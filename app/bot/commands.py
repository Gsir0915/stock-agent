# -*- coding: utf-8 -*-
"""
命令解析器
解析飞书用户发送的消息，识别股票代码
"""

import re
from typing import Optional, Tuple
from ..utils.stock_names import StockNameService
from ..utils.logger import get_logger

logger = get_logger("bot.commands")


class CommandParser:
    """命令解析器类"""

    # 股票代码正则（6 位数字）
    STOCK_CODE_PATTERN = re.compile(r'\b(\d{6})\b')

    # 支持的命令前缀
    SUPPORTED_COMMANDS = ['分析', '查看', '查询', 'help', '帮助']

    @classmethod
    def parse_message(cls, message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析用户消息，提取股票代码

        Args:
            message: 用户发送的消息文本

        Returns:
            (stock_code, command) 元组
            - stock_code: 识别出的股票代码，如果未识别返回 None
            - command: 识别出的命令类型，如 'analyze', 'help', None
        """
        if not message or not message.strip():
            return None, None

        message = message.strip()
        logger.debug(f"解析消息：{message}")

        # 检查是否是帮助命令
        if message.lower() in ['help', '帮助']:
            return None, 'help'

        # 尝试从消息中提取股票代码
        stock_code = cls._extract_stock_code(message)

        if stock_code:
            # 验证股票代码是否有效（是否是已知股票）
            if StockNameService.is_known_stock(stock_code):
                logger.info(f"识别出股票代码：{stock_code}")
                return stock_code, 'analyze'
            else:
                # 未知股票，但仍然返回代码（让分析引擎处理）
                logger.warning(f"识别出未知股票代码：{stock_code}")
                return stock_code, 'analyze'

        # 尝试从命令 + 股票名称识别
        for cmd in cls.SUPPORTED_COMMANDS:
            if message.startswith(cmd):
                remaining = message[len(cmd):].strip()
                # 去掉可能的空格、冒号等
                remaining = remaining.lstrip(':：').strip()
                stock_code = cls._extract_stock_code(remaining)
                if stock_code:
                    return stock_code, 'analyze'

        # 尝试直接使用消息内容作为股票名称查询代码
        stock_code = StockNameService.get_code(message.strip())
        if stock_code:
            logger.info(f"通过股票名称查询到代码：{message} -> {stock_code}")
            return stock_code, 'analyze'

        logger.warning(f"无法解析消息：{message}")
        return None, None

    @classmethod
    def _extract_stock_code(cls, text: str) -> Optional[str]:
        """
        从文本中提取股票代码

        Args:
            text: 文本内容

        Returns:
            股票代码，如果未找到返回 None
        """
        # 查找 6 位数字
        matches = cls.STOCK_CODE_PATTERN.findall(text)

        if matches:
            # 返回第一个匹配的股票代码
            code = matches[0]
            logger.debug(f"从文本中提取到股票代码：{code}")
            return code

        return None

    @classmethod
    def get_help_message(cls) -> str:
        """
        获取帮助消息

        Returns:
            帮助消息文本
        """
        return """🤖 **股票分析机器人使用指南**

**支持的命令格式**：
• `@bot 600519` - 直接发送股票代码
• `@bot 分析 600519` - 带命令前缀
• `@bot 贵州茅台` - 发送股票名称

**功能说明**：
• 自动执行技术分析、基本面分析、新闻情绪分析
• 生成投资分析报告并推送到群聊

**注意事项**：
• 分析可能需要 10-30 秒
• 仅支持 A 股股票代码

有问题请联系管理员。"""
