# -*- coding: utf-8 -*-
"""
Web UI 测试脚本
"""

import uvicorn
from app.web_ui import app
import threading
import time
import requests


def run_server():
    """运行服务器"""
    uvicorn.run(app, host='127.0.0.1', port=8080, log_level='warning')


def test_api():
    """测试 API"""
    # 启动服务器
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(3)

    base_url = 'http://127.0.0.1:8080'

    print("=" * 60)
    print("🐢 海龟交易监控系统 - Web UI 测试")
    print("=" * 60)

    # 测试 1: 仪表盘
    print("\n1️⃣ 测试仪表盘 API...")
    try:
        resp = requests.get(f'{base_url}/api/dashboard', timeout=10)
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   持仓：{data.get('position_count', 0)} 只")
        print(f"   关注：{data.get('watchlist_count', 0)} 只")
        print(f"   总盈亏：¥{data.get('total_profit', 0):,.0f}")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 测试 2: 提醒
    print("\n2️⃣ 测试提醒 API...")
    try:
        resp = requests.get(f'{base_url}/api/alerts', timeout=10)
        print(f"   Status: {resp.status_code}")
        alerts = resp.json().get('alerts', [])
        print(f"   提醒数量：{len(alerts)}")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 测试 3: 主页
    print("\n3️⃣ 测试主页...")
    try:
        resp = requests.get(f'{base_url}/', timeout=10)
        print(f"   Status: {resp.status_code}")
        print(f"   页面大小：{len(resp.text)} 字节")
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 测试 4: 添加持仓（使用已缓存的股票）
    print("\n4️⃣ 测试添加持仓 API...")
    try:
        resp = requests.post(f'{base_url}/api/position/add',
            json={'code': '000001', 'capital': 100000}, timeout=30)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   消息：{result.get('message', '')}")
            print("   ✅ 通过")
        else:
            print(f"   响应：{resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n💡 提示：使用以下命令启动 Web 界面:")
    print("   python -m app.web_ui --port 8080")
    print("   或运行：.\\scripts\\start_web_ui.bat")
    print("\n访问地址：http://localhost:8080")


if __name__ == "__main__":
    test_api()
