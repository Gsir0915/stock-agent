# -*- coding: utf-8 -*-
"""
报告生成服务
生成 Markdown 格式的投资分析报告
"""

import os
import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..exceptions import ReportGenerationError
from ..utils.logger import get_logger

logger = get_logger("services.report")


class ReportService:
    """报告生成服务"""

    def __init__(self, output_dir: str = "reports"):
        """
        初始化报告服务

        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown_report(
        self,
        code: str,
        stock_name: str,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> str:
        """
        生成 Markdown 格式的投资分析报告

        Args:
            code: 股票代码
            stock_name: 股票名称
            technical: 技术分析结果
            fundamental: 基本面分析结果
            news: 新闻分析结果
            output_dir: 输出目录（可选）

        Returns:
            报告文件路径

        Raises:
            ReportGenerationError: 生成失败时抛出
        """
        try:
            # 确定输出目录
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self.output_dir

            # 生成报告文件名
            date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{code}_{stock_name}_{date_str}.md"
            report_path = output_path / report_filename

            # 构建报告内容
            report_lines = self._build_report_content(
                code, stock_name, technical, fundamental, news
            )

            # 写入文件
            content = "\n".join(report_lines)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"报告生成成功：{report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"报告生成失败：{e}")
            raise ReportGenerationError(f"报告生成失败：{str(e)}")

    def _build_report_content(
        self,
        code: str,
        stock_name: str,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any]
    ) -> list:
        """构建报告内容"""
        lines = []

        # 标题
        lines.extend(self._build_header(code, stock_name))

        # 核心指标概览
        lines.extend(self._build_summary_section(technical, fundamental, news))

        # 技术分析
        lines.extend(self._build_technical_section(technical))

        # 基本面分析
        lines.extend(self._build_fundamental_section(fundamental))

        # 新闻情绪分析
        lines.extend(self._build_news_section(news))

        # 综合建议
        lines.extend(self._build_recommendation_section(
            technical, fundamental, news
        ))

        # 底部信息
        lines.extend(self._build_footer())

        return lines

    def _build_header(self, code: str, stock_name: str) -> list:
        """构建报告头部"""
        lines = [
            "# 📊 股票投资分析报告",
            "",
            f"**股票**：{stock_name} ({code})",
            f"**报告时间**：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        return lines

    def _build_summary_section(
        self,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any]
    ) -> list:
        """构建核心指标概览"""
        lines = [
            "## 📈 核心指标概览",
            "",
            "| 指标 | 数值 | 状态 |",
            "|------|------|------|"
        ]

        # 技术面状态
        tech_status = "✅" if technical.get('success') else "❌"
        tech_text = "正常" if technical.get('success') else "失败"
        lines.append(f"| 技术分析 | {tech_status} | {tech_text} |")

        # 基本面评分
        fund_score = fundamental.get('score', 0)
        fund_emoji = self._get_fund_emoji(fund_score)
        fund_rating = fundamental.get('rating', 'N/A')
        lines.append(f"| 基本面评分 | {fund_score}/100 | {fund_emoji} {fund_rating} |")

        # 新闻情绪
        news_summary = news.get('summary', {})
        news_positive = news_summary.get('positive_count', 0)
        news_negative = news_summary.get('negative_count', 0)
        news_neutral = news_summary.get('neutral_count', 0)
        news_emoji = self._get_news_emoji(news_positive, news_negative)
        news_overall = news_summary.get('overall', '未知')
        lines.append(
            f"| 新闻情绪 | {news_positive}正/{news_negative}负/{news_neutral}中 | "
            f"{news_emoji} {news_overall} |"
        )

        lines.extend(["", "---", ""])
        return lines

    def _build_technical_section(self, technical: Dict[str, Any]) -> list:
        """构建技术分析部分"""
        lines = [
            "## 📊 技术分析",
            ""
        ]

        if not technical.get('success'):
            error = technical.get('error', '未知错误')
            lines.append(f"❌ 技术分析失败：{error}")
            lines.extend(["", "---", ""])
            return lines

        ind = technical.get('indicators', {})

        # 技术指标表格
        lines.extend([
            "### 技术指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|"
        ])

        lines.append(f"| 收盘价 | {ind.get('close', 0):.2f} |")
        lines.append(f"| 5 日均线 (MA5) | {ind.get('ma5', 0):.2f} |")
        lines.append(f"| 10 日均线 (MA10) | {ind.get('ma10', 0):.2f} |")
        lines.append(f"| 20 日均线 (MA20) | {ind.get('ma20', 0):.2f} |")
        lines.append(f"| 60 日均线 (MA60) | {ind.get('ma60', 0):.2f} |")
        lines.append(f"| DIF | {ind.get('dif', 0):.4f} |")
        lines.append(f"| DEA | {ind.get('dea', 0):.4f} |")
        lines.append(f"| MACD | {ind.get('macd', 0):.4f} |")
        lines.append(f"| RSI(14) | {ind.get('rsi', 0):.2f} |")
        lines.append(f"| 数据日期 | {ind.get('date', 'N/A')} |")
        lines.append("")

        # 技术信号
        signals = technical.get('signals', [])
        if signals:
            lines.extend([
                "### 技术信号",
                ""
            ])
            for sig in signals:
                lines.append(
                    f"- **{sig['type']}**: {sig['signal']} - {sig.get('desc', '')}"
                )
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _build_fundamental_section(self, fundamental: Dict[str, Any]) -> list:
        """构建基本面分析部分"""
        lines = [
            "## 💰 基本面分析",
            ""
        ]

        if not fundamental.get('success'):
            error = fundamental.get('error', '未知错误')
            lines.append(f"❌ 基本面分析失败：{error}")
            lines.extend(["", "---", ""])
            return lines

        ind = fundamental.get('indicators', {})

        # 估值指标表格
        lines.extend([
            "### 估值指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|"
        ])

        pe_str = f"{ind.get('pe', 0):.2f}" if ind.get('pe') else "无数据"
        pb_str = f"{ind.get('pb', 0):.2f}" if ind.get('pb') else "无数据"
        growth_str = (
            f"{ind.get('profit_growth', 0):.2f}%"
            if ind.get('profit_growth') else "无数据"
        )

        lines.append(f"| 市盈率 (PE) | {pe_str} |")
        lines.append(f"| 市净率 (PB) | {pb_str} |")
        lines.append(f"| 净利润增长率 | {growth_str} |")
        lines.append("")

        # 评分详情
        lines.extend([
            "### 价值评估",
            "",
            f"**综合评分**: {fundamental.get('score', 0)}/100",
            f"**评级**: {fundamental.get('rating', 'N/A')}",
            ""
        ])

        details = fundamental.get('details', [])
        if details:
            lines.extend([
                "| 项目 | 详情 |",
                "|------|------|"
            ])
            for d in details:
                lines.append(f"| - | {d} |")
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _build_news_section(self, news: Dict[str, Any]) -> list:
        """构建新闻情绪分析部分"""
        lines = [
            "## 📰 新闻情绪分析",
            ""
        ]

        if not news.get('success'):
            error = news.get('error', '未知错误')
            lines.append(f"❌ 新闻分析失败：{error}")
            lines.extend(["", "---", ""])
            return lines

        summary = news.get('summary', {})

        # 情绪汇总
        lines.extend([
            "### 情绪汇总",
            "",
            f"- 🟢 正面新闻：{summary.get('positive_count', 0)} 条",
            f"- 🔴 负面新闻：{summary.get('negative_count', 0)} 条",
            f"- ⚪ 中性新闻：{summary.get('neutral_count', 0)} 条",
            f"- **整体判断**: {summary.get('overall', '未知')}",
            ""
        ])

        # 新闻列表
        lines.extend([
            "### 新闻列表",
            ""
        ])

        news_list = news.get('news', [])
        for i, item in enumerate(news_list, 1):
            emoji = {
                "正面": "🟢",
                "负面": "🔴",
                "中性": "⚪"
            }.get(item.get('emotion'), "⚪")

            publish_time = item.get('publish_time', '')
            time_str = f" [{publish_time}]" if publish_time else ""

            lines.append(
                f"{i}. {emoji} {item.get('title', 'N/A')}{time_str}"
            )
            if item.get('url'):
                lines.append(f"   - [📎 查看原文]({item.get('url')})")
            lines.append(f"   - 情绪：{item.get('emotion')} - {item.get('reason', 'N/A')}")
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _build_recommendation_section(
        self,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any]
    ) -> list:
        """构建综合建议部分"""
        lines = [
            "## 💡 综合建议",
            "",
        ]

        recommendations = []

        # 技术面
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

        # 基本面
        fund_score = fundamental.get('score', 0)
        if fund_score >= 60:
            recommendations.append("💰 基本面具有投资价值")
        elif fund_score >= 40:
            recommendations.append("💰 基本面估值中等")
        else:
            recommendations.append("💰 基本面估值偏高")

        # 新闻面
        news_summary = news.get('summary', {})
        news_positive = news_summary.get('positive_count', 0)
        news_negative = news_summary.get('negative_count', 0)

        if news_positive > news_negative:
            recommendations.append("📰 新闻情绪偏正面")
        elif news_negative > news_positive:
            recommendations.append("📰 新闻情绪偏负面")
        else:
            recommendations.append("📰 新闻情绪中性")

        lines.append(" | ".join(recommendations))
        lines.append("")
        lines.append(
            "> ⚠️ **免责声明**：本报告仅供参考，不构成投资建议。"
            "投资有风险，入市需谨慎。"
        )
        lines.extend(["", "---", ""])

        return lines

    def _build_footer(self) -> list:
        """构建报告底部"""
        lines = [
            "",
            "*报告由 Stock Analysis Bot 自动生成*"
        ]
        return lines

    def _get_fund_emoji(self, score: int) -> str:
        """根据基本面评分获取 emoji"""
        if score >= 80:
            return "💎"
        elif score >= 60:
            return "✅"
        elif score >= 40:
            return "⚠️"
        else:
            return "❌"

    def _get_news_emoji(
        self,
        positive: int,
        negative: int
    ) -> str:
        """根据新闻情绪获取 emoji"""
        if positive > negative:
            return "🟢"
        elif negative > positive:
            return "🔴"
        else:
            return "⚪"
