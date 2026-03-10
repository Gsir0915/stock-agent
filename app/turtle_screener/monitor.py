# -*- coding: utf-8 -*-
"""
海龟交易监控器
监控持仓股票的价格、止损、加仓等状态
"""

import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from ..core.turtle import TurtleScreener, TurtleConfig, TurtleSignal
from ..data.downloader import DataDownloader
from ..data.repository import get_repository
from ..utils.logger import get_logger
from ..utils.stock_names import StockNameService

logger = get_logger("turtle_monitor")


@dataclass
class PositionInfo:
    """持仓信息"""
    code: str  # 股票代码
    name: str  # 股票名称

    # 入场信息
    entry_price: float  # 入场价格
    entry_date: str  # 入场日期
    units: int  # 当前持仓单位数 (1-4)

    # 头寸信息
    shares_per_unit: int  # 每单位股数
    total_shares: int  # 总股数
    total_cost: float  # 总成本

    # 止损信息
    initial_stop: float  # 初始止损价
    current_stop: float  # 当前移动止损价
    stop_n: int  # 止损 N 值 (默认 2)
    atr: float  # ATR 值

    # 加仓信息
    add_unit_window: float  # 加仓窗口 (0.5N)
    add_prices: List[float]  # 加仓价格列表
    filled_add_prices: List[float] = field(default_factory=list)  # 已触发的加仓价格

    # 当前状态
    current_price: float = 0.0  # 当前价格
    market_value: float = 0.0  # 市值
    profit_loss: float = 0.0  # 盈亏金额
    profit_loss_pct: float = 0.0  # 盈亏比例

    # 信号状态
    is_breakout: bool = False  # 是否突破
    is_add_triggered: bool = False  # 是否触发加仓
    is_stop_triggered: bool = False  # 是否触发止损
    exit_signal: str = ""  # 退出信号


@dataclass
class WatchStock:
    """关注股票"""
    code: str  # 股票代码
    name: str  # 股票名称
    breakout_price: float  # 突破价格
    current_price: float = 0.0  # 当前价格
    atr: float = 0.0  # ATR
    add_prices: List[float] = field(default_factory=list)  # 加仓价格
    stop_price: float = 0.0  # 止损价

    # 信号
    is_breakout: bool = False  # 是否突破
    is_add_triggered: List[bool] = field(default_factory=list)  # 各加仓位是否触发


class TurtleMonitor:
    """海龟交易监控器"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化监控器

        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir
        self.repository = get_repository(data_dir)
        self.downloader = DataDownloader()
        self.screener = TurtleScreener()

        # 持仓列表
        self.positions: List[PositionInfo] = []

        # 关注列表（等待突破）
        self.watchlist: List[WatchStock] = []

    def add_position(self, position: PositionInfo):
        """添加持仓"""
        self.positions.append(position)
        logger.info(f"添加持仓：{position.code} {position.name}")

    def remove_position(self, code: str):
        """移除持仓"""
        self.positions = [p for p in self.positions if p.code != code]
        logger.info(f"移除持仓：{code}")

    def add_to_watchlist(self, stock: WatchStock):
        """添加到关注列表"""
        self.watchlist.append(stock)
        logger.info(f"添加关注：{stock.code} {stock.name}")

    def update_prices(self) -> Dict[str, Any]:
        """
        更新所有股票价格

        Returns:
            更新结果
        """
        results = {
            "positions_updated": 0,
            "watchlist_updated": 0,
            "alerts": []
        }

        # 更新持仓
        for position in self.positions:
            result = self._update_position(position)
            if result:
                results["positions_updated"] += 1
                if result["alerts"]:
                    results["alerts"].extend(result["alerts"])

        # 更新关注列表
        for stock in self.watchlist:
            result = self._update_watchlist_stock(stock)
            if result:
                results["watchlist_updated"] += 1
                if result["alerts"]:
                    results["alerts"].extend(result["alerts"])

        return results

    def _update_position(self, position: PositionInfo) -> Optional[Dict[str, Any]]:
        """更新单个持仓"""
        try:
            # 获取最新数据
            df = self.repository.load_stock_data(position.code)
            if df is None:
                df = self.downloader.download_stock_history(position.code)

            if df is None or len(df) < 2:
                return None

            latest = df.iloc[-1]
            position.current_price = float(latest["收盘"])
            position.market_value = position.current_price * position.total_shares
            position.profit_loss = position.market_value - position.total_cost
            position.profit_loss_pct = (position.current_price / position.entry_price - 1) * 100

            # 重新计算 ATR
            df = self.screener._calculate_atr(df)
            position.atr = float(df["ATR"].iloc[-1])

            # 更新移动止损价
            highest = max(position.entry_price, position.current_price)
            # 如果有历史更高价
            if len(df) >= 2:
                recent_high = df["最高"].iloc[-20:].max()
                highest = max(highest, recent_high)
            position.current_stop = round(highest - position.atr * position.stop_n, 2)

            # 检查加仓触发
            for add_price in position.add_prices:
                if add_price not in position.filled_add_prices:
                    if position.current_price >= add_price:
                        position.filled_add_prices.append(add_price)
                        position.is_add_triggered = True

            # 检查止损触发
            if position.current_price <= position.current_stop:
                position.is_stop_triggered = True
                position.exit_signal = "跌破移动止损"

            # 检查退出信号
            if position.is_stop_triggered:
                pass  # 已设置退出信号

            return {
                "code": position.code,
                "alerts": self._generate_alerts(position)
            }

        except Exception as e:
            logger.error(f"更新持仓失败 {position.code}: {e}")
            return None

    def _update_watchlist_stock(self, stock: WatchStock) -> Optional[Dict[str, Any]]:
        """更新关注列表股票"""
        try:
            # 获取最新数据
            df = self.repository.load_stock_data(stock.code)
            if df is None:
                df = self.downloader.download_stock_history(stock.code)

            if df is None or len(df) < 20:
                return None

            latest = df.iloc[-1]
            stock.current_price = float(latest["收盘"])

            # 检查是否突破
            twenty_day_high = df["最高"].iloc[-20:-1].max() if len(df) > 20 else float(df["最高"].iloc[-1])
            stock.is_breakout = stock.current_price > stock.breakout_price

            # 计算 ATR
            df = self.screener._calculate_atr(df)
            stock.atr = float(df["ATR"].iloc[-1])
            stock.stop_price = round(stock.current_price - stock.atr * 2, 2)

            # 检查加仓触发
            stock.is_add_triggered = []
            for add_price in stock.add_prices:
                stock.is_add_triggered.append(stock.current_price >= add_price)

            return {
                "code": stock.code,
                "alerts": self._generate_watchlist_alerts(stock)
            }

        except Exception as e:
            logger.error(f"更新关注股票失败 {stock.code}: {e}")
            return None

    def _generate_alerts(self, position: PositionInfo) -> List[Dict[str, Any]]:
        """生成持仓提醒"""
        alerts = []

        # 止损预警
        if position.is_stop_triggered:
            alerts.append({
                "type": "STOP_LOSS",
                "level": "CRITICAL",
                "code": position.code,
                "name": position.name,
                "message": f"⚠️ 止损触发！{position.name} ({position.code}) 当前价 ¥{position.current_price:.2f} ≤ 止损价 ¥{position.current_stop:.2f}",
                "action": "建议全部卖出退出"
            })

        # 加仓触发
        if position.is_add_triggered and position.units < 4:
            unfilled = [p for p in position.add_prices if p not in position.filled_add_prices]
            if unfilled:
                next_add = unfilled[0]
                if position.current_price >= next_add * 0.99:  # 接近加仓价
                    alerts.append({
                        "type": "ADD_UNIT",
                        "level": "INFO",
                        "code": position.code,
                        "name": position.name,
                        "message": f"📈 加仓机会！{position.name} 当前价 ¥{position.current_price:.2f}，下次加仓价 ¥{next_add:.2f}",
                        "action": f"准备加仓 {position.shares_per_unit} 股"
                    })

        # 大幅盈利
        if position.profit_loss_pct > 20:
            alerts.append({
                "type": "PROFIT_HIGH",
                "level": "INFO",
                "code": position.code,
                "name": position.name,
                "message": f"🎯 大幅盈利！{position.name} 盈利 +{position.profit_loss_pct:.1f}% (¥{position.profit_loss:,.0f})",
                "action": f"移动止损价 ¥{position.current_stop:.2f}，保护利润"
            })

        # 接近止损
        stop_distance = (position.current_price - position.current_stop) / position.current_price * 100
        if 0 < stop_distance <= 3:
            alerts.append({
                "type": "STOP_WARNING",
                "level": "WARNING",
                "code": position.code,
                "name": position.name,
                "message": f"⚠️ 接近止损！{position.name} 距离止损价仅 {stop_distance:.1f}%",
                "action": "密切关注，准备退出"
            })

        return alerts

    def _generate_watchlist_alerts(self, stock: WatchStock) -> List[Dict[str, Any]]:
        """生成关注列表提醒"""
        alerts = []

        # 突破提醒
        if stock.is_breakout:
            alerts.append({
                "type": "BREAKOUT",
                "level": "INFO",
                "code": stock.code,
                "name": stock.name,
                "message": f"🚀 突破信号！{stock.name} ({stock.code}) 突破 ¥{stock.breakout_price:.2f}",
                "action": f"建议建仓，止损价 ¥{stock.stop_price:.2f}"
            })

        return alerts

    def generate_report(self) -> str:
        """生成监控报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("🐢 海龟交易持仓监控报告")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)

        # 持仓汇总
        if self.positions:
            lines.append(f"\n📊 持仓汇总 ({len(self.positions)} 只)")
            lines.append("-" * 80)

            total_cost = sum(p.total_cost for p in self.positions)
            total_value = sum(p.market_value for p in self.positions)
            total_profit = total_value - total_cost
            total_profit_pct = (total_value / total_cost - 1) * 100 if total_cost > 0 else 0

            lines.append(f"总成本：¥{total_cost:,.0f}")
            lines.append(f"总市值：¥{total_value:,.0f}")
            lines.append(f"总盈亏：¥{total_profit:,.0f} ({total_profit_pct:+.1f}%)")
            lines.append("")

            # 持仓明细
            lines.append("📈 持仓明细:")
            lines.append(f"{'代码':<10} {'名称':<12} {'现价':>8} {'成本':>8} {'盈亏%':>8} {'止损':>8} {'信号':>10}")
            lines.append("-" * 80)

            for p in self.positions:
                signal = ""
                if p.is_stop_triggered:
                    signal = "❌ 止损"
                elif p.profit_loss_pct > 20:
                    signal = "🎯 大盈"
                elif p.profit_loss_pct > 10:
                    signal = "✅ 盈利"
                elif p.profit_loss_pct < -5:
                    signal = "⚠️ 亏损"
                else:
                    signal = "➖ 持有"

                lines.append(f"{p.code:<10} {p.name[:12]:<12} {p.current_price:>8.2f} {p.entry_price:>8.2f} "
                           f"{p.profit_loss_pct:>+7.1f}% {p.current_stop:>8.2f} {signal:>10}")
        else:
            lines.append("\n⚪ 当前无持仓")

        # 关注列表
        if self.watchlist:
            lines.append(f"\n👁️ 关注列表 ({len(self.watchlist)} 只)")
            lines.append("-" * 80)
            lines.append(f"{'代码':<10} {'名称':<12} {'现价':>8} {'突破价':>8} {'状态':>10}")
            lines.append("-" * 80)

            for s in self.watchlist:
                status = "🚀 已突破" if s.is_breakout else "⏳ 等待突破"
                lines.append(f"{s.code:<10} {s.name[:12]:<12} {s.current_price:>8.2f} {s.breakout_price:>8.2f} {status:>10}")
        else:
            lines.append("\n⚪ 无关注股票")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def print_alerts(self, alerts: List[Dict[str, Any]]):
        """打印提醒"""
        if not alerts:
            print("\nℹ️  暂无新提醒")
            return

        print("\n" + "!" * 80)
        print("🔔 实时提醒")
        print("!" * 80)

        for alert in alerts:
            level_icon = {
                "CRITICAL": "🚨",
                "WARNING": "⚠️",
                "INFO": "ℹ️"
            }.get(alert["level"], "•")

            print(f"\n{level_icon} [{alert['type']}] {alert['message']}")
            if "action" in alert:
                print(f"   👉 {alert['action']}")

        print("\n" + "!" * 80)


def create_monitor() -> TurtleMonitor:
    """创建监控器实例"""
    return TurtleMonitor()
