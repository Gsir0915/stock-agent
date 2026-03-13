# -*- coding: utf-8 -*-
"""
回测日志模块

记录选股器选出的股票在未来 N 个交易日的表现，用于策略优化和验证。
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

import pandas as pd

# 添加项目根目录到路径，以便导入现有模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.data.downloader import DataDownloader
from app.data.repository import DataRepository


@dataclass
class StockSelection:
    """选股记录"""
    selection_date: str  # 选股日期
    stock_code: str  # 股票代码
    stock_name: str  # 股票名称
    entry_price: float  # 入选时价格
    quality_score: float  # 质量因子得分
    momentum_score: float  # 动量因子得分
    dividend_score: float  # 股息因子得分
    total_score: float  # 综合得分
    ranks: Dict[str, int]  # 各项排名


@dataclass
class BacktestResult:
    """回测结果"""
    selection: StockSelection  # 选股记录
    day_1_return: float  # 第 1 日收益率 (%)
    day_3_return: float  # 第 3 日累计收益率 (%)
    day_5_return: float  # 第 5 日累计收益率 (%)
    max_gain: float  # 期间最大收益率 (%)
    max_loss: float  # 期间最大回撤 (%)
    final_price: float  # 期末价格
    status: str  # 状态：completed/partial/failed


class BacktestLogger:
    """
    回测日志记录器

    功能:
    1. 记录每次选股的结果
    2. 跟踪选股后 5 个交易日的表现
    3. 保存回测数据到 JSON 文件
    4. 提供回测统计分析
    """

    def __init__(self, log_dir: str = "backtest_logs"):
        """
        初始化回测日志

        Args:
            log_dir: 日志文件保存目录
        """
        self.log_dir = Path(log_dir)
        self._ensure_log_dir()

        self.downloader = DataDownloader()
        self.repository = DataRepository()

        # 内存缓存
        self._selections: List[StockSelection] = []
        self._results: List[BacktestResult] = []

        # 加载现有日志
        self._load_existing_logs()

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self, date: Optional[str] = None) -> Path:
        """获取日志文件路径"""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"backtest_{date}.json"

    def _load_existing_logs(self):
        """加载现有的日志文件"""
        today = datetime.now().strftime("%Y%m%d")
        log_file = self._get_log_file_path(today)

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 加载选股记录
                for s in data.get("selections", []):
                    self._selections.append(StockSelection(**s))

                # 加载回测结果
                for r in data.get("results", []):
                    selection_data = r.get("selection", {})
                    selection = StockSelection(**selection_data)
                    result = BacktestResult(
                        selection=selection,
                        day_1_return=r.get("day_1_return", 0),
                        day_3_return=r.get("day_3_return", 0),
                        day_5_return=r.get("day_5_return", 0),
                        max_gain=r.get("max_gain", 0),
                        max_loss=r.get("max_loss", 0),
                        final_price=r.get("final_price", 0),
                        status=r.get("status", "pending")
                    )
                    self._results.append(result)

                print(f"已加载 {len(self._selections)} 条选股记录，{len(self._results)} 条回测结果")

            except Exception as e:
                print(f"[WARN] 加载日志文件失败：{e}")

    def log_selection(
        self,
        stock_code: str,
        stock_name: str,
        entry_price: float,
        quality_score: float,
        momentum_score: float,
        dividend_score: float,
        total_score: float,
        ranks: Optional[Dict[str, int]] = None,
        selection_date: Optional[str] = None
    ) -> StockSelection:
        """
        记录一次选股

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            entry_price: 入选时价格
            quality_score: 质量因子得分
            momentum_score: 动量因子得分
            dividend_score: 股息因子得分
            total_score: 综合得分
            ranks: 各项排名 (可选)
            selection_date: 选股日期 (默认今天)

        Returns:
            StockSelection 选股记录
        """
        if selection_date is None:
            selection_date = datetime.now().strftime("%Y-%m-%d")

        if ranks is None:
            ranks = {}

        selection = StockSelection(
            selection_date=selection_date,
            stock_code=stock_code,
            stock_name=stock_name,
            entry_price=entry_price,
            quality_score=quality_score,
            momentum_score=momentum_score,
            dividend_score=dividend_score,
            total_score=total_score,
            ranks=ranks
        )

        self._selections.append(selection)
        return selection

    def calculate_returns(
        self,
        stock_code: str,
        entry_price: float,
        start_date: str,
        trading_days: int = 5
    ) -> Dict[str, Any]:
        """
        计算股票在未来 N 个交易日的收益率

        Args:
            stock_code: 股票代码
            entry_price: 买入价格
            start_date: 起始日期 (选股日期的次日)
            trading_days: 交易日数量

        Returns:
            收益率字典
        """
        try:
            # 下载最新数据
            df = self.repository.load_stock_data(stock_code)
            if df is None:
                df = self.downloader.download_stock_history(stock_code)
                self.repository.save_stock_data(stock_code, df)

            if df is None or len(df) < 2:
                return {
                    "status": "failed",
                    "error": "无法获取股票数据"
                }

            # 确保日期列是 datetime 类型
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期").reset_index(drop=True)

            # 找到起始日期后的交易日
            start_dt = pd.to_datetime(start_date)
            future_data = df[df["日期"] > start_dt].head(trading_days)

            if len(future_data) == 0:
                return {
                    "status": "pending",
                    "message": "未来交易日数据不足，稍后重试"
                }

            # 计算每日收益率
            prices = future_data["收盘"].tolist()
            dates = future_data["日期"].tolist()

            # 计算各时间点的收益率
            day_1_return = 0.0
            day_3_return = 0.0
            day_5_return = 0.0
            max_gain = 0.0
            max_loss = 0.0

            for i, price in enumerate(prices):
                ret = (price - entry_price) / entry_price * 100

                if i == 0:  # 第 1 日
                    day_1_return = ret
                elif i == 2:  # 第 3 日
                    day_3_return = ret
                elif i == 4:  # 第 5 日
                    day_5_return = ret

                # 跟踪最大收益和最大回撤
                if ret > max_gain:
                    max_gain = ret
                if ret < max_loss:
                    max_loss = ret

            final_price = prices[-1] if prices else entry_price
            actual_days = len(prices)

            return {
                "status": "completed" if actual_days >= trading_days else "partial",
                "actual_days": actual_days,
                "day_1_return": round(day_1_return, 2),
                "day_3_return": round(day_3_return, 2),
                "day_5_return": round(day_5_return, 2),
                "max_gain": round(max_gain, 2),
                "max_loss": round(max_loss, 2),
                "final_price": round(final_price, 2),
                "prices": [round(p, 2) for p in prices],
                "dates": [str(d.date()) for d in dates]
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def update_results(
        self,
        selection_date: Optional[str] = None,
        trading_days: int = 5
    ) -> List[BacktestResult]:
        """
        更新回测结果

        Args:
            selection_date: 选股日期，None 则更新所有未完成的记录
            trading_days: 跟踪的交易日数量

        Returns:
            更新的回测结果列表
        """
        if selection_date is None:
            selection_date = datetime.now().strftime("%Y-%m-%d")

        # 找到指定日期的选股记录
        selections_to_update = [
            s for s in self._selections
            if s.selection_date == selection_date
        ]

        new_results = []
        today = datetime.now().strftime("%Y-%m-%d")

        for selection in selections_to_update:
            # 计算从选股次日开始的收益率
            # 选股当日不算，从下一个交易日开始计算
            result_data = self.calculate_returns(
                stock_code=selection.stock_code,
                entry_price=selection.entry_price,
                start_date=selection.selection_date,  # 选股日期，系统会自动找之后的交易日
                trading_days=trading_days
            )

            if result_data["status"] != "failed":
                result = BacktestResult(
                    selection=selection,
                    day_1_return=result_data.get("day_1_return", 0),
                    day_3_return=result_data.get("day_3_return", 0),
                    day_5_return=result_data.get("day_5_return", 0),
                    max_gain=result_data.get("max_gain", 0),
                    max_loss=result_data.get("max_loss", 0),
                    final_price=result_data.get("final_price", selection.entry_price),
                    status=result_data.get("status", "pending")
                )

                # 如果已有该记录则更新，否则添加
                existing_idx = None
                for i, r in enumerate(self._results):
                    if (r.selection.stock_code == selection.stock_code and
                        r.selection.selection_date == selection.selection_date):
                        existing_idx = i
                        break

                if existing_idx is not None:
                    self._results[existing_idx] = result
                else:
                    self._results.append(result)

                new_results.append(result)

        return new_results

    def save(self, date: Optional[str] = None) -> str:
        """
        保存日志到 JSON 文件

        Args:
            date: 日期字符串，None 则使用今天

        Returns:
            保存的文件路径
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        log_file = self._get_log_file_path(date)

        data = {
            "generated_at": datetime.now().isoformat(),
            "selections": [asdict(s) for s in self._selections],
            "results": [
                {
                    "selection": asdict(r.selection),
                    "day_1_return": r.day_1_return,
                    "day_3_return": r.day_3_return,
                    "day_5_return": r.day_5_return,
                    "max_gain": r.max_gain,
                    "max_loss": r.max_loss,
                    "final_price": r.final_price,
                    "status": r.status
                }
                for r in self._results
            ]
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] 回测日志已保存：{log_file}")
        return str(log_file)

    def get_statistics(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取回测统计信息

        Args:
            date: 日期字符串，None 则统计所有数据

        Returns:
            统计信息字典
        """
        results_to_analyze = self._results

        if date is not None:
            results_to_analyze = [
                r for r in self._results
                if r.selection.selection_date.startswith(date.replace("-", ""))
            ]

        if not results_to_analyze:
            return {"error": "没有可统计的回测数据"}

        # 过滤已完成的结果
        completed = [r for r in results_to_analyze if r.status == "completed"]

        if not completed:
            return {
                "total_selections": len(results_to_analyze),
                "completed": 0,
                "message": "回测数据不足，稍后重试"
            }

        # 计算胜率
        day_5_wins = sum(1 for r in completed if r.day_5_return > 0)
        day_5_win_rate = day_5_wins / len(completed) * 100

        day_1_wins = sum(1 for r in completed if r.day_1_return > 0)
        day_1_win_rate = day_1_wins / len(completed) * 100

        # 平均收益率
        avg_day_1_return = sum(r.day_1_return for r in completed) / len(completed)
        avg_day_3_return = sum(r.day_3_return for r in completed) / len(completed)
        avg_day_5_return = sum(r.day_5_return for r in completed) / len(completed)

        # 最大收益/回撤
        max_gain = max(r.max_gain for r in completed)
        max_loss = min(r.max_loss for r in completed)

        # 按综合得分分组的统计
        score_groups = {}
        for r in completed:
            score = r.selection.total_score
            group = "high" if score >= 0.6 else "medium" if score >= 0.4 else "low"
            if group not in score_groups:
                score_groups[group] = []
            score_groups[group].append(r.day_5_return)

        group_stats = {}
        for group, returns in score_groups.items():
            group_stats[group] = {
                "count": len(returns),
                "avg_return": sum(returns) / len(returns) if returns else 0,
                "win_rate": sum(1 for r in returns if r > 0) / len(returns) * 100 if returns else 0
            }

        return {
            "total_selections": len(results_to_analyze),
            "completed": len(completed),
            "pending": len(results_to_analyze) - len(completed),
            "day_1_win_rate": round(day_1_win_rate, 2),
            "day_5_win_rate": round(day_5_win_rate, 2),
            "avg_day_1_return": round(avg_day_1_return, 2),
            "avg_day_3_return": round(avg_day_3_return, 2),
            "avg_day_5_return": round(avg_day_5_return, 2),
            "max_gain": round(max_gain, 2),
            "max_loss": round(max_loss, 2),
            "score_group_stats": group_stats
        }

    def print_report(self, date: Optional[str] = None) -> None:
        """
        打印回测报告

        Args:
            date: 日期字符串，None 则打印所有数据
        """
        stats = self.get_statistics(date)

        print("\n" + "=" * 60)
        print("Stock Selector 回测报告")
        print("=" * 60)

        if "error" in stats:
            print(f"\n[WARN] {stats['error']}")
            print("=" * 60)
            return

        print(f"\n选股总数：{stats.get('total_selections', 0)}")
        print(f"已完成回测：{stats.get('completed', 0)}")
        print(f"待完成：{stats.get('pending', 0)}")

        if stats.get('completed', 0) == 0:
            print("\n[INFO] 回测数据不足，稍后重试")
            print("=" * 60)
            return

        print(f"\n收益率统计:")
        print(f"  T+1 胜率：{stats.get('day_1_win_rate', 0):.1f}%")
        print(f"  T+1 平均收益：{stats.get('avg_day_1_return', 0):.2f}%")
        print(f"  T+3 平均收益：{stats.get('avg_day_3_return', 0):.2f}%")
        print(f"  T+5 胜率：{stats.get('day_5_win_rate', 0):.1f}%")
        print(f"  T+5 平均收益：{stats.get('avg_day_5_return', 0):.2f}%")

        print(f"\n极值统计:")
        print(f"  最大收益：+{stats.get('max_gain', 0):.2f}%")
        print(f"  最大回撤：{stats.get('max_loss', 0):.2f}%")

        group_stats = stats.get('score_group_stats', {})
        if group_stats:
            print(f"\n按综合得分分组统计:")
            print(f"  {'得分区间':<12} {'样本数':>8} {'胜率':>10} {'平均收益':>10}")
            print(f"  {'-'*42}")
            for group, data in sorted(group_stats.items()):
                label = {
                    "high": "高分 (>=0.6)",
                    "medium": "中等 (0.4-0.6)",
                    "low": "低分 (<0.4)"
                }.get(group, group)
                print(f"  {label:<12} {data['count']:>8} {data['win_rate']:>9.1f}% "
                      f"{data['avg_return']:>+9.2f}%")

        print("\n" + "=" * 60)


# 全局默认日志记录器实例
_default_logger: Optional[BacktestLogger] = None


def get_backtest_logger(log_dir: str = "backtest_logs") -> BacktestLogger:
    """获取全局默认回测日志实例"""
    global _default_logger
    if _default_logger is None:
        _default_logger = BacktestLogger(log_dir)
    return _default_logger
