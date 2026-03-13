# -*- coding: utf-8 -*-
"""海龟交易法则选股 Agent

封装 TurtleScreener，提供股票筛选和监控能力。
"""

from pathlib import Path
import sys
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agent_base import BaseAgent, AgentResult
from app.core.turtle import TurtleScreener, TurtleConfig, TurtleSignal
from app.data.repository import DataRepository, get_repository
from app.data.downloader import DataDownloader
from app.utils.stock_names import StockNameService


class TurtleScreenerAgent(BaseAgent):
    """海龟交易法则选股 Agent

    支持的命令:
    - check: 检查单只股票
    - scan: 扫描股票池
    - monitor: 查看持仓监控
    """

    name = "turtle-screener"
    description = "海龟交易法则选股 Agent，基于突破信号和 ATR 指标进行选股"

    def __init__(
        self,
        data_dir: str = "data",
        capital: float = 100000,
        config: Optional[TurtleConfig] = None
    ):
        """初始化海龟选股 Agent

        Args:
            data_dir: 数据目录
            capital: 每只股票可用资金
            config: 海龟交易配置
        """
        self.data_dir = data_dir
        self.capital = capital
        self.config = config or TurtleConfig()
        self.screener = TurtleScreener(self.config)
        self.repository = get_repository(data_dir)
        self.downloader = DataDownloader()

    def execute(self, command: str, **kwargs) -> AgentResult:
        """执行命令

        Args:
            command: 命令名称 (check/scan/monitor)
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        if command == "check":
            return self._execute_check(**kwargs)
        elif command == "scan":
            return self._execute_scan(**kwargs)
        elif command == "monitor":
            return self._execute_monitor(**kwargs)
        else:
            return AgentResult.fail(f"Unknown command: {command}")

    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表"""
        return ["check", "scan", "monitor"]

    def _execute_check(
        self,
        code: str,
        download: bool = True,
        **kwargs
    ) -> AgentResult:
        """检查单只股票

        Args:
            code: 股票代码
            download: 是否下载最新数据
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        try:
            name = StockNameService.get_name(code)

            # 获取股票数据
            df = self.repository.load_stock_data(code)
            if df is None or len(df) < self.config.min_history_days:
                if download:
                    df = self.downloader.download_stock_history(code)
                    self.repository.save_stock_data(code, df)
                else:
                    return AgentResult.fail(f"数据不足且未开启下载")

            if df is None or len(df) < self.config.min_history_days:
                return AgentResult.fail(f"数据量不足，至少需要 {self.config.min_history_days} 条记录")

            # 执行海龟选股检查
            signal = self.screener.check_stock(code, name, df, self.capital)

            if not signal.success:
                return AgentResult.fail(signal.error)

            return AgentResult.ok(
                data={
                    "code": code,
                    "name": name,
                    "breakout": signal.breakout,
                    "current_price": signal.current_price,
                    "twenty_day_high": signal.twenty_day_high,
                    "days_since_high": signal.days_since_high,
                    "atr_current": signal.atr_current,
                    "atr_trend": signal.atr_trend,
                    "position_size": signal.position_size,
                    "stop_loss_price": signal.stop_loss_price,
                    "risk_amount": signal.risk_amount,
                },
                message=f"{name} ({code}) {'突破' if signal.breakout else '未突破'} 20 日高点"
            )

        except Exception as e:
            return AgentResult.fail(f"检查失败：{e}")

    def _execute_scan(
        self,
        stock_pool: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AgentResult:
        """扫描股票池

        Args:
            stock_pool: 股票池列表，每项包含 code 和 name
            **kwargs: 其他参数

        Returns:
            AgentResult 执行结果
        """
        # 默认股票池
        if stock_pool is None:
            stock_pool = [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000858", "name": "五粮液"},
                {"code": "601318", "name": "中国平安"},
                {"code": "600036", "name": "招商银行"},
                {"code": "002415", "name": "海康威视"},
                {"code": "300750", "name": "宁德时代"},
                {"code": "600276", "name": "恒瑞医药"},
                {"code": "000538", "name": "云南白药"},
                {"code": "600585", "name": "海螺水泥"},
                {"code": "601088", "name": "中国神华"},
            ]

        results = []
        breakout_count = 0

        for stock in stock_pool:
            code = stock.get("code")
            name = stock.get("name", code)

            try:
                # 获取数据
                df = self.repository.load_stock_data(code)
                if df is None or len(df) < self.config.min_history_days:
                    df = self.downloader.download_stock_history(code)
                    self.repository.save_stock_data(code, df)

                if df is None or len(df) < self.config.min_history_days:
                    continue

                # 执行检查
                signal = self.screener.check_stock(code, name, df, self.capital)

                if signal.success:
                    result = {
                        "code": code,
                        "name": name,
                        "price": signal.current_price,
                        "breakout": signal.breakout,
                        "atr_trend": signal.atr_trend,
                        "position_size": signal.position_size,
                        "stop_loss": signal.stop_loss_price,
                    }
                    results.append(result)

                    if signal.breakout:
                        breakout_count += 1

            except Exception as e:
                continue

        return AgentResult.ok(
            data={
                "total": len(results),
                "breakout_count": breakout_count,
                "stocks": results,
            },
            message=f"扫描完成：共 {len(results)} 只，{breakout_count} 只突破"
        )

    def _execute_monitor(self, **kwargs) -> AgentResult:
        """查看持仓监控

        Args:
            **kwargs: 参数包括 positions 等

        Returns:
            AgentResult 执行结果
        """
        positions = kwargs.get("positions", [])

        if not positions:
            return AgentResult.fail("未提供持仓信息")

        results = []

        for position in positions:
            code = position.get("code")
            cost = position.get("cost", 0)
            units = position.get("units", 0)

            try:
                name = StockNameService.get_name(code)

                # 获取最新数据
                df = self.repository.load_stock_data(code)
                if df is None or len(df) < self.config.min_history_days:
                    df = self.downloader.download_stock_history(code)

                if df is None:
                    continue

                # 获取最新价格
                latest_price = float(df.iloc[-1]["收盘"])

                # 计算盈亏
                pnl = (latest_price - cost) * units
                pnl_percent = ((latest_price - cost) / cost) * 100 if cost > 0 else 0

                # 检查海龟退出信号
                signal = self.screener.check_stock(code, name, df, self.capital)

                results.append({
                    "code": code,
                    "name": name,
                    "cost": cost,
                    "units": units,
                    "current_price": latest_price,
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                    "exit_signal": signal.exit_signal if hasattr(signal, 'exit_signal') else "",
                })

            except Exception as e:
                continue

        return AgentResult.ok(
            data=results,
            message=f"监控 {len(results)} 只持仓"
        )
