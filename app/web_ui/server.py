# -*- coding: utf-8 -*-
"""
海龟交易监控系统 - Web 可视化界面
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.turtle_screener.monitor import TurtleMonitor, PositionInfo, WatchStock, create_monitor
from ..utils.stock_names import StockNameService

app = FastAPI(title="海龟交易监控系统")

# 数据文件路径
POSITIONS_FILE = Path("data/turtle_positions.json")
WATCHLIST_FILE = Path("data/turtle_watchlist.json")


# ==================== 数据模型 ====================

class PositionAddRequest(BaseModel):
    code: str
    capital: float = 100000


class PositionRemoveRequest(BaseModel):
    code: str


class WatchAddRequest(BaseModel):
    code: str


class WatchRemoveRequest(BaseModel):
    code: str


# ==================== 辅助函数 ====================

def load_positions() -> List[Dict[str, Any]]:
    """加载持仓数据"""
    if not POSITIONS_FILE.exists():
        return []
    with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_positions(positions: List[Dict[str, Any]]):
    """保存持仓数据"""
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


def load_watchlist() -> List[Dict[str, Any]]:
    """加载关注列表"""
    if not WATCHLIST_FILE.exists():
        return []
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(watchlist: List[Dict[str, Any]]):
    """保存关注列表"""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


# ==================== HTML 页面 ====================

def get_html_content() -> str:
    """返回主页面 HTML"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐢 海龟交易监控系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #333;
            font-size: 28px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-actions {
            display: flex;
            gap: 12px;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #f0f0f0;
            color: #333;
        }

        .btn-secondary:hover {
            background: #e0e0e0;
        }

        .btn-danger {
            background: #ff4757;
            color: white;
        }

        .btn-danger:hover {
            background: #ff3344;
        }

        .btn-success {
            background: #2ed573;
            color: white;
        }

        .btn-success:hover {
            background: #26c966;
        }

        .btn-warning {
            background: #ffa502;
            color: white;
        }

        .btn-warning:hover {
            background: #ff9500;
        }

        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        .card-label {
            color: #888;
            font-size: 13px;
            margin-bottom: 8px;
        }

        .card-value {
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }

        .card-value.positive {
            color: #2ed573;
        }

        .card-value.negative {
            color: #ff4757;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        @media (max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 2px solid #f0f0f0;
        }

        .panel-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .tab-container {
            margin-bottom: 20px;
        }

        .tabs {
            display: flex;
            gap: 8px;
            background: #f5f5f5;
            padding: 6px;
            border-radius: 10px;
            margin-bottom: 16px;
        }

        .tab {
            flex: 1;
            padding: 10px 16px;
            border: none;
            background: transparent;
            cursor: pointer;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
        }

        .tab.active {
            background: white;
            color: #667eea;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            color: #666;
            font-size: 13px;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
        }

        td {
            padding: 14px 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 14px;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .stock-code {
            font-weight: 600;
            color: #667eea;
        }

        .stock-name {
            color: #333;
        }

        .price {
            font-weight: 500;
        }

        .profit-positive {
            color: #2ed573;
            font-weight: 500;
        }

        .profit-negative {
            color: #ff4757;
            font-weight: 500;
        }

        .profit-neutral {
            color: #888;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-holding {
            background: #e8f4fd;
            color: #0077cc;
        }

        .status-profit {
            background: #e6f9ed;
            color: #2ed573;
        }

        .status-big-profit {
            background: #d4edda;
            color: #1e7e34;
        }

        .status-loss {
            background: #fff0f0;
            color: #ff4757;
        }

        .status-stop {
            background: #ffcccc;
            color: #cc0000;
        }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .modal {
            background: white;
            border-radius: 16px;
            padding: 32px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 24px;
            color: #333;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-size: 14px;
            font-weight: 500;
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .modal-actions {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }

        .modal-actions .btn {
            flex: 1;
            justify-content: center;
        }

        .alerts-container {
            margin-top: 24px;
        }

        .alert-item {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .alert-critical {
            background: #fff0f0;
            border-left: 4px solid #ff4757;
        }

        .alert-warning {
            background: #fff8e6;
            border-left: 4px solid #ffa502;
        }

        .alert-info {
            background: #e6f4ff;
            border-left: 4px solid #0077cc;
        }

        .alert-icon {
            font-size: 20px;
        }

        .alert-content {
            flex: 1;
        }

        .alert-message {
            color: #333;
            font-size: 14px;
        }

        .alert-action {
            color: #666;
            font-size: 12px;
            margin-top: 4px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #888;
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🐢 海龟交易监控系统</h1>
            <div class="header-actions">
                <button class="btn btn-secondary" onclick="refreshData()">
                    🔄 刷新
                </button>
                <button class="btn btn-primary" onclick="showAddPositionModal()">
                    ➕ 添加持仓
                </button>
            </div>
        </div>

        <!-- 汇总卡片 -->
        <div class="summary-cards">
            <div class="card">
                <div class="card-label">持仓数量</div>
                <div class="card-value" id="positionCount">-</div>
            </div>
            <div class="card">
                <div class="card-label">总成本</div>
                <div class="card-value" id="totalCost">-</div>
            </div>
            <div class="card">
                <div class="card-label">总市值</div>
                <div class="card-value" id="totalValue">-</div>
            </div>
            <div class="card">
                <div class="card-label">总盈亏</div>
                <div class="card-value" id="totalProfit">-</div>
            </div>
            <div class="card">
                <div class="card-label">关注股票</div>
                <div class="card-value" id="watchCount">-</div>
            </div>
        </div>

        <!-- 主内容 -->
        <div class="main-content">
            <!-- 左侧：持仓和关注 -->
            <div class="panel">
                <div class="tab-container">
                    <div class="tabs">
                        <button class="tab active" onclick="switchTab('positions')">持仓列表</button>
                        <button class="tab" onclick="switchTab('watchlist')">关注列表</button>
                    </div>

                    <!-- 持仓列表 -->
                    <div class="tab-content active" id="positions-tab">
                        <table>
                            <thead>
                                <tr>
                                    <th>代码</th>
                                    <th>名称</th>
                                    <th>现价</th>
                                    <th>成本价</th>
                                    <th>盈亏</th>
                                    <th>止损价</th>
                                    <th>状态</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="positionsTableBody">
                                <tr><td colspan="8" class="loading">加载中...</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- 关注列表 -->
                    <div class="tab-content" id="watchlist-tab">
                        <table>
                            <thead>
                                <tr>
                                    <th>代码</th>
                                    <th>名称</th>
                                    <th>现价</th>
                                    <th>突破价</th>
                                    <th>状态</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="watchlistTableBody">
                                <tr><td colspan="6" class="loading">加载中...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- 右侧：提醒和详情 -->
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">🔔 实时提醒</div>
                    <button class="btn btn-secondary" onclick="checkAlerts()">检查提醒</button>
                </div>
                <div class="alerts-container" id="alertsContainer">
                    <div class="empty-state">
                        <div class="empty-state-icon">ℹ️</div>
                        <div>暂无新提醒</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 添加持仓模态框 -->
    <div class="modal-overlay" id="addPositionModal">
        <div class="modal">
            <div class="modal-title">添加持仓</div>
            <div class="form-group">
                <label class="form-label">股票代码</label>
                <input type="text" class="form-input" id="addPositionCode" placeholder="例如：002053">
            </div>
            <div class="form-group">
                <label class="form-label">资金量（元）</label>
                <input type="number" class="form-input" id="addPositionCapital" value="100000">
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="hideAddPositionModal()">取消</button>
                <button class="btn btn-primary" onclick="submitAddPosition()">确定</button>
            </div>
        </div>
    </div>

    <!-- 添加关注模态框 -->
    <div class="modal-overlay" id="addWatchModal">
        <div class="modal">
            <div class="modal-title">添加到关注列表</div>
            <div class="form-group">
                <label class="form-label">股票代码</label>
                <input type="text" class="form-input" id="addWatchCode" placeholder="例如：600519">
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="hideAddWatchModal()">取消</button>
                <button class="btn btn-primary" onclick="submitAddWatch()">确定</button>
            </div>
        </div>
    </div>

    <script>
        let positionsData = [];
        let watchlistData = [];

        // 页面加载时获取数据
        document.addEventListener('DOMContentLoaded', () => {
            refreshData();
        });

        // 刷新数据
        async function refreshData() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();

                positionsData = data.positions || [];
                watchlistData = data.watchlist || [];

                updateSummaryCards(data);
                renderPositionsTable();
                renderWatchlistTable();
            } catch (error) {
                console.error('获取数据失败:', error);
            }
        }

        // 更新汇总卡片
        function updateSummaryCards(data) {
            document.getElementById('positionCount').textContent = data.position_count || 0;
            document.getElementById('totalCost').textContent = formatCurrency(data.total_cost || 0);
            document.getElementById('totalValue').textContent = formatCurrency(data.total_value || 0);

            const profit = data.total_profit || 0;
            const profitEl = document.getElementById('totalProfit');
            profitEl.textContent = formatCurrency(profit);
            profitEl.className = 'card-value ' + (profit >= 0 ? 'positive' : 'negative');

            document.getElementById('watchCount').textContent = data.watchlist_count || 0;
        }

        // 渲染持仓列表
        function renderPositionsTable() {
            const tbody = document.getElementById('positionsTableBody');

            if (!positionsData || positionsData.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-state-icon">📭</div><div>暂无持仓</div></td></tr>';
                return;
            }

            tbody.innerHTML = positionsData.map(p => {
                const profitClass = p.profit_loss_pct >= 0 ? 'profit-positive' : 'profit-negative';
                const statusInfo = getStatusInfo(p);

                return `<tr>
                    <td class="stock-code">${p.code}</td>
                    <td class="stock-name">${p.name}</td>
                    <td class="price">¥${p.current_price?.toFixed(2) || '-'}</td>
                    <td>¥${p.entry_price?.toFixed(2) || '-'}</td>
                    <td class="${profitClass}">${p.profit_loss_pct?.toFixed(1) || 0}%</td>
                    <td>¥${p.current_stop?.toFixed(2) || '-'}</td>
                    <td><span class="status-badge ${statusInfo.class}">${statusInfo.text}</span></td>
                    <td>
                        <button class="btn btn-danger" style="padding:6px 12px;font-size:12px;"
                            onclick="removePosition('${p.code}')">移除</button>
                    </td>
                </tr>`;
            }).join('');
        }

        // 渲染关注列表
        function renderWatchlistTable() {
            const tbody = document.getElementById('watchlistTableBody');

            if (!watchlistData || watchlistData.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-state-icon">👁️</div><div>暂无关注股票</div></td></tr>';
                return;
            }

            tbody.innerHTML = watchlistData.map(w => {
                const statusClass = w.is_breakout ? 'status-profit' : 'status-holding';
                const statusText = w.is_breakout ? '🚀 已突破' : '⏳ 等待突破';

                return `<tr>
                    <td class="stock-code">${w.code}</td>
                    <td class="stock-name">${w.name}</td>
                    <td class="price">¥${w.current_price?.toFixed(2) || '-'}</td>
                    <td>¥${w.breakout_price?.toFixed(2) || '-'}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td>
                        <button class="btn btn-danger" style="padding:6px 12px;font-size:12px;"
                            onclick="removeWatch('${w.code}')">移除</button>
                    </td>
                </tr>`;
            }).join('');
        }

        // 获取状态信息
        function getStatusInfo(p) {
            const pct = p.profit_loss_pct || 0;
            if (p.is_stop_triggered) {
                return { class: 'status-stop', text: '❌ 止损' };
            } else if (pct > 20) {
                return { class: 'status-big-profit', text: '🎯 大盈' };
            } else if (pct > 10) {
                return { class: 'status-profit', text: '✅ 盈利' };
            } else if (pct < -5) {
                return { class: 'status-loss', text: '⚠️ 亏损' };
            } else {
                return { class: 'status-holding', text: '➖ 持有' };
            }
        }

        // 切换标签页
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        }

        // 显示/隐藏模态框
        function showAddPositionModal() {
            document.getElementById('addPositionModal').style.display = 'flex';
        }

        function hideAddPositionModal() {
            document.getElementById('addPositionModal').style.display = 'none';
        }

        function showAddWatchModal() {
            document.getElementById('addWatchModal').style.display = 'flex';
        }

        function hideAddWatchModal() {
            document.getElementById('addWatchModal').style.display = 'none';
        }

        // 提交添加持仓
        async function submitAddPosition() {
            const code = document.getElementById('addPositionCode').value.trim();
            const capital = parseFloat(document.getElementById('addPositionCapital').value);

            if (!code) {
                alert('请输入股票代码');
                return;
            }

            try {
                const response = await fetch('/api/position/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code, capital })
                });

                const result = await response.json();

                if (response.ok) {
                    alert('✅ 添加成功!\\n' + result.message);
                    hideAddPositionModal();
                    refreshData();
                } else {
                    alert('❌ 添加失败：' + result.detail);
                }
            } catch (error) {
                alert('请求失败：' + error.message);
            }
        }

        // 提交添加关注
        async function submitAddWatch() {
            const code = document.getElementById('addWatchCode').value.trim();

            if (!code) {
                alert('请输入股票代码');
                return;
            }

            try {
                const response = await fetch('/api/watchlist/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });

                const result = await response.json();

                if (response.ok) {
                    alert('✅ 添加成功!');
                    hideAddWatchModal();
                    refreshData();
                } else {
                    alert('❌ 添加失败：' + result.detail);
                }
            } catch (error) {
                alert('请求失败：' + error.message);
            }
        }

        // 移除持仓
        async function removePosition(code) {
            if (!confirm(`确定要移除持仓 ${code} 吗？`)) return;

            try {
                const response = await fetch('/api/position/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });

                if (response.ok) {
                    refreshData();
                } else {
                    alert('移除失败：' + response.statusText);
                }
            } catch (error) {
                alert('请求失败：' + error.message);
            }
        }

        // 移除关注
        async function removeWatch(code) {
            if (!confirm(`确定要移除关注 ${code} 吗？`)) return;

            try {
                const response = await fetch('/api/watchlist/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });

                if (response.ok) {
                    refreshData();
                } else {
                    alert('移除失败：' + response.statusText);
                }
            } catch (error) {
                alert('请求失败：' + error.message);
            }
        }

        // 检查提醒
        async function checkAlerts() {
            try {
                const response = await fetch('/api/alerts');
                const data = await response.json();

                const container = document.getElementById('alertsContainer');

                if (!data.alerts || data.alerts.length === 0) {
                    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">ℹ️</div><div>暂无新提醒</div></div>';
                    return;
                }

                container.innerHTML = data.alerts.map(alert => {
                    const icons = {
                        'CRITICAL': '🚨',
                        'WARNING': '⚠️',
                        'INFO': 'ℹ️'
                    };
                    const alertClass = 'alert-' + alert.level.toLowerCase();

                    return `<div class="alert-item ${alertClass}">
                        <div class="alert-icon">${icons[alert.level] || '•'}</div>
                        <div class="alert-content">
                            <div class="alert-message">${alert.message}</div>
                            ${alert.action ? '<div class="alert-action">👉 ' + alert.action + '</div>' : ''}
                        </div>
                    </div>`;
                }).join('');
            } catch (error) {
                console.error('获取提醒失败:', error);
            }
        }

        // 格式化货币
        function formatCurrency(value) {
            const num = parseFloat(value) || 0;
            return '¥' + Math.abs(num).toLocaleString('zh-CN', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            });
        }
    </script>
</body>
</html>
"""
