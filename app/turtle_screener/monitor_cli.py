# -*- coding: utf-8 -*-
"""
海龟交易监控器 - CLI 入口

功能:
1. 监控持仓股票的价格和止损
2. 加仓提醒
3. 止盈预警
4. 生成监控报告

使用方式:
    python -m app.turtle_screener monitor              # 查看监控报告
    python -m app.turtle_screener monitor --add        # 添加持仓
    python -m app.turtle_screener monitor --alert      # 检查提醒
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

from .monitor import TurtleMonitor, PositionInfo, WatchStock, create_monitor
from ..utils.logger import get_logger
from ..utils.stock_names import StockNameService

logger = get_logger("turtle_monitor_cli")

# 持仓数据文件
POSITIONS_FILE = Path("data/turtle_positions.json")
WATCHLIST_FILE = Path("data/turtle_watchlist.json")


def load_positions() -> List[Dict[str, Any]]:
    """加载持仓数据"""
    if not POSITIONS_FILE.exists():
        return []
    with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_positions(positions: List[Dict[str, Any]]):
    """保存持仓数据"""
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


def load_watchlist() -> List[Dict[str, Any]]:
    """加载关注列表"""
    if not WATCHLIST_FILE.exists():
        return []
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(watchlist: List[Dict[str, Any]]):
    """保存关注列表"""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def cmd_report(args):
    """显示监控报告"""
    monitor = create_monitor()

    # 加载持仓
    positions_data = load_positions()
    for p in positions_data:
        position = PositionInfo(
            code=p["code"],
            name=p["name"],
            entry_price=p["entry_price"],
            entry_date=p.get("entry_date", ""),
            units=p.get("units", 1),
            shares_per_unit=p["shares_per_unit"],
            total_shares=p["total_shares"],
            total_cost=p["total_cost"],
            initial_stop=p["initial_stop"],
            current_stop=p.get("current_stop", p["initial_stop"]),
            stop_n=p.get("stop_n", 2),
            atr=p.get("atr", 0),
            add_unit_window=p.get("add_unit_window", 0),
            add_prices=p.get("add_prices", []),
            filled_add_prices=p.get("filled_add_prices", [])
        )
        monitor.add_position(position)

    # 加载关注列表
    watchlist_data = load_watchlist()
    for w in watchlist_data:
        stock = WatchStock(
            code=w["code"],
            name=w["name"],
            breakout_price=w["breakout_price"],
            add_prices=w.get("add_prices", []),
            stop_price=w.get("stop_price", 0)
        )
        monitor.add_to_watchlist(stock)

    # 更新价格
    print("正在更新价格...")
    results = monitor.update_prices()

    # 保存更新后的数据
    positions_data = []
    for p in monitor.positions:
        positions_data.append({
            "code": p.code,
            "name": p.name,
            "entry_price": p.entry_price,
            "entry_date": p.entry_date,
            "units": p.units,
            "shares_per_unit": p.shares_per_unit,
            "total_shares": p.total_shares,
            "total_cost": p.total_cost,
            "initial_stop": p.initial_stop,
            "current_stop": p.current_stop,
            "stop_n": p.stop_n,
            "atr": p.atr,
            "add_unit_window": p.add_unit_window,
            "add_prices": p.add_prices,
            "filled_add_prices": p.filled_add_prices
        })
    save_positions(positions_data)

    # 显示提醒
    if args.alert and results["alerts"]:
        monitor.print_alerts(results["alerts"])

    # 显示报告
    report = monitor.generate_report()
    print(report)

    return 0


def cmd_add_position(args):
    """添加持仓"""
    code = args.code
    name = StockNameService.get_name(code)

    # 获取股票数据计算 ATR
    from ..data.downloader import DataDownloader
    from ..data.repository import get_repository
    from ..core.turtle import TurtleScreener

    downloader = DataDownloader()
    repository = get_repository()

    df = downloader.download_stock_history(code)
    if df is not None:
        repository.save_stock_data(code, df)

    screener = TurtleScreener()
    signal = screener.check_stock(code, name, df, args.capital)

    if not signal.success or signal.position_size == 0:
        print(f"❌ 无法获取 {code} 的交易信号")
        return 1

    # 创建持仓记录
    position = {
        "code": code,
        "name": name,
        "entry_price": signal.current_price,
        "entry_date": "",
        "units": 1,
        "shares_per_unit": signal.position_size,
        "total_shares": signal.position_size,
        "total_cost": signal.position_value,
        "initial_stop": signal.stop_loss_price,
        "current_stop": signal.stop_loss_price,
        "stop_n": 2,
        "atr": signal.atr_current,
        "add_unit_window": signal.add_unit_window,
        "add_prices": signal.add_unit_prices,
        "filled_add_prices": []
    }

    # 加载并添加
    positions = load_positions()
    positions.append(position)
    save_positions(positions)

    print(f"✅ 已添加持仓：{code} {name}")
    print(f"   入场价：¥{signal.current_price:.2f}")
    print(f"   股数：{signal.position_size:,}")
    print(f"   止损价：¥{signal.stop_loss_price:.2f}")
    print(f"   加仓价：{', '.join([f'¥{p:.2f}' for p in signal.add_unit_prices])}")

    return 0


def cmd_remove_position(args):
    """移除持仓"""
    positions = load_positions()
    positions = [p for p in positions if p["code"] != args.code]
    save_positions(positions)
    print(f"✅ 已移除持仓：{args.code}")
    return 0


def cmd_list_positions(args):
    """列出持仓"""
    positions = load_positions()
    if not positions:
        print("⚪ 当前无持仓")
        return 0

    print("=" * 80)
    print("📊 持仓列表")
    print("=" * 80)
    print(f"{'代码':<10} {'名称':<12} {'入场价':>8} {'股数':>10} {'成本':>12} {'止损':>8}")
    print("-" * 80)

    for p in positions:
        print(f"{p['code']:<10} {p['name'][:12]:<12} {p['entry_price']:>8.2f} "
              f"{p['total_shares']:>10,} {p['total_cost']:>12,.0f} {p['initial_stop']:>8.2f}")

    print("-" * 80)
    print(f"合计：{len(positions)} 只股票，总成本 ¥{sum(p['total_cost'] for p in positions):,.0f}")

    return 0


def cmd_add_watch(args):
    """添加到关注列表"""
    from ..data.downloader import DataDownloader
    from ..data.repository import get_repository
    from ..core.turtle import TurtleScreener

    code = args.code
    name = StockNameService.get_name(code)

    downloader = DataDownloader()
    repository = get_repository()
    screener = TurtleScreener()

    df = downloader.download_stock_history(code)
    if df is not None:
        repository.save_stock_data(code, df)

    signal = screener.check_stock(code, name, df, 100000)

    if not signal.success:
        print(f"❌ 无法获取 {code} 的数据")
        return 1

    # 创建关注记录
    watch = {
        "code": code,
        "name": name,
        "breakout_price": signal.twenty_day_high,
        "current_price": signal.current_price,
        "add_prices": signal.add_unit_prices,
        "stop_price": signal.stop_loss_price
    }

    watchlist = load_watchlist()
    watchlist.append(watch)
    save_watchlist(watchlist)

    print(f"✅ 已添加到关注列表：{code} {name}")
    print(f"   突破价：¥{signal.twenty_day_high:.2f}")
    print(f"   当前价：¥{signal.current_price:.2f}")

    return 0


def cmd_remove_watch(args):
    """从关注列表移除"""
    watchlist = load_watchlist()
    watchlist = [w for w in watchlist if w["code"] != args.code]
    save_watchlist(watchlist)
    print(f"✅ 已从关注列表移除：{args.code}")
    return 0


def cmd_list_watch(args):
    """列出关注列表"""
    watchlist = load_watchlist()
    if not watchlist:
        print("⚪ 当前无关注股票")
        return 0

    print("=" * 80)
    print("👁️ 关注列表（等待突破）")
    print("=" * 80)
    print(f"{'代码':<10} {'名称':<12} {'现价':>8} {'突破价':>8} {'加仓价':>20}")
    print("-" * 80)

    for w in watchlist:
        add_prices_str = ", ".join([f"¥{p:.2f}" for p in w.get("add_prices", [])])[:20]
        print(f"{w['code']:<10} {w['name'][:12]:<12} {w['current_price']:>8.2f} "
              f"{w['breakout_price']:>8.2f} {add_prices_str:>20}")

    print("-" * 80)
    print(f"合计：{len(watchlist)} 只股票")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="🐢 海龟交易监控器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  report           显示监控报告和提醒
  add              添加持仓
  remove           移除持仓
  list             列出持仓
  watch-add        添加到关注列表
  watch-remove     从关注列表移除
  watch-list       列出关注列表

示例:
  # 显示监控报告
  python -m app.turtle_screener monitor report

  # 显示报告并检查提醒
  python -m app.turtle_screener monitor report --alert

  # 添加持仓（自动计算头寸）
  python -m app.turtle_screener monitor add 002053

  # 列出持仓
  python -m app.turtle_screener monitor list

  # 添加到关注列表
  python -m app.turtle_screener monitor watch-add 600812
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # report 命令
    report_parser = subparsers.add_parser("report", help="显示监控报告")
    report_parser.add_argument("--alert", action="store_true", help="显示实时提醒")
    report_parser.set_defaults(func=cmd_report)

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加持仓")
    add_parser.add_argument("code", help="股票代码")
    add_parser.add_argument("--capital", type=float, default=100000, help="资金量（默认 100000）")
    add_parser.set_defaults(func=cmd_add_position)

    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="移除持仓")
    remove_parser.add_argument("code", help="股票代码")
    remove_parser.set_defaults(func=cmd_remove_position)

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出持仓")
    list_parser.set_defaults(func=cmd_list_positions)

    # watch-add 命令
    watch_add_parser = subparsers.add_parser("watch-add", help="添加到关注列表")
    watch_add_parser.add_argument("code", help="股票代码")
    watch_add_parser.set_defaults(func=cmd_add_watch)

    # watch-remove 命令
    watch_remove_parser = subparsers.add_parser("watch-remove", help="从关注列表移除")
    watch_remove_parser.add_argument("code", help="股票代码")
    watch_remove_parser.set_defaults(func=cmd_remove_watch)

    # watch-list 命令
    watch_list_parser = subparsers.add_parser("watch-list", help="列出关注列表")
    watch_list_parser.set_defaults(func=cmd_list_watch)

    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        # 无命令时显示报告
        args.command = "report"
        args.alert = True
        if not hasattr(args, "func"):
            args.func = cmd_report
        args.func(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
