# -*- coding: utf-8 -*-
"""
海龟交易法则选股器 - CLI 入口

功能:
1. 扫描股票池，找出符合海龟交易买入条件的股票
2. 显示突破信号、ATR 状态、建议头寸

使用方式:
    python -m app.turtle_screener              # 扫描默认股票池
    python -m app.turtle_screener 600519       # 检查单只股票
    python -m app.turtle_screener --pool       # 使用股票池模式
"""

import argparse
import sys
import io
from typing import List, Dict, Any
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

from ..core.turtle import TurtleScreener, TurtleConfig, TurtleSignal
from ..data.repository import DataRepository, get_repository
from ..data.downloader import DataDownloader
from ..utils.logger import get_logger
from ..utils.stock_names import StockNameService

logger = get_logger("turtle_screener")


# 默认股票池 - 可根据需要扩展
DEFAULT_STOCK_POOL = [
    # 白酒/消费
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
    {"code": "000568", "name": "泸州老窖"},
    {"code": "600809", "name": "山西汾酒"},
    {"code": "002304", "name": "洋河股份"},

    # 金融
    {"code": "601318", "name": "中国平安"},
    {"code": "600036", "name": "招商银行"},
    {"code": "601166", "name": "兴业银行"},

    # 科技
    {"code": "002415", "name": "海康威视"},
    {"code": "300750", "name": "宁德时代"},
    {"code": "600030", "name": "中信证券"},

    # 医药
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "000538", "name": "云南白药"},
    {"code": "300122", "name": "智飞生物"},

    # 周期/其他
    {"code": "600585", "name": "海螺水泥"},
    {"code": "601088", "name": "中国神华"},
    {"code": "600900", "name": "长江电力"},
]


class TurtleScreenerCLI:
    """海龟选股器命令行界面"""

    def __init__(
        self,
        data_dir: str = "data",
        capital: float = 100000,
        config: TurtleConfig = None
    ):
        """
        初始化 CLI

        Args:
            data_dir: 数据目录
            capital: 每只股票可用资金
            config: 配置参数
        """
        self.data_dir = data_dir
        self.capital = capital
        self.config = config or TurtleConfig()

        # 初始化数据服务
        self.repository = get_repository(data_dir)
        self.downloader = DataDownloader()

        # 初始化选股器
        self.screener = TurtleScreener(self.config)

    def check_single_stock(
        self,
        code: str,
        download: bool = True
    ) -> TurtleSignal:
        """
        检查单只股票

        Args:
            code: 股票代码
            download: 是否下载最新数据

        Returns:
            TurtleSignal 交易信号
        """
        name = StockNameService.get_name(code)

        # 获取数据
        df = self._get_stock_data(code, download)

        if df is None:
            return TurtleSignal(
                code=code,
                name=name,
                success=False,
                error="无法获取股票数据"
            )

        # 执行检查
        return self.screener.check_stock(code, name, df, self.capital)

    def scan_pool(
        self,
        stock_pool: List[Dict[str, Any]] = None,
        download: bool = True
    ) -> List[TurtleSignal]:
        """
        扫描股票池

        Args:
            stock_pool: 股票池列表
            download: 是否下载最新数据

        Returns:
            符合条件的股票信号列表
        """
        if stock_pool is None:
            stock_pool = DEFAULT_STOCK_POOL

        results = []
        matched = []

        logger.info(f"开始扫描 {len(stock_pool)} 只股票...")
        print(f"\n{'='*60}")
        print(f"海龟交易法则选股器 - 扫描结果")
        print(f"{'='*60}")
        print(f"扫描时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"股票池：{len(stock_pool)} 只")
        print(f"资金配置：¥{self.capital:,.0f} / 每只")
        print(f"{'='*60}\n")

        for stock in stock_pool:
            code = stock["code"]
            name = stock.get("name", "")

            try:
                df = self._get_stock_data(code, download)

                if df is None:
                    logger.warning(f"无法获取股票数据：{code}")
                    continue

                signal = self.screener.check_stock(code, name, df, self.capital)
                results.append(signal)

                # 显示检查结果
                self._print_signal(signal, verbose=False)

                # 收集符合买入条件的股票
                if (signal.success and signal.breakout and
                    signal.atr_consolidation and signal.atr_trend == "rising"):
                    matched.append(signal)

            except Exception as e:
                logger.error(f"扫描股票 {code} 失败：{e}")
                continue

        # 显示汇总
        print(f"\n{'='*60}")
        print(f"扫描完成：共检查 {len(results)} 只股票")
        print(f"{'='*60}\n")

        # 显示符合条件的股票
        if matched:
            print(f"\n🐢 符合海龟买入条件的股票 ({len(matched)} 只):\n")
            self._print_summary_table(matched)
        else:
            print("\n⚠️  当前没有股票符合海龟买入条件")
            print("   条件：20 日新高 + ATR 低位震荡后向上\n")

        return matched

    def _get_stock_data(
        self,
        code: str,
        download: bool
    ) -> pd.DataFrame:
        """获取股票数据"""
        # 优先使用缓存
        df = self.repository.load_stock_data(code)

        if df is not None and not download:
            return df

        # 下载数据
        if download:
            try:
                df = self.downloader.download_stock_history(code)
                if df is not None:
                    self.repository.save_stock_data(code, df)
                return df
            except Exception as e:
                logger.warning(f"下载失败：{e}，尝试使用缓存...")
                return self.repository.load_stock_data(code)

        return df

    def _print_signal(self, signal: TurtleSignal, verbose: bool = True) -> None:
        """打印信号详情"""
        if not signal.success:
            print(f"  {signal.code}: ❌ {signal.error}")
            return

        # 状态图标
        breakout_icon = "✅" if signal.breakout else "❌"
        atr_icon = "✅" if signal.atr_consolidation else "❌"
        trend_icon = {
            "rising": "📈",
            "falling": "📉",
            "stable": "➖",
            "unknown": "❓"
        }.get(signal.atr_trend, "❓")

        # 简洁输出
        if not verbose:
            status = "匹配" if (signal.breakout and signal.atr_consolidation and
                           signal.atr_trend == "rising") else "不匹配"
            status_icon = "🐢" if status == "匹配" else "⚪"
            print(f"  {status_icon} {signal.code} {signal.name[:10]:<10} | "
                  f"突破:{breakout_icon} ATR:{atr_icon}{trend_icon} | "
                  f"ATR={signal.atr_current:.2f}")
            return

        # 详细输出
        print(f"\n{'='*50}")
        print(f"股票代码：{signal.code} ({signal.name})")
        print(f"{'='*50}")

        # 突破信号
        print(f"\n📊 突破信号:")
        print(f"  当前价格：¥{signal.current_price:.2f}")
        print(f"  20 日最高：¥{signal.twenty_day_high:.2f}")
        print(f"  是否突破：{'✅ 是' if signal.breakout else '❌ 否'}")
        if signal.breakout:
            print(f"  突破幅度：{(signal.current_price - signal.twenty_day_high) / signal.twenty_day_high * 100:.2f}%")

        # ATR 信号
        print(f"\n📈 ATR 分析:")
        print(f"  当前 ATR: {signal.atr_current:.3f}")
        print(f"  前 5 日均：{signal.atr_prev_5:.3f}")
        print(f"  前 10 日均：{signal.atr_prev_10:.3f}")
        print(f"  ATR 趋势：{trend_icon} {signal.atr_trend}")
        print(f"  低位震荡：{'✅ 是' if signal.atr_consolidation else '❌ 否'}")
        print(f"  说明：{signal.consolidation_details}")

        # 头寸建议
        if signal.position_size > 0:
            print(f"\n💰 头寸建议:")
            print(f"  建议股数：{signal.position_size:,} 股")
            print(f"  建仓金额：¥{signal.position_value:,.0f}")
            print(f"  风险金额：¥{signal.risk_amount:,.0f} ({signal.risk_amount / self.capital * 100:.1f}%)")
            print(f"  止损价格：¥{signal.stop_loss_price:.2f}")
            print(f"  止损幅度：{(signal.current_price - signal.stop_loss_price) / signal.current_price * 100:.2f}%")
            print(f"  单位风险 (1N): ¥{signal.unit_risk:.2f}")

            # 加仓窗口
            if signal.add_unit_window > 0 and signal.add_unit_prices:
                print(f"\n📈 加仓窗口:")
                print(f"  加仓间距：0.5N = ¥{signal.add_unit_window:.2f}")
                print(f"  最多加仓：3 次 (总仓位 4 个单位)")
                print(f"  加仓价格:")
                for i, price in enumerate(signal.add_unit_prices, 1):
                    add_value = signal.position_size * price
                    print(f"    第{i}次加仓：¥{price:.2f} (加仓 {signal.position_size:,} 股，金额 ¥{add_value:,.0f})")
                print(f"  统一止损：¥{signal.stop_loss_price:.2f} (所有仓位)")

            # 移动止损/止盈
            if signal.current_trailing_stop > 0:
                print(f"\n🛡️ 移动止损 (止盈):")
                print(f"  初始止损：¥{signal.stop_loss_price:.2f} (入场价 - 2N)")
                print(f"  移动止损：¥{signal.current_trailing_stop:.2f} (最高价 - 2N)")
                print(f"  信号：{signal.exit_signal}")
                print(f"\n  💡 止盈策略：股价每创新高，止损价上移 0.5N；跌破移动止损价时全部退出")

        print()

    def _print_summary_table(self, signals: List[TurtleSignal]) -> None:
        """打印汇总表"""
        print(f"{'代码':<10} {'名称':<15} {'价格':>8} {'ATR':>8} {'突破%':>8} {'股数':>10} {'金额':>12}")
        print(f"{'-'*75}")

        for s in signals:
            breakout_pct = ((s.current_price - s.twenty_day_high) / s.twenty_day_high * 100
                           if s.twenty_day_high > 0 else 0)
            print(f"{s.code:<10} {s.name[:15]:<15} {s.current_price:>8.2f} {s.atr_current:>8.3f} "
                  f"{breakout_pct:>7.2f}% {s.position_size:>10,} {s.position_value:>12,.0f}")

        print(f"{'-'*75}")
        print(f"合计：{len(signals)} 只股票，总金额：¥{sum(s.position_value for s in signals):,.0f}")


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="海龟交易法则选股器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描默认股票池
  python -m app.turtle_screener

  # 检查单只股票
  python -m app.turtle_screener 600519

  # 使用自定义股票池
  python -m app.turtle_screener --pool

  # 指定资金量
  python -m app.turtle_screener --capital 200000

  # 不使用 AI 分析 (仅技术面)
  python -m app.turtle_screener --no-download
        """
    )

    parser.add_argument(
        "code",
        nargs="?",
        default=None,
        help="股票代码 (如果不填则扫描股票池)"
    )

    parser.add_argument(
        "--pool",
        action="store_true",
        help="强制使用股票池模式"
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="每只股票可用资金 (默认：100000)"
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="数据目录 (默认：data)"
    )

    parser.add_argument(
        "--no-download",
        action="store_true",
        help="不下载最新数据，使用缓存"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    # 初始化 CLI
    cli = TurtleScreenerCLI(
        data_dir=args.data_dir,
        capital=args.capital
    )

    # 执行检查
    if args.code and not args.pool:
        # 单只股票模式
        logger.info(f"检查股票：{args.code}")
        signal = cli.check_single_stock(args.code, download=not args.no_download)
        cli._print_signal(signal, verbose=args.verbose)

        # 显示是否符合条件
        if signal.success and signal.breakout and signal.atr_consolidation:
            if signal.atr_trend == "rising":
                print(f"\n🐢 {signal.code} 符合海龟买入条件!")
                if signal.position_size > 0:
                    print(f"   建议建仓：{signal.position_size:,} 股 @ ¥{signal.current_price:.2f}")
                    print(f"   止损价格：¥{signal.stop_loss_price:.2f}")
                    print(f"   风险敞口：¥{signal.risk_amount:,.0f} (2%)")
                    # 加仓窗口
                    if signal.add_unit_window > 0:
                        print(f"\n   加仓窗口:")
                        print(f"   加仓间距：0.5N = ¥{signal.add_unit_window:.2f}")
                        print(f"   加仓价格：{', '.join([f'¥{p:.2f}' for p in signal.add_unit_prices])}")
            else:
                print(f"\n⚠️ {signal.code} 部分符合条件 (ATR 未明显向上)")
        else:
            reason = []
            if not signal.breakout:
                reason.append("未创 20 日新高")
            if not signal.atr_consolidation:
                reason.append("ATR 未处于震荡")
            if reason:
                print(f"\n❌ {signal.code} 不符合条件：{', '.join(reason)}")

    else:
        # 股票池模式
        cli.scan_pool(download=not args.no_download)


if __name__ == "__main__":
    main()
