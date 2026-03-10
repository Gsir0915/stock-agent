# -*- coding: utf-8 -*-
"""
定时任务启动器
用于启动报告清理定时任务
"""

import argparse
import sys
import io

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="🕐 股票分析报告定时任务调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动定时任务调度器（默认每天 23:59:59 执行报告清理）
  python -m app.tasks.scheduler

  # 立即执行一次清理任务
  python -m app.tasks.cleanup_reports

  # 指定报告目录
  python -m app.tasks.scheduler --reports-dir /path/to/reports
        """
    )

    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="报告目录路径（默认：reports）"
    )

    parser.add_argument(
        "--keep-count",
        type=int,
        default=3,
        help="每个股票保留的报告数量（默认：3）"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="立即执行一次清理任务后退出，不启动调度器"
    )

    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    if args.once:
        # 立即执行一次清理任务
        from .cleanup_reports import cleanup_reports
        print("=" * 50)
        print("立即执行报告清理任务")
        print("=" * 50)
        result = cleanup_reports(args.reports_dir, args.keep_count)
        print(f"结果：{result['message']}")
        return 0 if result['success'] else 1
    else:
        # 启动定时任务调度器
        import os
        os.environ['REPORTS_DIR'] = args.reports_dir
        from .scheduler import start_scheduler
        start_scheduler()
        return 0


if __name__ == "__main__":
    sys.exit(main())
