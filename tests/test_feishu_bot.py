# -*- coding: utf-8 -*-
"""
飞书机器人模块测试
"""

import pytest


class TestCommandParser:
    """测试命令解析器"""

    def test_parse_stock_code_only(self):
        """测试纯股票代码解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("600519")
        assert code == "600519"
        assert cmd == "analyze"

    def test_parse_with_command(self):
        """测试带命令的解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("分析 600519")
        assert code == "600519"
        assert cmd == "analyze"

    def test_parse_stock_name(self):
        """测试股票名称解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("贵州茅台")
        assert code == "600519"
        assert cmd == "analyze"

    def test_parse_help_command(self):
        """测试帮助命令解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("帮助")
        assert code is None
        assert cmd == "help"

    def test_parse_empty_message(self):
        """测试空消息解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("")
        assert code is None
        assert cmd is None

    def test_parse_invalid_code(self):
        """测试无效代码解析"""
        from app.bot.commands import CommandParser

        code, cmd = CommandParser.parse_message("123456")
        # 未知股票代码，但仍返回代码让分析引擎处理
        assert code == "123456"
        assert cmd == "analyze"

    def test_get_help_message(self):
        """测试帮助消息"""
        from app.bot.commands import CommandParser

        help_msg = CommandParser.get_help_message()
        assert "股票分析机器人使用指南" in help_msg
        assert "600519" in help_msg


class TestFeishuClient:
    """测试飞书客户端"""

    def test_build_analysis_card(self):
        """测试分析卡片构建"""
        from app.bot.feishu_client import FeishuClient

        technical = {
            'success': True,
            'indicators': {
                'close': 1700.00,
                'ma5': 1695.00,
                'ma20': 1680.00,
                'dif': 0.0012,
                'dea': 0.0010,
                'macd': 0.0002,
                'rsi': 55.0
            },
            'signals': [
                {'signal': '🟢 金叉', 'desc': 'MACD 金叉信号'}
            ]
        }

        fundamental = {
            'success': True,
            'score': 75,
            'rating': '推荐',
            'indicators': {
                'pe': 30.5,
                'pb': 5.2,
                'profit_growth': 15.0
            },
            'details': ['盈利能力较强', '估值合理']
        }

        news = {
            'success': True,
            'summary': {
                'positive_count': 3,
                'negative_count': 1,
                'neutral_count': 1,
                'overall': '正面'
            },
            'news': [
                {'title': '公司新闻 1', 'emotion': '正面', 'url': 'http://example.com'}
            ]
        }

        card = FeishuClient.build_analysis_card(
            code="600519",
            stock_name="贵州茅台",
            technical=technical,
            fundamental=fundamental,
            news=news
        )

        assert card is not None
        assert 'config' in card
        assert 'header' in card
        assert 'elements' in card
        assert card['header']['title']['content'] == "📊 股票投资分析报告 - 贵州茅台 (600519)"


class TestConfig:
    """测试配置模块"""

    def test_config_load(self):
        """测试配置加载"""
        from app.config import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, 'feishu_app_id')
        assert hasattr(config, 'feishu_app_secret')
        assert hasattr(config, 'feishu_verification_token')
        assert hasattr(config, 'feishu_bot_port')

    def test_has_feishu_bot_config(self):
        """测试飞书配置检查"""
        from app.config import get_config

        config = get_config()
        # 如果没有配置环境变量，应该返回 False
        result = config.has_feishu_bot_config
        assert isinstance(result, bool)


class TestMessageHandler:
    """测试消息处理器"""

    def test_handler_init(self):
        """测试处理器初始化"""
        from app.bot.handler import MessageHandler

        handler = MessageHandler()
        assert handler is not None
        assert handler.command_parser is not None
        assert handler.feishu_client is not None

    def test_handle_url_challenge(self):
        """测试 URL 挑战处理"""
        from app.bot.handler import MessageHandler

        handler = MessageHandler()
        result = handler.handle_url_challenge("test_challenge")
        assert result == "test_challenge"

    def test_handle_event_missing_event(self):
        """测试缺少 event 字段的事件"""
        from app.bot.handler import MessageHandler

        handler = MessageHandler()
        success, message = handler.handle_event({})
        assert success is False
        assert message == "Invalid event data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
