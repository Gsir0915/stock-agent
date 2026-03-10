# -*- coding: utf-8 -*-
"""
全 A 股市场海龟选股器
从主板 + 北交所中筛选符合海龟交易条件的股票
"""

import argparse
import sys
import io
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from ..core.turtle import TurtleScreener, TurtleConfig, TurtleSignal
from ..data.downloader import DataDownloader
from ..data.repository import get_repository
from ..utils.logger import get_logger
from ..utils.stock_names import StockNameService

logger = get_logger("full_market_screener")


@dataclass
class StockInfo:
    """股票信息"""
    code: str  # 股票代码
    name: str  # 股票名称
    price: float  # 当前价格
    market: str  # 市场：主板/创业板/科创板/北交所


class FullMarketTurtleScreener:
    """全市场海龟选股器"""

    def __init__(
        self,
        capital: float = 100000,
        config: Optional[TurtleConfig] = None,
        use_cache: bool = True
    ):
        """
        初始化选股器

        Args:
            capital: 每只股票可用资金
            config: 配置参数
            use_cache: 是否使用缓存数据
        """
        self.capital = capital
        self.config = config or TurtleConfig()
        self.use_cache = use_cache

        self.screener = TurtleScreener(self.config)
        self.downloader = DataDownloader()
        self.repository = get_repository()

    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """
        获取全 A 股市场股票列表（主板 + 北交所）

        Returns:
            股票列表 [{"code": "600519", "name": "贵州茅台", "price": 1800.0}, ...]
        """
        import akshare as ak

        print("正在获取全市场股票列表...")

        try:
            # 获取 A 股实时行情数据
            df_spot = ak.stock_zh_a_spot_em()

            if df_spot is None or len(df_spot) == 0:
                logger.error("无法获取股票列表")
                return []

            # 过滤有效数据
            stocks = []
            for _, row in df_spot.iterrows():
                code = str(row.get("代码", "")).strip()
                name = row.get("名称", "")

                # 跳过无效数据
                if not code or code == "-" or name == "-" or name == "":
                    continue

                # 获取价格
                price_str = str(row.get("最新价", ""))
                try:
                    price = float(price_str) if price_str and price_str != "-" else 0.0
                except (ValueError, TypeError):
                    price = 0.0

                # 跳过停牌或无价格的股票
                if price <= 0:
                    continue

                # 判断市场
                market = self._identify_market(code)

                stocks.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "market": market
                })

            logger.info(f"获取到 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            logger.error(f"获取股票列表失败：{e}")
            return []

    def _identify_market(self, code: str) -> str:
        """根据代码识别市场"""
        code = str(code).strip()

        if code.startswith("60") or code.startswith("600") or code.startswith("601") or code.startswith("603") or code.startswith("605"):
            return "主板"
        elif code.startswith("000") or code.startswith("001") or code.startswith("002") or code.startswith("003"):
            return "主板"
        elif code.startswith("300") or code.startswith("301"):
            return "创业板"
        elif code.startswith("688"):
            return "科创板"
        elif code.startswith("4") or code.startswith("8") or code.startswith("920"):
            return "北交所"
        else:
            return "其他"

    def scan_market(
        self,
        top_n: int = 10,
        min_price: float = 2.0,
        max_price: float = 500.0,
        exclude_st: bool = True,
        exclude_kcb: bool = False,
        exclude_bse: bool = False
    ) -> List[TurtleSignal]:
        """
        扫描全市场，找出符合条件的股票

        Args:
            top_n: 返回符合条件的股票数量
            min_price: 最低价格过滤
            max_price: 最高价格过滤
            exclude_st: 排除 ST 股票
            exclude_kcb: 排除科创板
            exclude_bse: 排除北交所

        Returns:
            符合条件的股票信号列表
        """
        print("=" * 70)
        print("全 A 股市场海龟选股器")
        print("=" * 70)
        print(f"扫描时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标数量：{top_n} 只")
        print(f"价格范围：¥{min_price:.0f} - ¥{max_price:.0f}")
        print(f"排除 ST: {'是' if exclude_st else '否'}")
        print(f"排除科创板：{'是' if exclude_kcb else '否'}")
        print(f"排除北交所：{'是' if exclude_bse else '否'}")
        print("=" * 70)

        # 获取股票列表
        all_stocks = self.get_all_stocks()

        if not all_stocks:
            print("获取股票列表失败")
            return []

        # 过滤条件
        filtered_stocks = []
        for stock in all_stocks:
            # 价格过滤
            if stock["price"] < min_price or stock["price"] > max_price:
                continue

            # ST 股票过滤
            if exclude_st and ("ST" in stock["name"] or "退" in stock["name"]):
                continue

            # 市场过滤
            if exclude_kcb and stock["market"] == "科创板":
                continue

            if exclude_bse and stock["market"] == "北交所":
                continue

            filtered_stocks.append(stock)

        print(f"\n初始股票池：{len(all_stocks)} 只")
        print(f"过滤后股票池：{len(filtered_stocks)} 只")
        print(f"开始扫描...\n")

        # 扫描股票
        results = []
        matched = []

        for i, stock in enumerate(filtered_stocks):
            code = stock["code"]
            name = stock["name"]

            # 显示进度
            if (i + 1) % 100 == 0:
                print(f"进度：{i + 1}/{len(filtered_stocks)} (已匹配：{len(matched)}只)")

            try:
                # 获取数据
                df = self._get_stock_data(code)

                if df is None or len(df) < 60:
                    continue

                # 执行海龟选股检查
                signal = self.screener.check_stock(code, name, df, self.capital)

                if not signal.success:
                    continue

                # 检查是否符合买入条件
                if (signal.breakout and signal.atr_consolidation and
                    signal.atr_trend == "rising" and signal.position_size > 0):
                    matched.append(signal)

                    # 如果达到目标数量，停止扫描
                    if len(matched) >= top_n:
                        print(f"\n已找到 {top_n} 只符合条件的股票，停止扫描")
                        break

            except Exception as e:
                # 单个股票失败不影响整体
                continue

        # 显示结果
        self._print_results(matched, top_n)

        return matched

    def _get_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        # 优先使用缓存
        if self.use_cache:
            df = self.repository.load_stock_data(code)
            if df is not None:
                return df

        # 下载数据
        try:
            df = self.downloader.download_stock_history(code)
            if df is not None:
                self.repository.save_stock_data(code, df)
            return df
        except Exception:
            return None

    def _print_results(self, results: List[TurtleSignal], top_n: int) -> None:
        """打印结果"""
        print("\n" + "=" * 80)
        print(f"扫描结果 - 符合海龟买入条件的股票")
        print("=" * 80)

        if not results:
            print("\n未找到符合条件的股票")
            print("条件：20 日新高 + ATR 低位震荡后向上 + 头寸>0")
            return

        print(f"\n共找到 {len(results)} 只股票（目标：{top_n}只）\n")

        # 打印汇总表
        print(f"{'序号':<6} {'代码':<10} {'名称':<12} {'价格':>8} {'突破%':>8} {'ATR':>8} {'股数':>10} {'金额':>12} {'止损':>8}")
        print("-" * 90)

        for i, s in enumerate(results, 1):
            breakout_pct = ((s.current_price - s.twenty_day_high) / s.twenty_day_high * 100
                           if s.twenty_day_high > 0 else 0)
            stop_pct = ((s.current_price - s.stop_loss_price) / s.current_price * 100
                       if s.stop_loss_price > 0 else 0)

            print(f"{i:<6} {s.code:<10} {s.name[:12]:<12} {s.current_price:>8.2f} "
                  f"{breakout_pct:>7.2f}% {s.atr_current:>8.3f} "
                  f"{s.position_size:>10,} {s.position_value:>12,.0f} {s.stop_loss_price:>8.2f}")

        print("-" * 90)
        total_value = sum(s.position_value for s in results)
        total_risk = sum(s.risk_amount for s in results)
        print(f"合计：{len(results)} 只股票")
        print(f"      总金额：¥{total_value:,.0f}")
        print(f"      总风险：¥{total_risk:,.0f} ({total_risk / (self.capital * len(results)) * 100:.1f}% 平均)")

        # 打印详细信息
        print("\n" + "=" * 80)
        print("个股详细信息")
        print("=" * 80)

        for i, s in enumerate(results, 1):
            print(f"\n[{i}] {s.code} {s.name}")
            print(f"    当前价格：¥{s.current_price:.2f} | 20 日最高：¥{s.twenty_day_high:.2f}")
            print(f"    ATR: {s.atr_current:.3f} (趋势：{s.atr_trend})")
            print(f"    建议头寸：{s.position_size:,} 股")
            print(f"    建仓金额：¥{s.position_value:,.0f}")
            print(f"    止损价格：¥{s.stop_loss_price:.2f} (幅度：{(s.current_price - s.stop_loss_price) / s.current_price * 100:.2f}%)")
            print(f"    风险金额：¥{s.risk_amount:,.0f} (2%)")

        print("\n" + "=" * 80)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="全 A 股市场海龟选股器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描全市场，找出 10 只符合条件的股票
  python -m app.turtle_screener.market_scan

  # 扫描 20 只股票
  python -m app.turtle_screener.market_scan --top-n 20

  # 指定价格范围
  python -m app.turtle_screener.market_scan --min-price 5 --max-price 200

  # 包含 ST 股票
  python -m app.turtle_screener.market_scan --include-st

  # 排除科创板和北交所
  python -m app.turtle_screener.market_scan --exclude-kcb --exclude-bse

  # 不使用缓存（下载最新数据）
  python -m app.turtle_screener.market_scan --no-cache
        """
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="返回符合条件的股票数量（默认：10）"
    )

    parser.add_argument(
        "--min-price",
        type=float,
        default=2.0,
        help="最低价格过滤（默认：2 元）"
    )

    parser.add_argument(
        "--max-price",
        type=float,
        default=500.0,
        help="最高价格过滤（默认：500 元）"
    )

    parser.add_argument(
        "--include-st",
        action="store_true",
        help="包含 ST 股票（默认：排除）"
    )

    parser.add_argument(
        "--exclude-kcb",
        action="store_true",
        help="排除科创板（默认：包含）"
    )

    parser.add_argument(
        "--exclude-bse",
        action="store_true",
        help="排除北交所（默认：包含）"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="不使用缓存数据"
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="每只股票可用资金（默认：100000）"
    )

    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 初始化选股器
    screener = FullMarketTurtleScreener(
        capital=args.capital,
        use_cache=not args.no_cache
    )

    # 执行扫描
    results = screener.scan_market(
        top_n=args.top_n,
        min_price=args.min_price,
        max_price=args.max_price,
        exclude_st=not args.include_st,
        exclude_kcb=args.exclude_kcb,
        exclude_bse=args.exclude_bse
    )

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
