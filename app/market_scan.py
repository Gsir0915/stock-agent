# -*- coding: utf-8 -*-
"""
全市场股票扫描 - 使用 StockSelector 多因子模型
"""

import sys
import io

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_selector.factors import QualityFactor, MomentumFactor, DividendFactor
from agents.stock_selector.engine import StockSelectorEngine
from app.data.downloader import DataDownloader
from app.data.repository import DataRepository
from app.utils.stock_names import StockNameService


def load_stock_pool(pool_file: str = "data/stock_pool_all.txt") -> List[str]:
    """加载股票池"""
    try:
        with open(pool_file, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]
        return codes
    except FileNotFoundError:
        print(f"错误：股票池文件不存在：{pool_file}")
        return []


def get_market_mode_name(engine: StockSelectorEngine) -> str:
    """获取当前市场模式名称"""
    try:
        regime = engine.determine_market_regime()
        return regime.regime_name
    except Exception as e:
        print(f"[WARN] 获取市场模式失败：{e}")
        return "结构性行情"


def run_full_market_scan(
    stock_pool: List[str],
    data_dir: str = "data",
    top_n: int = 10,
    use_filters: bool = True
) -> List[Dict]:
    """
    运行全市场扫描

    Args:
        stock_pool: 股票代码池
        data_dir: 数据目录
        top_n: 返回前 N 只股票
        use_filters: 是否使用过滤条件

    Returns:
        选股结果列表
    """
    from app.data.downloader import DataDownloader
    from app.data.repository import DataRepository
    from agents.stock_selector.backtest_logger import get_backtest_logger

    print("=" * 70)
    print("🔍 Stock Selector - 全市场扫描")
    print("=" * 70)
    print(f"股票池总数：{len(stock_pool)}")
    print(f"数据目录：{data_dir}")
    print(f"目标：选出 Top {top_n}")
    print("=" * 70 + "\n")

    # 初始化服务
    downloader = DataDownloader()
    repository = DataRepository(data_dir)

    # 初始化因子
    quality_factor = QualityFactor()
    momentum_factor = MomentumFactor()
    dividend_factor = DividendFactor()

    # 初始化选股引擎（用于获取市场模式和权重）
    selector_engine = StockSelectorEngine()

    # 获取当前市场模式和因子权重
    try:
        regime = selector_engine.determine_market_regime()
        weights = selector_engine.get_current_weights()
        print(f"当前市场模式：{regime.regime_name}")
        print(f"两市成交额：{regime.total_turnover:.2f} 亿元")
        print(f"上证指数：{regime.sh_index_close:.2f} 点")
        print(f"趋势类型：{regime.trend_type}")
        print(f"\n当前因子权重:")
        for factor, weight in weights.items():
            print(f"  {factor}: {weight:.0%}")
        print()
    except Exception as e:
        print(f"[WARN] 获取市场模式失败：{e}")
        weights = {"quality": 0.25, "momentum": 0.25, "dividend": 0.25, "valuation": 0.25}

    # 获取过滤条件
    filters_config = selector_engine._config.filters if selector_engine._config else None

    # 初始化回测日志
    bt_logger = get_backtest_logger()

    results = []
    processed = 0
    errors = 0

    for code in stock_pool:
        processed += 1

        # 每 500 只显示一次进度
        if processed % 500 == 0:
            print(f"进度：{processed}/{len(stock_pool)} ({processed/len(stock_pool)*100:.1f}%) - 成功：{len(results)} - 错误：{errors}")

        name = StockNameService.get_name(code)

        try:
            # 获取股票数据
            df = repository.load_stock_data(code)
            if df is None or len(df) < 60:
                try:
                    df = downloader.download_stock_history(code)
                    repository.save_stock_data(code, df)
                except Exception as e:
                    errors += 1
                    continue

            if df is None or len(df) < 60:
                errors += 1
                continue

            # 应用过滤条件
            if use_filters and filters_config:
                # 检查上市天数
                min_listing_days = getattr(filters_config, 'min_listing_days', 0)
                if min_listing_days and len(df) < min_listing_days:
                    continue

                # 检查股价
                latest_price = float(df.iloc[-1]["收盘"])
                min_price = getattr(filters_config, 'min_price', 0)
                if min_price and latest_price < min_price:
                    continue

                # 检查市值（需要基本面数据）
                # 简化处理：跳过市值检查

            # 获取基本面数据
            fundamentals = downloader.get_fundamentals(code)

            # 如果之前没有获取到名称，尝试从基本面数据中获取
            if not name and fundamentals:
                name = fundamentals.get("name", code)

            # 动量因子数据
            latest = df.iloc[-1]
            current_price = float(latest["收盘"])
            current_volume = float(latest.get("成交量", 0))
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

            # 质量因子数据
            profit_growth = fundamentals.get("profit_growth", 0) if fundamentals else 0
            quality_data = {
                "fcf": fundamentals.get("fcf", 1) if fundamentals else 1,
                "net_profit": fundamentals.get("net_profit", 1) if fundamentals else 1,
                "net_profit_growth": profit_growth,
            }

            # 股息因子数据
            dividend_data = {
                "dividend_yield": fundamentals.get("dividend_yield", 2.5) if fundamentals else 2.5,
                "consecutive_years": fundamentals.get("consecutive_years", 3) if fundamentals else 3,
                "payout_ratio": fundamentals.get("payout_ratio", 40) if fundamentals else 40,
            }

            # 计算因子得分
            quality_score = quality_factor.run(quality_data)
            momentum_score = momentum_factor.run(momentum_data)
            dividend_score = dividend_factor.run(dividend_data)

            # 根据市场模式加权计算综合得分
            total_score = (
                quality_score * weights.get("quality", 0.25) +
                momentum_score * weights.get("momentum", 0.25) +
                dividend_score * weights.get("dividend", 0.25) +
                0.5 * weights.get("valuation", 0.25)  # 估值因子简化处理
            )

            # 记录结果
            results.append({
                "code": code,
                "name": name or code,
                "quality_score": quality_score,
                "momentum_score": momentum_score,
                "dividend_score": dividend_score,
                "total_score": total_score,
                "price": current_price,
            })

            # 记录到回测日志
            bt_logger.log_selection(
                stock_code=code,
                stock_name=name or code,
                entry_price=current_price,
                quality_score=quality_score,
                momentum_score=momentum_score,
                dividend_score=dividend_score,
                total_score=total_score,
                ranks={"total": len(results)}
            )

        except Exception as e:
            errors += 1
            continue

    # 按总分排序
    results.sort(key=lambda x: x["total_score"], reverse=True)

    # 打印结果
    print("\n" + "=" * 70)
    print(f"扫描完成！处理：{processed} 只，成功：{len(results)} 只，错误：{errors}")
    print("=" * 70)

    # 打印 Top N
    print(f"\n📊 全市场扫描 Top {top_n} 推荐:\n")
    print("| 排名 | 代码 | 名称 | 价格 | 质量 | 动量 | 股息 | 综合得分 |")
    print("|------|------|------|------|------|------|------|----------|")

    for i, r in enumerate(results[:top_n], 1):
        print(
            f"| {i} | {r['code']} | {r['name']} | {r['price']:.2f} | "
            f"{r['quality_score']:.2f} | {r['momentum_score']:.2f} | "
            f"{r['dividend_score']:.2f} | {r['total_score']:.2f} |"
        )

    print("\n## 因子说明\n")
    print("- **质量因子**: 基于 FCF/净利润比率和利润增长率")
    print("- **动量因子**: 基于价格位置 (20 日区间) 和成交量放大程度")
    print("- **股息因子**: 基于股息率、连续分红年数和分红健康度")
    print(f"- **市场模式**: {regime.regime_name} (权重动态调整)\n")

    # 保存回测日志
    bt_logger.save()
    print(f"[OK] 回测日志已保存：backtest_logs\\backtest_{pd.Timestamp.now().strftime('%Y%m%d')}.json")

    # 保存结果到 CSV
    output_file = f"market_scan_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[OK] 完整结果已保存：{output_file}")

    print("\n" + "=" * 70)

    return results[:top_n]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="全市场股票扫描")
    parser.add_argument("--top-n", type=int, default=10, help="返回前 N 只股票")
    parser.add_argument("--pool", type=str, default="data/stock_pool_all.txt", help="股票池文件路径")
    parser.add_argument("--data-dir", type=str, default="data", help="数据目录")
    parser.add_argument("--no-filters", action="store_true", help="不使用过滤条件")

    args = parser.parse_args()

    # 加载股票池
    stock_pool = load_stock_pool(args.pool)

    if not stock_pool:
        print("错误：股票池为空")
        sys.exit(1)

    # 运行扫描
    top_stocks = run_full_market_scan(
        stock_pool=stock_pool,
        data_dir=args.data_dir,
        top_n=args.top_n,
        use_filters=not args.no_filters
    )
