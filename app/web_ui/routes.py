# -*- coding: utf-8 -*-
"""
海龟交易监控系统 - API 路由
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.turtle_screener.monitor import TurtleMonitor, PositionInfo, WatchStock
from ..core.turtle import TurtleScreener
from ..data.downloader import DataDownloader
from ..data.repository import get_repository
from ..utils.stock_names import StockNameService
from .server import load_positions, save_positions, load_watchlist, save_watchlist

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """获取仪表盘数据"""
    monitor = create_monitor_with_data()

    # 更新价格
    monitor.update_prices()

    # 保存更新后的数据
    save_monitor_data(monitor)

    # 计算汇总数据
    positions = []
    for p in monitor.positions:
        positions.append({
            "code": p.code,
            "name": p.name,
            "current_price": p.current_price,
            "entry_price": p.entry_price,
            "profit_loss_pct": p.profit_loss_pct,
            "profit_loss": p.profit_loss,
            "current_stop": p.current_stop,
            "is_stop_triggered": p.is_stop_triggered,
            "market_value": p.market_value,
            "total_cost": p.total_cost,
        })

    watchlist = []
    for w in monitor.watchlist:
        watchlist.append({
            "code": w.code,
            "name": w.name,
            "current_price": w.current_price,
            "breakout_price": w.breakout_price,
            "is_breakout": w.is_breakout,
            "atr": w.atr,
            "stop_price": w.stop_price,
        })

    total_cost = sum(p["total_cost"] for p in positions)
    total_value = sum(p["market_value"] for p in positions)
    total_profit = total_value - total_cost

    return {
        "positions": positions,
        "watchlist": watchlist,
        "position_count": len(positions),
        "watchlist_count": len(watchlist),
        "total_cost": total_cost,
        "total_value": total_value,
        "total_profit": total_profit,
    }


@router.get("/alerts")
async def get_alerts():
    """获取实时提醒"""
    monitor = create_monitor_with_data()
    results = monitor.update_prices()

    return {
        "alerts": results.get("alerts", [])
    }


@router.post("/position/add")
async def add_position(data: dict):
    """添加持仓"""
    code = data.get("code", "").strip()
    capital = data.get("capital", 100000)

    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    # 获取股票数据
    name = StockNameService.get_name(code)

    downloader = DataDownloader()
    repository = get_repository()
    screener = TurtleScreener()

    df = downloader.download_stock_history(code)
    if df is not None:
        repository.save_stock_data(code, df)

    signal = screener.check_stock(code, name, df, capital)

    if not signal.success or signal.position_size == 0:
        raise HTTPException(status_code=400, detail=f"无法获取 {code} 的交易信号")

    # 创建持仓记录
    position = {
        "code": code,
        "name": name,
        "entry_price": signal.current_price,
        "entry_date": "",
        "units": 1,
        "shares_per_unit": signal.position_size,
        "total_shares": signal.position_size,
        "total_cost": signal.position_value,
        "initial_stop": signal.stop_loss_price,
        "current_stop": signal.stop_loss_price,
        "stop_n": 2,
        "atr": signal.atr_current,
        "add_unit_window": signal.add_unit_window,
        "add_prices": signal.add_unit_prices,
        "filled_add_prices": []
    }

    # 保存
    positions = load_positions()

    # 检查是否已存在
    for p in positions:
        if p["code"] == code:
            raise HTTPException(status_code=400, detail=f"持仓 {code} 已存在")

    positions.append(position)
    save_positions(positions)

    return {
        "success": True,
        "message": f"已添加持仓：{code} {name}\n入场价：¥{signal.current_price:.2f}\n股数：{signal.position_size:,}\n止损价：¥{signal.stop_loss_price:.2f}",
        "position": position
    }


@router.post("/position/remove")
async def remove_position(data: dict):
    """移除持仓"""
    code = data.get("code", "").strip()

    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    positions = load_positions()
    positions = [p for p in positions if p["code"] != code]
    save_positions(positions)

    return {"success": True, "message": f"已移除持仓：{code}"}


@router.post("/watchlist/add")
async def add_watchlist(data: dict):
    """添加到关注列表"""
    code = data.get("code", "").strip()

    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    name = StockNameService.get_name(code)

    downloader = DataDownloader()
    repository = get_repository()
    screener = TurtleScreener()

    df = downloader.download_stock_history(code)
    if df is not None:
        repository.save_stock_data(code, df)

    signal = screener.check_stock(code, name, df, 100000)

    if not signal.success:
        raise HTTPException(status_code=400, detail=f"无法获取 {code} 的数据")

    watch = {
        "code": code,
        "name": name,
        "breakout_price": signal.twenty_day_high,
        "current_price": signal.current_price,
        "add_prices": signal.add_unit_prices,
        "stop_price": signal.stop_loss_price
    }

    watchlist = load_watchlist()

    # 检查是否已存在
    for w in watchlist:
        if w["code"] == code:
            raise HTTPException(status_code=400, detail=f"关注股票 {code} 已存在")

    watchlist.append(watch)
    save_watchlist(watchlist)

    return {"success": True, "message": f"已添加到关注列表：{code} {name}"}


@router.post("/watchlist/remove")
async def remove_watchlist(data: dict):
    """从关注列表移除"""
    code = data.get("code", "").strip()

    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    watchlist = load_watchlist()
    watchlist = [w for w in watchlist if w["code"] != code]
    save_watchlist(watchlist)

    return {"success": True, "message": f"已移除关注：{code}"}


def create_monitor_with_data() -> TurtleMonitor:
    """创建监控器并加载数据"""
    monitor = TurtleMonitor()

    # 加载持仓
    positions_data = load_positions()
    for p in positions_data:
        position = PositionInfo(
            code=p["code"],
            name=p["name"],
            entry_price=p["entry_price"],
            entry_date=p.get("entry_date", ""),
            units=p.get("units", 1),
            shares_per_unit=p["shares_per_unit"],
            total_shares=p["total_shares"],
            total_cost=p["total_cost"],
            initial_stop=p["initial_stop"],
            current_stop=p.get("current_stop", p["initial_stop"]),
            stop_n=p.get("stop_n", 2),
            atr=p.get("atr", 0),
            add_unit_window=p.get("add_unit_window", 0),
            add_prices=p.get("add_prices", []),
            filled_add_prices=p.get("filled_add_prices", [])
        )
        monitor.add_position(position)

    # 加载关注列表
    watchlist_data = load_watchlist()
    for w in watchlist_data:
        stock = WatchStock(
            code=w["code"],
            name=w["name"],
            breakout_price=w["breakout_price"],
            add_prices=w.get("add_prices", []),
            stop_price=w.get("stop_price", 0)
        )
        monitor.add_to_watchlist(stock)

    return monitor


def save_monitor_data(monitor: TurtleMonitor):
    """保存监控器数据"""
    positions_data = []
    for p in monitor.positions:
        positions_data.append({
            "code": p.code,
            "name": p.name,
            "entry_price": p.entry_price,
            "entry_date": p.entry_date,
            "units": p.units,
            "shares_per_unit": p.shares_per_unit,
            "total_shares": p.total_shares,
            "total_cost": p.total_cost,
            "initial_stop": p.initial_stop,
            "current_stop": p.current_stop,
            "stop_n": p.stop_n,
            "atr": p.atr,
            "add_unit_window": p.add_unit_window,
            "add_prices": p.add_prices,
            "filled_add_prices": p.filled_add_prices
        })
    save_positions(positions_data)
