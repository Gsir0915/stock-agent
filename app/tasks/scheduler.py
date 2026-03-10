# -*- coding: utf-8 -*-
"""
定时任务调度器
"""

import schedule
import time
import sys
from datetime import datetime

from .cleanup_reports import run_cleanup_task


def start_scheduler():
    """启动定时任务调度器"""
    print("=" * 50)
    print("🕐 定时任务调度器启动")
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 每天 23:59:59 执行清理任务
    schedule.every().day.at("23:59:59").do(run_cleanup_task)

    print("已注册任务：")
    print("  - 报告清理任务：每天 23:59:59 执行")
    print("=" * 50)
    print("按 Ctrl+C 停止调度器...\n")

    # 运行调度器
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n调度器已停止")
        sys.exit(0)


if __name__ == "__main__":
    start_scheduler()
