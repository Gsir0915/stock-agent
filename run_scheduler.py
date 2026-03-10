# -*- coding: utf-8 -*-
"""
定时任务运行器 - 可作为独立服务运行
使用方式: python run_scheduler.py
"""

import os
import sys
import io

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks.scheduler import start_scheduler

if __name__ == "__main__":
    start_scheduler()
