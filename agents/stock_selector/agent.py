# -*- coding: utf-8 -*-
"""多因子选股 Agent

封装 StockSelectorEngine，提供选股能力。
"""

from pathlib import Path
import sys
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agent_base import BaseAgent, AgentResult
from .engine import StockSelectorEngine, MarketRegime
from .factors import QualityFactor, MomentumFactor, DividendFactor
from .backtest_logger import get_backtest_logger


class SelectorAgent(BaseAgent):
    """多因子选股 Agent

    支持的命令:
    - scan: 全市场扫描
    - regime: 市场环境判断
    - weights: 获取当前因子权重
    """

    name = "stock-selector"
    description = "多因子选股 Agent，基于质量、动量、股息等因子进行股票筛选"

    def __init__(self, config_path: Optional[str] = None):
        """初始化选股 Agent

        Args:
            config_path: 配置文件路径
        """
        self.engine = StockSelectorEngine(config_path)

    def execute(self, command: str, **kwargs) -> AgentResult:
        """执行命令

        Args:
            command: 命令名称 (scan/regime/weights)
            **kwargs: 命令参数

        Returns:
            AgentResult 执行结果
        """
        if command == "scan":
            return self._execute_scan(**kwargs)
        elif command == "regime":
            return self._execute_regime(**kwargs)
        elif command == "weights":
            return self._execute_weights(**kwargs)
        else:
            return AgentResult.fail(f"Unknown command: {command}")

    def get_capabilities(self) -> List[str]:
        """返回支持的命令列表"""
        return ["scan", "regime", "weights"]

    def _execute_scan(self, **kwargs) -> AgentResult:
        """执行全市场扫描

        Args:
            **kwargs: 参数包括 stock_pool, top_n, data_dir 等

        Returns:
            AgentResult 执行结果
        """
        stock_pool = kwargs.get("stock_pool", [])
        top_n = kwargs.get("top_n", 10)
        data_dir = kwargs.get("data_dir", "data")
        use_filters = kwargs.get("use_filters", True)

        if not stock_pool:
            return AgentResult.fail("stock_pool 不能为空")

        try:
            # 获取市场环境和权重
            try:
                regime = self.engine.determine_market_regime()
                weights = self.engine.get_current_weights()
                print(f"当前市场模式：{regime.regime_name}")
                print(f"因子权重：{weights}")
            except Exception as e:
                print(f"[WARN] 获取市场环境失败：{e}")
                weights = {"quality": 0.25, "momentum": 0.25, "dividend": 0.25, "valuation": 0.25}

            # 执行扫描
            results = self._run_scan(
                stock_pool=stock_pool,
                top_n=top_n,
                data_dir=data_dir,
                use_filters=use_filters,
                weights=weights
            )

            return AgentResult.ok(
                data=results,
                message=f"扫描完成，返回 Top {len(results)} 只股票"
            )

        except Exception as e:
            return AgentResult.fail(f"扫描失败：{e}")

    def _run_scan(
        self,
        stock_pool: List[str],
        top_n: int,
        data_dir: str,
        use_filters: bool,
        weights: Dict[str, float]
    ) -> List[Dict]:
        """执行扫描逻辑

        Args:
            stock_pool: 股票代码池
            top_n: 返回前 N 只
            data_dir: 数据目录
            use_filters: 是否使用过滤
            weights: 因子权重

        Returns:
            选股结果列表
        """
        from app.data.downloader import DataDownloader
        from app.data.repository import DataRepository
        from app.utils.stock_names import StockNameService

        downloader = DataDownloader()
        repository = DataRepository(data_dir)
        bt_logger = get_backtest_logger()

        quality_factor = QualityFactor()
        momentum_factor = MomentumFactor()
        dividend_factor = DividendFactor()

        results = []
        processed = 0
        errors = 0

        for code in stock_pool:
            processed += 1
            if processed % 100 == 0:
                print(f"进度：{processed}/{len(stock_pool)} - 成功：{len(results)} - 错误：{errors}")

            name = StockNameService.get_name(code)

            try:
                # 获取股票数据
                df = repository.load_stock_data(code)
                if df is None or len(df) < 60:
                    df = downloader.download_stock_history(code)
                    repository.save_stock_data(code, df)

                if df is None or len(df) < 60:
                    errors += 1
                    continue

                # 获取基本面数据
                fundamentals = downloader.get_fundamentals(code)
                if not name and fundamentals:
                    name = fundamentals.get("name", code)

                # 动量因子数据
                latest = df.iloc[-1]
                current_price = float(latest["收盘"])
                current_volume = float(latest.get("成交量", 0))
                high_20 = float(df["收盘"].tail(20).max())
                low_20 = float(df["收盘"].tail(20).min())
                avg_volume_20 = float(df["成交量"].tail(20).mean())

                momentum_data = {
                    "current_price": current_price,
                    "high_20": high_20,
                    "low_20": low_20,
                    "current_volume": current_volume,
                    "avg_volume_20": avg_volume_20,
                }

                # 质量因子数据
                profit_growth = fundamentals.get("profit_growth", 0) if fundamentals else 0
                quality_data = {
                    "fcf": fundamentals.get("fcf", 1) if fundamentals else 1,
                    "net_profit": fundamentals.get("net_profit", 1) if fundamentals else 1,
                    "net_profit_growth": profit_growth,
                }

                # 股息因子数据
                dividend_data = {
                    "dividend_yield": fundamentals.get("dividend_yield", 2.5) if fundamentals else 2.5,
                    "consecutive_years": fundamentals.get("consecutive_years", 3) if fundamentals else 3,
                    "payout_ratio": fundamentals.get("payout_ratio", 40) if fundamentals else 40,
                }

                # 计算因子得分
                quality_score = quality_factor.run(quality_data)
                momentum_score = momentum_factor.run(momentum_data)
                dividend_score = dividend_factor.run(dividend_data)

                # 加权计算综合得分
                total_score = (
                    quality_score * weights.get("quality", 0.25) +
                    momentum_score * weights.get("momentum", 0.25) +
                    dividend_score * weights.get("dividend", 0.25) +
                    0.5 * weights.get("valuation", 0.25)
                )

                results.append({
                    "code": code,
                    "name": name or code,
                    "quality_score": quality_score,
                    "momentum_score": momentum_score,
                    "dividend_score": dividend_score,
                    "total_score": total_score,
                    "price": current_price,
                })

                # 记录回测日志
                bt_logger.log_selection(
                    stock_code=code,
                    stock_name=name or code,
                    entry_price=current_price,
                    quality_score=quality_score,
                    momentum_score=momentum_score,
                    dividend_score=dividend_score,
                    total_score=total_score,
                    ranks={"total": len(results)}
                )

            except Exception as e:
                errors += 1
                continue

        # 按总分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # 保存回测日志
        bt_logger.save()

        return results[:top_n]

    def _execute_regime(self, **kwargs) -> AgentResult:
        """执行市场环境判断

        Returns:
            AgentResult 执行结果
        """
        try:
            regime = self.engine.determine_market_regime()
            return AgentResult.ok(
                data={
                    "regime_name": regime.regime_name,
                    "volume_level": regime.volume_level,
                    "trend_type": regime.trend_type,
                    "total_turnover": regime.total_turnover,
                    "sh_index_close": regime.sh_index_close,
                    "sh_ma120": regime.sh_ma120,
                },
                message=f"市场模式：{regime.regime_name}"
            )
        except Exception as e:
            return AgentResult.fail(f"判断市场环境失败：{e}")

    def _execute_weights(self, **kwargs) -> AgentResult:
        """获取当前因子权重

        Returns:
            AgentResult 执行结果
        """
        try:
            weights = self.engine.get_current_weights()
            return AgentResult.ok(
                data=weights,
                message=f"当前因子权重：{weights}"
            )
        except Exception as e:
            return AgentResult.fail(f"获取权重失败：{e}")
