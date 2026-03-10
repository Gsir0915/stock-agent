# -*- coding: utf-8 -*-
"""
飞书机器人启动入口
使用 python -m app.bot 启动 HTTP 服务器
"""

import argparse
import sys
import io

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from .server import run_server
from .handler import MessageHandler
from .feishu_client import FeishuClient
from ..config import get_config
from ..utils.logger import setup_logger, get_logger


def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("🤖 飞书股票分析机器人")
    print("在飞书群中@机器人并发送股票代码，自动执行分析并回复报告")
    print("=" * 70)


def print_config_info():
    """打印配置信息"""
    config = get_config()

    print("\n📋 配置检查:")
    print(f"  监听端口：{config.feishu_bot_port}")

    # 飞书机器人配置
    if config.has_feishu_bot_config:
        print(f"  飞书 AppID: {config.feishu_app_id[:10]}... ✅")
        print(f"  飞书 AppSecret: 已配置 ✅")
        print(f"  验证 Token: 已配置 ✅")
    else:
        print(f"  ⚠️  飞书机器人配置不完整，请检查环境变量:")
        print(f"     - FEISHU_APP_ID")
        print(f"     - FEISHU_APP_SECRET")
        print(f"     - FEISHU_VERIFICATION_TOKEN")

    # AI 配置
    if config.has_ai_api:
        print(f"  AI 分析：已启用 ✅")
    else:
        print(f"  ⚠️  AI 分析：未配置 ANTHROPIC_API_KEY")

    # 数据配置
    print(f"  数据目录：{config.data_dir}")
    print(f"  报告目录：{config.reports_dir}")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="🤖 飞书股票分析机器人 - HTTP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
启动飞书机器人 HTTP 服务器，接收飞书事件推送。

使用前请确保:
1. 已在飞书开放平台创建应用并获取 AppID/AppSecret
2. 已配置事件订阅 URL（公网可访问）
3. 已订阅 im.message.receive_v1 事件

示例:
  # 使用默认配置启动
  python -m app.bot

  # 指定端口
  python -m app.bot --port 9000

  # 指定日志级别
  python -m app.bot --log-level DEBUG
        """
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听地址（默认：0.0.0.0）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口（默认：从 FEISHU_BOT_PORT 环境变量读取，或 8080）"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认：INFO）"
    )

    return parser


def main():
    """主函数"""
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()

    # 设置日志
    logger = setup_logger(
        name="feishu_bot",
        level=args.log_level
    )

    # 打印横幅
    print_banner()
    print_config_info()

    # 检查必要配置
    config = get_config()
    if not config.has_feishu_bot_config:
        print("\n❌ 错误：飞书机器人配置不完整")
        print("请在 .env 文件中配置以下环境变量:")
        print("  - FEISHU_APP_ID")
        print("  - FEISHU_APP_SECRET")
        print("  - FEISHU_VERIFICATION_TOKEN")
        print("\n启动即将继续，但机器人将无法正常工作...")

    print("\n" + "=" * 70)
    print("正在启动服务器...")
    print("=" * 70)

    # 启动服务器
    try:
        run_server(
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower()
        )
    except KeyboardInterrupt:
        print("\n\n收到退出信号，正在关闭...")
        print("服务器已停止")
    except Exception as e:
        logger.exception(f"服务器异常：{e}")
        print(f"\n❌ 服务器启动失败：{e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
