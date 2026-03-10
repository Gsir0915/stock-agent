# -*- coding: utf-8 -*-
"""
定时清理报告文件任务
保留每个股票编码最新的 3 条报告数据
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def get_stock_code_from_filename(filename: str) -> str | None:
    """从报告文件名中提取股票代码"""
    # 匹配格式：600519_贵州茅台_20260307_143022.md
    match = re.match(r'^(\d{6})_', filename)
    if match:
        return match.group(1)
    return None


def get_report_timestamp(filename: str) -> datetime | None:
    """从报告文件名中提取时间戳"""
    # 匹配格式：600519_贵州茅台_20260307_143022.md
    match = re.search(r'_(\d{8})_(\d{6})\.md$', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except ValueError:
            return None
    return None


def cleanup_reports(reports_dir: str, keep_count: int = 3) -> dict:
    """
    清理报告文件，每个股票只保留最新的 N 条

    Args:
        reports_dir: 报告目录路径
        keep_count: 每个股票保留的报告数量，默认 3 条

    Returns:
        清理结果统计
    """
    reports_path = Path(reports_dir)

    if not reports_path.exists():
        return {
            'success': True,
            'message': '报告目录不存在',
            'deleted_count': 0,
            'deleted_files': []
        }

    # 收集所有报告文件
    stock_reports = defaultdict(list)

    for file in reports_path.iterdir():
        if file.is_file() and file.suffix == '.md':
            stock_code = get_stock_code_from_filename(file.name)
            if stock_code:
                timestamp = get_report_timestamp(file.name)
                if timestamp:
                    stock_reports[stock_code].append({
                        'path': file,
                        'timestamp': timestamp
                    })

    # 清理旧报告
    deleted_files = []
    deleted_count = 0

    for stock_code, reports in stock_reports.items():
        if len(reports) > keep_count:
            # 按时间戳排序，最新的在前
            sorted_reports = sorted(
                reports,
                key=lambda x: x['timestamp'],
                reverse=True
            )

            # 删除超出数量的旧报告
            for report in sorted_reports[keep_count:]:
                try:
                    report['path'].unlink()
                    deleted_files.append(report['path'].name)
                    deleted_count += 1
                    print(f"已删除：{report['path'].name}")
                except Exception as e:
                    print(f"删除失败 {report['path'].name}: {e}")

    return {
        'success': True,
        'message': f'清理完成，共删除 {deleted_count} 条报告',
        'deleted_count': deleted_count,
        'deleted_files': deleted_files
    }


def run_cleanup_task():
    """执行清理任务"""
    print("=" * 50)
    print("开始执行报告清理任务")
    print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 获取报告目录（从环境变量或默认值）
    reports_dir = os.environ.get('REPORTS_DIR', 'reports')

    result = cleanup_reports(reports_dir, keep_count=3)

    print("=" * 50)
    print(f"任务完成：{result['message']}")
    print("=" * 50)

    return result


if __name__ == "__main__":
    run_cleanup_task()
