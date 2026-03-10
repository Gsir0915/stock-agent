# -*- coding: utf-8 -*-
"""
飞书消息处理器
解析飞书推送的事件消息，协调分析服务和回复
"""

import json
from typing import Optional, Dict, Any, Tuple
from .commands import CommandParser
from .feishu_client import FeishuClient
from ..core.analyzer import StockAnalyzer, AnalysisResult
from ..services.report import ReportService
from ..utils.logger import get_logger
from ..exceptions import StockAgentError

logger = get_logger("bot.handler")


class MessageHandler:
    """飞书消息处理器"""

    def __init__(self):
        """初始化消息处理器"""
        self.command_parser = CommandParser()
        self.feishu_client = FeishuClient()
        self.analyzer = None
        self.report_service = None

    def _get_analyzer(self) -> StockAnalyzer:
        """获取分析器实例（懒加载）"""
        if self.analyzer is None:
            from ..config import get_config
            config = get_config()
            self.analyzer = StockAnalyzer(
                data_dir=config.data_dir,
                use_ai=config.has_ai_api,
                api_key=config.anthropic_api_key
            )
        return self.analyzer

    def _get_report_service(self) -> ReportService:
        """获取报告服务实例（懒加载）"""
        if self.report_service is None:
            from ..config import get_config
            config = get_config()
            self.report_service = ReportService(output_dir=config.reports_dir)
        return self.report_service

    def handle_event(self, event_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        处理飞书事件

        Args:
            event_data: 飞书推送的事件数据

        Returns:
            (success, message) 元组
            - success: 是否处理成功
            - message: 结果消息
        """
        logger.info(f"收到飞书事件：{event_data.get('header', {}).get('event_type', 'unknown')}")

        # 解析事件
        event = event_data.get('event', {})
        if not event:
            logger.warning("事件数据中缺少 event 字段")
            return False, "Invalid event data"

        # 提取消息信息
        message = event.get('message', {})
        if not message:
            logger.warning("事件数据中缺少 message 字段")
            return False, "Invalid message data"

        # 解析消息内容
        content_str = message.get('content', '{}')
        try:
            content = json.loads(content_str)
        except json.JSONDecodeError:
            logger.error(f"消息内容解析失败：{content_str}")
            return False, "Failed to parse message content"

        text = content.get('text', '')
        chat_id = message.get('chat_id', '')
        message_id = message.get('message_id', '')

        # 提取发送者信息
        sender = event.get('sender', {})
        sender_id = sender.get('sender_id', {})
        open_id = sender_id.get('open_id', 'unknown')

        logger.info(f"收到来自 {open_id} 的消息：{text} (chat_id: {chat_id})")

        # 检查是否是@机器人的消息
        mentions = message.get('mentions', [])
        if not mentions:
            logger.debug("消息未@任何人，跳过")
            return True, "Not a mention message"

        # 解析用户命令
        stock_code, command = self.command_parser.parse_message(text)

        if command == 'help':
            # 发送帮助消息
            help_text = self.command_parser.get_help_message()
            success = self.feishu_client.send_text_message(
                chat_id=chat_id,
                text=help_text,
                reply_id=message_id
            )
            return success, "Help message sent" if success else "Failed to send help"

        if not stock_code:
            # 无法识别股票代码
            error_text = (
                "❌ 无法识别股票代码\n\n"
                "请尝试以下格式：\n"
                "• `@bot 600519`\n"
                "• `@bot 分析 600519`\n"
                "• `@bot 贵州茅台`\n\n"
                "发送 `@bot 帮助` 查看更多用法"
            )
            success = self.feishu_client.send_text_message(
                chat_id=chat_id,
                text=error_text,
                reply_id=message_id
            )
            return success, "Stock code not recognized"

        # 执行股票分析
        return self._execute_analysis(stock_code, chat_id, message_id, open_id)

    def _execute_analysis(
        self,
        stock_code: str,
        chat_id: str,
        reply_to_message_id: str,
        user_open_id: str
    ) -> Tuple[bool, str]:
        """
        执行股票分析并发送结果

        Args:
            stock_code: 股票代码
            chat_id: 群聊 ID
            reply_to_message_id: 回复的消息 ID
            user_open_id: 用户 open_id

        Returns:
            (success, message) 元组
        """
        from ..utils.stock_names import StockNameService

        # 获取股票名称
        stock_name = StockNameService.get_name(stock_code)

        logger.info(f"开始分析股票：{stock_name} ({stock_code})")

        # 发送"正在分析"提示
        analyzing_text = f"🤖 正在分析 **{stock_name} ({stock_code})**，请稍候..."
        self.feishu_client.send_text_message(
            chat_id=chat_id,
            text=analyzing_text,
            reply_id=reply_to_message_id
        )

        try:
            # 执行分析
            analyzer = self._get_analyzer()
            result = analyzer.analyze(
                code=stock_code,
                name=stock_name,
                download=True
            )

            # 准备报告数据
            technical_data = {
                'success': result.technical_success,
                'indicators': result.technical_indicators,
                'signals': result.technical_signals,
                'error': result.errors.get('technical', '')
            }

            fundamental_data = {
                'success': result.fundamental_success,
                'indicators': result.fundamental_indicators,
                'score': result.fundamental_score,
                'rating': result.fundamental_rating,
                'details': result.fundamental_details
            }

            news_data = {
                'success': result.sentiment_success,
                'news': result.sentiment_news,
                'summary': result.sentiment_summary,
                'error': result.errors.get('sentiment', '')
            }

            # 生成 Markdown 报告（保存到本地）
            try:
                report_service = self._get_report_service()
                report_path = report_service.generate_markdown_report(
                    code=stock_code,
                    stock_name=stock_name,
                    technical=technical_data,
                    fundamental=fundamental_data,
                    news=news_data
                )
                logger.info(f"报告已生成：{report_path}")
            except StockAgentError as e:
                logger.error(f"报告生成失败：{e.message}")
                report_path = None

            # 构建并发送卡片消息
            card_data = FeishuClient.build_analysis_card(
                code=stock_code,
                stock_name=stock_name,
                technical=technical_data,
                fundamental=fundamental_data,
                news=news_data
            )

            # 如果分析失败，添加错误提示
            if not result.success:
                error_summary = []
                if result.errors.get('technical'):
                    error_summary.append(f"技术分析：{result.errors['technical']}")
                if result.errors.get('fundamental'):
                    error_summary.append(f"基本面分析：{result.errors['fundamental']}")
                if result.errors.get('sentiment'):
                    error_summary.append(f"情绪分析：{result.errors['sentiment']}")

                # 在卡片元素开头添加错误提示
                error_text = "⚠️ **部分分析失败**: " + "；".join(error_summary) + "\n"
                card_data['elements'].insert(0, {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": error_text
                    }
                })

            # 发送卡片
            success = self.feishu_client.send_interactive_card(
                chat_id=chat_id,
                card_data=card_data,
                reply_id=reply_to_message_id
            )

            if success:
                logger.info(f"分析结果已发送到群聊：{chat_id}")
                return True, "Analysis completed and sent"
            else:
                logger.error("发送卡片消息失败")
                return False, "Failed to send card message"

        except StockAgentError as e:
            logger.error(f"分析过程出错：{e.message}")
            error_text = (
                f"❌ 分析失败\n\n"
                f"错误信息：{e.message}\n\n"
                f"请稍后重试或联系管理员"
            )
            self.feishu_client.send_text_message(
                chat_id=chat_id,
                text=error_text,
                reply_id=reply_to_message_id
            )
            return False, f"Analysis error: {e.message}"

        except Exception as e:
            logger.exception(f"未预期的错误：{e}")
            error_text = (
                f"❌ 系统错误\n\n"
                f"请稍后重试或联系管理员"
            )
            self.feishu_client.send_text_message(
                chat_id=chat_id,
                text=error_text,
                reply_id=reply_to_message_id
            )
            return False, f"Unexpected error: {e}"

    def handle_url_challenge(self, challenge: str) -> str:
        """
        处理飞书 URL 验证挑战

        Args:
            challenge: 飞书发送的挑战字符串

        Returns:
            挑战字符串（直接返回）
        """
        logger.info("收到 URL 验证挑战")
        return challenge
