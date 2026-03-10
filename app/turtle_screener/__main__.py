# -*- coding: utf-8 -*-
"""
海龟交易法则选股器 - 模块入口
支持子命令方式运行

使用方式:
    python -m app.turtle_screener              # 默认股票池扫描
    python -m app.turtle_screener 600519       # 检查单只股票
    python -m app.turtle_screener market_scan  # 全市场扫描
    python -m app.turtle_screener monitor      # 持仓监控
"""

import sys
import argparse


def create_main_parser() -> argparse.ArgumentParser:
    """创建主命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="海龟交易法则选股器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  (无)              扫描默认股票池
  <股票代码>        检查单只股票
  market_scan       全 A 股市场扫描
  monitor           持仓监控（价格/止损/加仓提醒）

示例:
  # 扫描默认股票池
  python -m app.turtle_screener

  # 检查单只股票
  python -m app.turtle_screener 600519

  # 全市场扫描，找出 10 只符合条件的股票
  python -m app.turtle_screener market_scan

  # 全市场扫描 20 只
  python -m app.turtle_screener market_scan --top-n 20

  # 持仓监控
  python -m app.turtle_screener monitor

  # 添加持仓
  python -m app.turtle_screener monitor add 002053

  # 显示监控报告并检查提醒
  python -m app.turtle_screener monitor report --alert
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help="子命令或股票代码"
    )

    # 传递剩余参数给子命令
    subargs, unknown = parser.parse_known_args()

    return parser, subargs, unknown


def main():
    """主函数"""
    parser, args, unknown = create_main_parser()

    command = args.command

    if command is None:
        # 无命令，扫描默认股票池
        from .turtle_screener import main as screener_main
        sys.argv = [sys.argv[0]] + unknown
        screener_main()

    elif command == "market_scan":
        # 全市场扫描
        from .market_scan import main as market_main
        sys.argv = [sys.argv[0]] + unknown
        market_main()

    elif command == "monitor":
        # 持仓监控
        from .monitor_cli import main as monitor_main
        sys.argv = [sys.argv[0]] + unknown
        monitor_main()

    elif command == "help" or command == "-h" or command == "--help":
        parser.print_help()

    else:
        # 假设是股票代码
        from .turtle_screener import main as screener_main
        sys.argv = [sys.argv[0], command] + unknown
        screener_main()


if __name__ == "__main__":
    main()
