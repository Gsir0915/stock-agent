# -*- coding: utf-8 -*-
"""
通知服务模块
使用策略模式支持多渠道通知（飞书、邮件、微信等）
"""

import os
import datetime
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from .exceptions import NotificationError
from ..utils.logger import get_logger

logger = get_logger("services.notification")


class NotificationChannel(ABC):
    """通知渠道基类"""

    @abstractmethod
    def send(self, title: str, content: Dict[str, Any]) -> bool:
        """
        发送通知

        Args:
            title: 通知标题
            content: 通知内容

        Returns:
            True 如果发送成功
        """
        pass


class FeishuWebhookChannel(NotificationChannel):
    """飞书 Webhook 通知渠道"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知渠道

        Args:
            webhook_url: 飞书 Webhook URL
        """
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")

    def send(self, title: str, content: Dict[str, Any]) -> bool:
        """发送飞书通知"""
        if not self.webhook_url:
            logger.warning("未配置飞书 Webhook URL")
            return False

        try:
            import requests

            # 构建交互式卡片消息
            card_data = self._build_card(title, content)

            payload = {
                "msg_type": "interactive",
                "card": card_data
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    logger.info("飞书推送成功")
                    return True

            logger.warning(f"飞书推送失败：{response.text}")
            return False

        except Exception as e:
            logger.error(f"飞书推送异常：{e}")
            return False

    def _build_card(self, title: str, content: Dict[str, Any]) -> dict:
        """构建飞书卡片"""
        elements = []

        # 标题
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{title}**"
            }
        })

        # 核心指标概览
        if 'summary' in content:
            summary = content['summary']
            summary_text = "\n".join([
                f"• {k}: {v}" for k, v in summary.items()
            ])
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**核心指标**:\n{summary_text}"
                }
            })

        # 技术指标
        if 'technical' in content:
            tech = content['technical']
            if tech.get('success'):
                ind = tech.get('indicators', {})
                tech_text = (
                    f"💰 收盘价：**{ind.get('close', 0):.2f}**\n"
                    f"📉 MA5: {ind.get('ma5', 0):.2f} | MA20: {ind.get('ma20', 0):.2f}\n"
                    f"📊 MACD: DIF={ind.get('dif', 0):.4f} DEA={ind.get('dea', 0):.4f}\n"
                    f"💪 RSI(14): {ind.get('rsi', 0):.2f}"
                )
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**技术指标**:\n{tech_text}"
                    }
                })

        # 基本面
        if 'fundamental' in content:
            fund = content['fundamental']
            if fund.get('success'):
                fund_text = (
                    f"价值评分：**{fund.get('score', 0)}/100**\n"
                    f"评级：{fund.get('rating', 'N/A')}"
                )
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**基本面**:\n{fund_text}"
                    }
                })

        # 底部信息
        elements.append({
            "tag": "hr"
        })
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"⏰ 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
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
                    "content": title
                }
            },
            "elements": elements
        }


class NotificationService:
    """通知服务"""

    def __init__(self):
        """初始化通知服务"""
        self.channels: Dict[str, NotificationChannel] = {}

        # 注册默认渠道
        feishu_channel = FeishuWebhookChannel()
        if feishu_channel.webhook_url:
            self.channels['feishu'] = feishu_channel

    def register_channel(
        self,
        name: str,
        channel: NotificationChannel
    ):
        """
        注册通知渠道

        Args:
            name: 渠道名称
            channel: 渠道实例
        """
        self.channels[name] = channel
        logger.info(f"注册通知渠道：{name}")

    def send(
        self,
        title: str,
        content: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        发送通知

        Args:
            title: 通知标题
            content: 通知内容
            channels: 指定渠道列表，如果为 None 则使用所有可用渠道

        Returns:
            各渠道发送结果
        """
        if channels is None:
            channels = list(self.channels.keys())

        results = {}

        for channel_name in channels:
            channel = self.channels.get(channel_name)

            if not channel:
                logger.warning(f"通知渠道不存在：{channel_name}")
                results[channel_name] = False
                continue

            try:
                success = channel.send(title, content)
                results[channel_name] = success
            except Exception as e:
                logger.error(f"{channel_name} 发送失败：{e}")
                results[channel_name] = False

        return results

    def send_feishu(
        self,
        title: str,
        content: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        发送飞书通知（便捷方法）

        Args:
            title: 通知标题
            content: 通知内容
            webhook_url: 指定的 Webhook URL

        Returns:
            是否发送成功
        """
        if webhook_url:
            channel = FeishuWebhookChannel(webhook_url)
            return channel.send(title, content)

        return self.send(title, content, ['feishu']).get('feishu', False)


def send_report_to_feishu(
    webhook_url: str,
    code: str,
    stock_name: str,
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
    news: Dict[str, Any],
    report_path: str
) -> bool:
    """
    发送投资分析报告到飞书（便捷函数）

    Args:
        webhook_url: 飞书 Webhook URL
        code: 股票代码
        stock_name: 股票名称
        technical: 技术分析结果
        fundamental: 基本面分析结果
        news: 新闻分析结果
        report_path: 报告文件路径

    Returns:
        是否发送成功
    """
    # 构建消息内容
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
                f"📄 报告文件：`{os.path.basename(report_path)}`\n"
                f"⏰ 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⚠️ *免责声明：报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*"
            )
        }
    })

    # 发送消息
    payload = {
        "msg_type": "interactive",
        "card": {
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
    }

    try:
        import requests

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                logger.info("飞书推送成功")
                return True

        logger.warning(f"飞书推送失败：{response.text}")
        return False

    except Exception as e:
        logger.error(f"飞书推送异常：{e}")
        return False
