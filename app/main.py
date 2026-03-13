# -*- coding: utf-8 -*-
"""
股票智能体应用入口 (CLI)
基于多 Agent 架构的统一命令行入口
"""

import argparse
import sys
import io
from pathlib import Path
from typing import List, Optional

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.router import AgentRouter
from core.agent_base import AgentResult
from app.utils.stock_names import StockNameService
from app.config import get_config


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="🤖 股票智能体 - 多 Agent 架构股票分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 列出所有 Agent
  python -m app.main --list-agents

  # 使用 stock-analyzer 分析个股
  python -m app.main stock-analyzer analyze 600519
  python -m app.main stock-analyzer technical 600519
  python -m app.main stock-analyzer fundamental 600519
  python -m app.main stock-analyzer sentiment 600519

  # 使用 turtle-screener 选股
  python -m app.main turtle-screener check 600519
  python -m app.main turtle-screener scan

  # 使用 stock-selector 多因子选股
  python -m app.main stock-selector scan --top-n 10
  python -m app.main stock-selector regime

兼容模式 (旧命令):
  python -m app.main 600519                    # 分析个股 (兼容旧命令)
  python -m app.main --scan                   # 选股扫描 (兼容旧命令)
  python -m app.main --backtest               # 回测统计 (兼容旧命令)
        """
    )

    # Agent 命令模式参数
    parser.add_argument(
        "agent",
        nargs="?",
        default=None,
        help="目标 Agent 名称 (stock-analyzer / turtle-screener / stock-selector)"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help="命令名称"
    )
    parser.add_argument(
        "cmd_args",
        nargs="*",
        default=None,
        help="命令参数"
    )

    # 全局选项
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="列出所有可用的 Agent"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="数据目录 (默认：data)"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="不使用下载，使用本地缓存"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="不使用 AI 分析"
    )
    parser.add_argument(
        "--feishu",
        action="store_true",
        help="发送飞书通知"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="选股数量 (stock-selector scan 专用)"
    )
    parser.add_argument(
        "--sector",
        type=str,
        default=None,
        help="板块/概念 (hot-news fetch 专用)"
    )
    parser.add_argument(
        "--sentiment",
        type=str,
        default="all",
        choices=["positive", "negative", "all"],
        help="情绪筛选 (hot-news fetch 专用)"
    )

    # 兼容旧命令参数
    parser.add_argument(
        "--scan",
        action="store_true",
        help="[兼容] 运行选股扫描"
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="[兼容] 更新回测结果"
    )
    parser.add_argument(
        "--pool",
        nargs="*",
        default=None,
        help="[兼容] 股票池"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="[兼容] 报告输出目录"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="[兼容] 日志级别"
    )

    return parser


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("🤖 股票智能体 v3.0 - 多 Agent 架构")
    print("主 Agent 协调 | 子 Agent 执行 | 模块化设计")
    print("=" * 70)


def run_legacy_mode(args):
    """运行兼容模式（旧命令）"""
    from app.main_legacy import main as legacy_main
    return legacy_main()


def detect_mode(args):
    """
    检测运行模式

    Returns:
        str: 'legacy' 或 'agent' 或 'help'
    """
    # 兼容模式：--scan, --backtest, 或第一个位置参数是股票代码
    if args.scan or args.backtest:
        return 'legacy'

    # 检查第一个位置参数是否是股票代码（数字开头）
    if args.agent and args.command is None and args.cmd_args is None:
        # 只有一个位置参数，可能是股票代码
        if args.agent.isdigit() or args.agent.startswith(('sh', 'sz')):
            return 'legacy'

    # 检查是否有两个位置参数且第二个是命令
    if args.agent and args.command:
        # 如果 agent 是已知的 Agent 名称，则是 agent 模式
        known_agents = ['stock-analyzer', 'turtle-screener', 'stock-selector', 'hot-news']
        if args.agent in known_agents:
            return 'agent'

    # 列出 Agent 模式
    if args.list_agents:
        return 'help'

    # 没有匹配任何模式，显示帮助
    return 'help'


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 检测运行模式
    mode = detect_mode(args)

    if mode == 'legacy':
        # 兼容模式
        return run_legacy_mode(args)

    elif mode == 'agent':
        # Agent 命令模式
        try:
            # 初始化路由
            router = AgentRouter(auto_register=True)

            # 检查 Agent 是否存在
            if args.agent not in router.list_agents():
                print(f"❌ 错误：未知的 Agent '{args.agent}'")
                print(f"可用的 Agent: {router.list_agents()}")
                return 1

            # 解析命令参数
            cmd_kwargs = {
                "data_dir": args.data_dir,
                "download": not args.no_download,
                "use_ai": not args.no_ai,
            }

            # 从 cmd_args 中提取命名参数和位置参数
            if args.cmd_args:
                # 第一个位置参数通常是 code
                if args.cmd_args:
                    cmd_kwargs["code"] = args.cmd_args[0]

            # 特殊处理 stock-selector 的 scan 命令
            if args.agent == "stock-selector" and args.command == "scan":
                # 支持 --pool 参数传递单只股票或多只股票
                if args.pool:
                    cmd_kwargs["stock_pool"] = args.pool
                else:
                    cmd_kwargs["stock_pool"] = load_stock_pool()
                # 优先从全局参数获取 top_n，如果没有则使用默认值
                cmd_kwargs["top_n"] = args.top_n if args.top_n is not None else 10

            # 特殊处理 hot-news 的 fetch 命令
            if args.agent == "hot-news" and args.command == "fetch":
                # 从全局参数获取 top_n, sector, sentiment
                cmd_kwargs["top_n"] = args.top_n if args.top_n is not None else 10
                cmd_kwargs["sector"] = args.sector if args.sector else None
                cmd_kwargs["sentiment"] = args.sentiment if args.sentiment else "all"

            # 执行命令
            result = router.dispatch(args.agent, args.command, **cmd_kwargs)

            # 处理结果
            if result.success:
                print_result(result)
                return 0
            else:
                print(f"❌ 执行失败：{result.error or result.message}")
                return 1

        except Exception as e:
            print(f"❌ 错误：{e}")
            import traceback
            traceback.print_exc()
            return 1

    else:
        # 帮助模式
        print_banner()
        print()

        # 列出所有 Agent
        router = AgentRouter(auto_register=True)
        agents = router.list_agents()
        capabilities = router.get_all_capabilities()

        print(f"已注册 {len(agents)} 个 Agent:\n")

        for agent_name in agents:
            agent = router.get_agent(agent_name)
            caps = capabilities.get(agent_name, [])
            print(f"  • {agent_name}: {agent.description}")
            print(f"    支持命令：{', '.join(caps) if caps else '无'}")
            print()

        parser.print_help()
        return 0


def load_stock_pool() -> List[str]:
    """加载股票池"""
    pool_file = "data/stock_pool_all.txt"
    try:
        with open(pool_file, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]
        return codes
    except FileNotFoundError:
        print(f"⚠️  股票池文件不存在：{pool_file}")
        return []


def print_result(result: AgentResult):
    """打印 Agent 执行结果"""
    if result.data is None:
        print(result.message or "执行完成")
        return

    # 根据数据类型打印
    if isinstance(result.data, dict):
        print("=" * 70)
        for key, value in result.data.items():
            if isinstance(value, list):
                print(f"\n{key}:")
                for item in value[:5]:  # 只显示前 5 项
                    if isinstance(item, dict):
                        print(f"  - {item}")
                    else:
                        print(f"  - {item}")
                if len(value) > 5:
                    print(f"  ... 还有 {len(value) - 5} 项")
            else:
                print(f"{key}: {value}")
        print("=" * 70)
    elif isinstance(result.data, list):
        print(f"结果数量：{len(result.data)}")
        for i, item in enumerate(result.data[:10]):
            print(f"{i + 1}. {item}")
        if len(result.data) > 10:
            print(f"... 还有 {len(result.data) - 10} 项")
    else:
        print(result.data)

    if result.message:
        print(f"\n{result.message}")


if __name__ == "__main__":
    sys.exit(main())
