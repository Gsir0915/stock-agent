# -*- coding: utf-8 -*-
"""
股票分析应用入口 (CLI)
使用 argparse 解析命令行参数，编排分析流程
"""

import argparse
import os
import sys
import io
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from .config import Config, get_config
from .utils.logger import setup_logger, get_logger
from .utils.stock_names import StockNameService
from .core.analyzer import StockAnalyzer, AnalysisResult
from .services.report import ReportService
from .services.notification import send_report_to_feishu
from .exceptions import StockAgentError


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="📊 股票投资分析报告生成器 - 基于分层架构的重构版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析贵州茅台
  python -m app.main 600519

  # 分析并推送到飞书
  python -m app.main 600519 --feishu

  # 使用缓存数据，不下载新数据
  python -m app.main 600519 --no-download

  # 指定数据和报告目录
  python -m app.main 600519 --data-dir data --output-dir reports
        """
    )

    parser.add_argument(
        "code",
        help="股票代码，如 600519"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="数据保存目录（默认：data）"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="报告输出目录（默认：reports）"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="跳过数据下载，使用本地缓存"
    )
    parser.add_argument(
        "--feishu",
        action="store_true",
        help="发送报告摘要到飞书"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="不使用 AI 进行新闻情绪分析"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认：INFO）"
    )

    return parser


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("📊 股票投资分析报告生成器 v2.0")
    print("基于分层架构重构 | 数据层 -> 业务层 -> 服务层 -> 表现层")
    print("=" * 70)


def print_analysis_result(
    code: str,
    name: str,
    result: AnalysisResult
):
    """打印分析结果"""
    print(f"\n{'=' * 70}")
    print(f"分析结果：{name} ({code})")
    print(f"{'=' * 70}")

    # 技术分析结果
    print(f"\n📊 技术分析:")
    if result.technical_success:
        ind = result.technical_indicators
        print(f"  收盘价：{ind.get('close', 0):.2f}")
        print(f"  RSI: {ind.get('rsi', 0):.2f}")
        print(f"  技术信号：{len(result.technical_signals)} 条")

        # 打印重要信号
        for sig in result.technical_signals[:3]:
            print(f"    - {sig.get('signal', '')}: {sig.get('desc', '')}")
    else:
        error = result.errors.get('technical', '未知错误')
        print(f"  ❌ 失败：{error}")

    # 基本面分析结果
    print(f"\n💰 基本面分析:")
    if result.fundamental_success:
        ind = result.fundamental_indicators
        pe_str = f"{ind.get('pe', 0):.2f}" if ind.get('pe') else "无数据"
        pb_str = f"{ind.get('pb', 0):.2f}" if ind.get('pb') else "无数据"
        growth_str = (
            f"{ind.get('profit_growth', 0):.2f}%"
            if ind.get('profit_growth') else "无数据"
        )
        print(f"  PE: {pe_str}")
        print(f"  PB: {pb_str}")
        print(f"  净利润增长率：{growth_str}")
        print(f"  价值评分：{result.fundamental_score}/100")
        print(f"  评级：{result.fundamental_rating}")
    else:
        error = result.errors.get('fundamental', '未知错误')
        print(f"  ❌ 失败：{error}")

    # 情绪分析结果
    print(f"\n📰 新闻情绪分析:")
    if result.sentiment_success:
        summary = result.sentiment_summary
        print(f"  正面：{summary.get('positive_count', 0)} 条")
        print(f"  负面：{summary.get('negative_count', 0)} 条")
        print(f"  中性：{summary.get('neutral_count', 0)} 条")
        print(f"  整体判断：{summary.get('overall', 'N/A')}")
    else:
        error = result.errors.get('sentiment', '未知错误')
        print(f"  ❌ 失败：{error}")

    print(f"\n{'=' * 70}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()

    # 设置日志
    logger = setup_logger(
        name="stock_agent",
        level=args.log_level
    )

    # 打印横幅
    print_banner()

    # 清理股票代码
    code = args.code.replace("sh", "").replace("sz", "").strip()
    stock_name = StockNameService.get_name(code)

    print(f"\n股票代码：{code}")
    print(f"股票名称：{stock_name}")
    print(f"数据目录：{args.data_dir}")
    print(f"报告目录：{args.output_dir}")

    # 获取配置
    config = get_config()

    # 创建分析引擎
    analyzer = StockAnalyzer(
        data_dir=args.data_dir,
        use_ai=not args.no_ai and config.has_ai_api,
        api_key=config.anthropic_api_key
    )

    # 执行分析
    print(f"\n{'=' * 70}")
    print("开始分析...")
    print(f"{'=' * 70}")

    result = analyzer.analyze(
        code=code,
        name=stock_name,
        download=not args.no_download
    )

    # 打印结果
    print_analysis_result(code, stock_name, result)

    # 生成报告
    print(f"\n生成报告...")
    print(f"{'=' * 70}")

    report_service = ReportService(output_dir=args.output_dir)

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

    try:
        report_path = report_service.generate_markdown_report(
            code=code,
            stock_name=stock_name,
            technical=technical_data,
            fundamental=fundamental_data,
            news=news_data
        )

        print(f"\n✅ 报告生成成功！")
        print(f"📄 报告路径：{report_path}")

    except StockAgentError as e:
        print(f"\n❌ 报告生成失败：{e.message}")
        report_path = None

    # 发送飞书通知
    if args.feishu:
        print(f"\n发送飞书通知...")

        webhook_url = config.feishu_webhook_url
        if webhook_url:
            # 准备通知内容
            summary = {}
            if result.technical_success:
                ind = result.technical_indicators
                summary['收盘价'] = f"{ind.get('close', 0):.2f}"
                summary['RSI'] = f"{ind.get('rsi', 0):.2f}"

            if result.fundamental_success:
                summary['价值评分'] = f"{result.fundamental_score}/100"
                summary['评级'] = result.fundamental_rating

            if result.sentiment_success:
                s = result.sentiment_summary
                summary['新闻情绪'] = (
                    f"{s.get('positive_count', 0)}正/"
                    f"{s.get('negative_count', 0)}负/"
                    f"{s.get('neutral_count', 0)}中"
                )

            content = {
                'summary': summary,
                'technical': technical_data,
                'fundamental': fundamental_data
            }

            success = send_report_to_feishu(
                webhook_url=webhook_url,
                code=code,
                stock_name=stock_name,
                technical=technical_data,
                fundamental=fundamental_data,
                news=news_data,
                report_path=report_path or "N/A"
            )

            if success:
                print("✅ 飞书推送成功！")
            else:
                print("❌ 飞书推送失败")
        else:
            print("⚠️ 未配置 FEISHU_WEBHOOK_URL 环境变量，跳过推送")

    # 完成
    print(f"\n{'=' * 70}")
    print("分析完成！")
    print(f"{'=' * 70}")

    # 返回状态码
    if result.success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
