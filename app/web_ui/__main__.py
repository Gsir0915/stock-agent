# -*- coding: utf-8 -*-
"""
海龟交易监控系统 - Web 界面启动入口

使用方式:
    python -m app.web_ui              # 启动 Web 服务器（默认 8080 端口）
    python -m app.web_ui --port 8000  # 指定端口
"""

import argparse
import uvicorn
from pathlib import Path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🐢 海龟交易监控系统 - Web 界面"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP 服务器端口（默认：8080）"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址（默认：0.0.0.0）"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（开发模式）"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="日志级别（默认：info）"
    )

    args = parser.parse_args()

    # 确保数据目录存在
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🐢 海龟交易监控系统 - Web 界面                           ║
║                                                           ║
║   访问地址：http://localhost:{args.port}                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

正在启动服务器...
""")

    uvicorn.run(
        "app.web_ui:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()
