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
from typing import List, Optional

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

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
        nargs="?",
        default=None,
        help="股票代码，如 600519（--scan 模式下可不填）"
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

    parser.add_argument(
        "--scan",
        action="store_true",
        help="运行选股扫描模式，使用多因子筛选股票池"
    )

    parser.add_argument(
        "--pool",
        nargs="*",
        default=None,
        help="指定股票代码池，多个代码用空格分隔"
    )

    parser.add_argument(
        "--backtest",
        action="store_true",
        help="更新回测结果并显示统计报告"
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


def run_stock_scan(
    stock_pool: Optional[List[str]] = None,
    data_dir: str = "data"
) -> None:
    """
    运行选股扫描流程

    Args:
        stock_pool: 股票代码池，None 则使用默认池
        data_dir: 数据目录
    """
    from agents.stock_selector.factors import (
        QualityFactor,
        MomentumFactor,
        DividendFactor,
    )
    from app.data.downloader import DataDownloader
    from app.data.repository import DataRepository
    from app.utils.stock_names import StockNameService

    # 设置日志
    logger = get_logger("stock_selector")

    # 默认股票池（复用海龟选股器的股票池）
    if stock_pool is None:
        stock_pool = [
            "600519", "000858", "000568", "600809", "002304",  # 白酒
            "601318", "600036", "601166",  # 金融
            "002415", "300750", "600030",  # 科技
            "600276", "000538", "300122",  # 医药
            "600585", "601088", "600900",  # 周期
        ]

    print(f"\n{'='*70}")
    print("🔍 Stock Selector - 多因子选股扫描")
    print(f"{'='*70}")
    print(f"扫描股票数量：{len(stock_pool)}")
    print(f"数据目录：{data_dir}")
    print(f"{'='*70}\n")

    # 初始化服务
    downloader = DataDownloader()
    repository = DataRepository(data_dir)

    # 批量获取股票名称（从实时行情数据）
    try:
        import akshare as ak
        df_spot = ak.stock_zh_a_spot_em()
        if df_spot is not None and len(df_spot) > 0:
            count = 0
            for _, row in df_spot.iterrows():
                code = str(row.get("代码", ""))
                name = row.get("名称", "")
                if code and name and name != "-":
                    StockNameService.add_name(code, name)
                    count += 1
            print(f"已加载 {count} 只股票名称映射")
    except Exception as e:
        print(f"⚠️  加载股票名称失败：{e}（将使用代码显示）")

    # 初始化因子
    quality_factor = QualityFactor()
    momentum_factor = MomentumFactor()
    dividend_factor = DividendFactor()

    # 初始化回测日志
    from agents.stock_selector.backtest_logger import get_backtest_logger
    logger = get_backtest_logger()

    results = []

    for code in stock_pool:
        # 先获取名称，如果获取不到后面再尝试从基本面数据中获取
        name = StockNameService.get_name(code)

        try:
            # 获取数据
            df = repository.load_stock_data(code)
            if df is None or len(df) < 60:
                # 下载数据
                try:
                    df = downloader.download_stock_history(code)
                    repository.save_stock_data(code, df)
                except Exception as e:
                    results.append({
                        "code": code,
                        "name": name,
                        "quality_score": 0.0,
                        "momentum_score": 0.0,
                        "dividend_score": 0.0,
                        "total_score": 0.0,
                        "error": f"数据获取失败：{e}"
                    })
                    continue

            if df is None or len(df) < 60:
                results.append({
                    "code": code,
                    "name": name,
                    "quality_score": 0.0,
                    "momentum_score": 0.0,
                    "dividend_score": 0.0,
                    "total_score": 0.0,
                    "error": "数据量不足"
                })
                continue

            # 获取基本面数据（用于质量因子和股息因子）
            fundamentals = downloader.get_fundamentals(code)

            # 如果之前没有获取到名称，尝试从基本面数据中获取
            if not name and fundamentals:
                name = fundamentals.get("name", code)

            # 如果还是没有名称，尝试从实时行情获取（单只股票）
            if not name or name == code:
                try:
                    import akshare as ak
                    df_spot = ak.stock_zh_a_spot_em()
                    if df_spot is not None and len(df_spot) > 0:
                        stock_data = df_spot[df_spot["代码"] == code]
                        if len(stock_data) > 0:
                            name = stock_data.iloc[0]["名称"]
                            if name and name != "-":
                                StockNameService.add_name(code, name)
                except Exception:
                    pass  # 获取失败继续使用代码

            # 计算动量因子所需数据
            latest = df.iloc[-1]
            current_price = float(latest["收盘"])
            current_volume = float(latest.get("成交量", 0))

            # 计算 20 日高低点和均量
            high_20 = float(df["收盘"].tail(20).max())
            low_20 = float(df["收盘"].tail(20).min())
            avg_volume_20 = float(df["成交量"].tail(20).mean())

            momentum_data = {
                "current_price": current_price,
                "high_20": high_20,
                "low_20": low_20,
                "current_volume": current_volume,
                "avg_volume_20": avg_volume_20,
            }

            # 获取基本面数据（用于质量因子和股息因子）
            fundamentals = downloader.get_fundamentals(code)

            # 质量因子数据
            # 注意：akshare 可能不返回 FCF 数据，当 FCF 缺失时主要依赖增长率评分
            profit_growth = fundamentals.get("profit_growth", 0) if fundamentals else 0
            quality_data = {
                "fcf": fundamentals.get("fcf", 1) if fundamentals else 1,
                "net_profit": fundamentals.get("net_profit", 1) if fundamentals else 1,
                "net_profit_growth": profit_growth,
            }

            # 股息因子数据
            # 使用默认值，因为 akshare 可能不返回这些数据
            dividend_data = {
                "dividend_yield": fundamentals.get("dividend_yield", 2.5) if fundamentals else 2.5,
                "consecutive_years": fundamentals.get("consecutive_years", 3) if fundamentals else 3,
                "payout_ratio": fundamentals.get("payout_ratio", 40) if fundamentals else 40,
            }

            # 运行因子
            quality_score = quality_factor.run(quality_data)
            momentum_score = momentum_factor.run(momentum_data)
            dividend_score = dividend_factor.run(dividend_data)

            # 综合得分（等权重）
            total_score = (quality_score + momentum_score + dividend_score) / 3

            # 记录到回测日志
            logger.log_selection(
                stock_code=code,
                stock_name=name,
                entry_price=current_price,
                quality_score=quality_score,
                momentum_score=momentum_score,
                dividend_score=dividend_score,
                total_score=total_score,
                ranks={
                    "total": len(results) + 1
                }
            )

            results.append({
                "code": code,
                "name": name,
                "quality_score": quality_score,
                "momentum_score": momentum_score,
                "dividend_score": dividend_score,
                "total_score": total_score,
                "error": None
            })

        except Exception as e:
            results.append({
                "code": code,
                "name": name,
                "quality_score": 0.0,
                "momentum_score": 0.0,
                "dividend_score": 0.0,
                "total_score": 0.0,
                "error": str(e)
            })

    # 按总分排序
    results.sort(key=lambda x: x["total_score"], reverse=True)

    # 打印 Markdown 表格
    print("# Stock Selector 扫描结果\n")
    print(f"扫描时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("## 综合评分排名\n")
    print("| 排名 | 代码 | 名称 | 质量因子 | 动量因子 | 股息因子 | 综合得分 |")
    print("|------|------|------|----------|----------|----------|----------|")

    for i, r in enumerate(results, 1):
        if r["error"] is None:
            print(
                f"| {i} | {r['code']} | {r['name']} | "
                f"{r['quality_score']:.2f} | {r['momentum_score']:.2f} | "
                f"{r['dividend_score']:.2f} | {r['total_score']:.2f} |"
            )
        else:
            print(f"| {i} | {r['code']} | {r['name']} | - | - | - | ❌ {r['error']} |")

    print("\n## 因子说明\n")
    print("- **质量因子**: 基于 FCF/净利润比率和利润增长率")
    print("- **动量因子**: 基于价格位置 (20 日区间) 和成交量放大程度")
    print("- **股息因子**: 基于股息率、连续分红年数和分红健康度\n")

    # 保存回测日志
    logger.save()

    # 更新并显示回测统计
    print("\n📊 回测统计:")
    logger.update_results()
    logger.print_report()

    print(f"{'='*70}")
    print("扫描完成!")
    print(f"{'='*70}\n")


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

    # 回测模式：更新结果并显示统计
    if args.backtest:
        from agents.stock_selector.backtest_logger import get_backtest_logger
        bt_logger = get_backtest_logger()
        bt_logger.update_results()
        bt_logger.save()
        bt_logger.print_report()
        return 0

    # 扫描模式
    if args.scan:
        stock_pool = args.pool if args.pool else None
        run_stock_scan(stock_pool=stock_pool, data_dir=args.data_dir)
        return 0

    # 普通模式需要 code 参数
    if args.code is None:
        parser.print_help()
        print("\n❌ 错误：请提供股票代码，或使用 --scan 运行选股扫描模式")
        return 1

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
