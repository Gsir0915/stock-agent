# -*- coding: utf-8 -*-
"""
飞书 API 客户端
使用飞书开放平台 API 发送消息到群聊
需要配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET
"""

import time
import hashlib
import base64
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ..utils.logger import get_logger
from ..exceptions import NotificationError

logger = get_logger("bot.feishu_client")


@dataclass
class TenantAccessToken:
    """飞书 tenant_access_token"""
    token: str
    expire_at: int  # 过期时间戳（秒）


class FeishuClient:
    """飞书 API 客户端"""

    # 飞书 API 基础 URL
    API_BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None
    ):
        """
        初始化飞书客户端

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
        """
        import os
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self._token_cache: Optional[TenantAccessToken] = None

        if not self.app_id or not self.app_secret:
            logger.warning("未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

    def _get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token（带缓存）

        Returns:
            tenant_access_token
        """
        # 检查缓存是否有效
        current_time = int(time.time())
        if self._token_cache and current_time < self._token_cache.expire_at:
            logger.debug("使用缓存的 tenant_access_token")
            return self._token_cache.token

        # 请求新的 token
        logger.info("请求新的 tenant_access_token")
        token = self._request_tenant_access_token()

        # 缓存 token（提前 5 分钟过期）
        self._token_cache = TenantAccessToken(
            token=token,
            expire_at=current_time + 7200 - 300  # 2 小时 - 5 分钟
        )

        return token

    def _request_tenant_access_token(self) -> str:
        """
        请求 tenant_access_token

        Returns:
            tenant_access_token
        """
        import requests

        url = f"{self.API_BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    token = result.get('tenant_access_token')
                    logger.info("成功获取 tenant_access_token")
                    return token

            logger.error(f"获取 tenant_access_token 失败：{response.text}")
            raise NotificationError(
                "获取飞书访问令牌失败",
                details={"status_code": response.status_code, "response": response.text}
            )

        except requests.RequestException as e:
            logger.error(f"请求 tenant_access_token 异常：{e}")
            raise NotificationError(
                "请求飞书访问令牌异常",
                details={"error": str(e)}
            )

    def send_message_to_chat(
        self,
        chat_id: str,
        msg_type: str,
        content: Dict[str, Any],
        reply_id: Optional[str] = None
    ) -> bool:
        """
        发送消息到群聊

        Args:
            chat_id: 群聊 ID
            msg_type: 消息类型（text, interactive, post 等）
            content: 消息内容
            reply_id: 回复的消息 ID（可选）

        Returns:
            True 如果发送成功
        """
        import requests

        url = f"{self.API_BASE_URL}/im/v1/messages"
        params = {
            "chat_id": chat_id,
            "receive_id_type": "chat_id"  # 必需参数：指定 receive_id 的类型
        }

        # 如果是回复消息，需要设置 reply_id
        if reply_id:
            params["reply_id"] = reply_id

        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False)
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_tenant_access_token()}"
        }

        try:
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=headers,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    logger.info(f"消息发送成功到群聊：{chat_id}")
                    return True

            logger.warning(f"消息发送失败：{response.text}")
            return False

        except requests.RequestException as e:
            logger.error(f"发送消息异常：{e}")
            return False

    def send_interactive_card(
        self,
        chat_id: str,
        card_data: Dict[str, Any],
        reply_id: Optional[str] = None
    ) -> bool:
        """
        发送交互式卡片消息到群聊

        Args:
            chat_id: 群聊 ID
            card_data: 卡片数据
            reply_id: 回复的消息 ID（可选）

        Returns:
            True 如果发送成功
        """
        return self.send_message_to_chat(
            chat_id=chat_id,
            msg_type="interactive",
            content=card_data,
            reply_id=reply_id
        )

    def send_text_message(
        self,
        chat_id: str,
        text: str,
        reply_id: Optional[str] = None
    ) -> bool:
        """
        发送文本消息到群聊

        Args:
            chat_id: 群聊 ID
            text: 文本内容
            reply_id: 回复的消息 ID（可选）

        Returns:
            True 如果发送成功
        """
        content = {"text": text}
        return self.send_message_to_chat(
            chat_id=chat_id,
            msg_type="text",
            content=content,
            reply_id=reply_id
        )

    @staticmethod
    def build_analysis_card(
        code: str,
        stock_name: str,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建分析报告卡片

        Args:
            code: 股票代码
            stock_name: 股票名称
            technical: 技术分析结果
            fundamental: 基本面分析结果
            news: 新闻分析结果

        Returns:
            卡片数据
        """
        import datetime
        import os

        elements = []

        # 标题
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📊 股票投资分析报告**\n**股票**: {stock_name} ({code})"
            }
        })

        # 核心指标概览
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "\n**📈 核心指标**"
            }
        })

        # 技术面状态
        tech_status_emoji = "✅" if technical.get('success') else "❌"
        tech_status_text = "正常" if technical.get('success') else "失败"

        # 基本面评分
        fund_score = fundamental.get('score', 0)
        fund_emoji = "💎" if fund_score >= 80 else "✅" if fund_score >= 60 else "⚠️" if fund_score >= 40 else "❌"
        fund_rating = fundamental.get('rating', 'N/A')

        # 新闻情绪
        news_summary = news.get('summary', {})
        news_positive = news_summary.get('positive_count', 0)
        news_negative = news_summary.get('negative_count', 0)
        news_neutral = news_summary.get('neutral_count', 0)
        news_emoji = "🟢" if news_positive > news_negative else "🔴" if news_negative > news_positive else "⚪"
        news_overall = news_summary.get('overall', '未知')

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"技术分析：{tech_status_emoji} {tech_status_text}  |  "
                    f"基本面：{fund_emoji} {fund_score}/100 {fund_rating}  |  "
                    f"新闻：{news_emoji} {news_overall}"
                )
            }
        })

        # 详细技术指标
        if technical.get('success'):
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📊 技术指标**"
                }
            })

            ind = technical.get('indicators', {})
            close_price = ind.get('close', 0)
            ma5 = ind.get('ma5', 0)
            ma20 = ind.get('ma20', 0)
            dif = ind.get('dif', 0)
            dea = ind.get('dea', 0)
            macd = ind.get('macd', 0)
            rsi = ind.get('rsi', 0)

            # 价格与均线关系
            ma_signal = "🟢" if close_price > ma20 else "🔴"
            ma_text = "线上" if close_price > ma20 else "线下"

            rsi_status = (
                " 🟢 超卖" if rsi < 30 else
                " 🔴 超买" if rsi > 70 else
                " ⚪ 中性"
            )

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"💰 收盘价：**{close_price:.2f}** {ma_signal}({ma_text} MA20)\n"
                        f"📉 MA5: {ma5:.2f} | MA20: {ma20:.2f}\n"
                        f"📊 MACD: DIF={dif:.4f} DEA={dea:.4f} MACD={macd:.4f}\n"
                        f"💪 RSI(14): {rsi:.2f}{rsi_status}"
                    )
                }
            })

            # 技术信号列表
            signals = technical.get('signals', [])
            if signals:
                signals_text = "\n".join([
                    f"• {s['signal']} {s.get('desc', '')}"
                    for s in signals
                ])
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**🔔 技术信号**:\n{signals_text}"
                    }
                })

        # 基本面详情
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**💰 基本面分析**"
            }
        })

        if fundamental.get('success'):
            ind = fundamental.get('indicators', {})
            pe = ind.get('pe')
            pb = ind.get('pb')
            profit_growth = ind.get('profit_growth')

            pe_str = f"{pe:.2f}" if pe else "无数据"
            pb_str = f"{pb:.2f}" if pb else "无数据"
            growth_str = f"{profit_growth:.2f}%" if profit_growth else "无数据"

            details = fundamental.get('details', [])
            details_text = "\n".join([f"• {d}" for d in details]) if details else "无详细数据"

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"估值指标:\n"
                        f"• 市盈率 (PE): **{pe_str}**\n"
                        f"• 市净率 (PB): {pb_str}\n"
                        f"• 净利润增长率：{growth_str}\n\n"
                        f"**评分详情**:\n{details_text}"
                    )
                }
            })

        # 新闻情绪
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**📰 新闻情绪**: 🟢{news_positive}正 🔴{news_negative}负 ⚪{news_neutral}中 | "
                    f"判断：{news_overall}"
                )
            }
        })

        # 新闻列表
        news_list = news.get('news', [])
        if news_list:
            news_items = []
            for n in news_list[:5]:
                emoji = '🟢' if n.get('emotion') == '正面' else '🔴' if n.get('emotion') == '负面' else '⚪'
                title = n.get('title', 'N/A')
                publish_time = n.get('publish_time', '')
                url = n.get('url', '')
                time_str = f" {publish_time}" if publish_time else ""
                if url:
                    news_items.append(f"• {emoji} [{title}]({url}){time_str}")
                else:
                    news_items.append(f"• {emoji} {title}{time_str}")
            news_text = "\n".join(news_items)
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**新闻标题**:\n{news_text}"
                }
            })

        # 综合建议
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**💡 综合建议**"
            }
        })

        recommendations = []

        if technical.get('success'):
            signals = technical.get('signals', [])
            bullish = sum(1 for s in signals if '🟢' in s.get('signal', ''))
            bearish = sum(1 for s in signals if '🔴' in s.get('signal', ''))

            if bullish > bearish:
                recommendations.append("📈 技术面偏多")
            elif bearish > bullish:
                recommendations.append("📉 技术面偏空")
            else:
                recommendations.append("📊 技术面中性")

        if fund_score >= 60:
            recommendations.append("💰 基本面具有投资价值")
        elif fund_score >= 40:
            recommendations.append("💰 基本面估值中等")
        else:
            recommendations.append("💰 基本面估值偏高")

        if news_positive > news_negative:
            recommendations.append("📰 新闻情绪偏正面")
        elif news_negative > news_positive:
            recommendations.append("📰 新闻情绪偏负面")
        else:
            recommendations.append("📰 新闻情绪中性")

        rec_text = "\n".join(recommendations)
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": rec_text
            }
        })

        # 底部信息
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"⏰ 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"⚠️ *投资有风险，入市需谨慎*"
                )
            }
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 股票投资分析报告 - {stock_name} ({code})"
                }
            },
            "elements": elements
        }
