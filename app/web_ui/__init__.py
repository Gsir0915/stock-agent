# -*- coding: utf-8 -*-
"""
海龟交易监控系统 - Web 可视化界面模块
"""

from .server import app
from .routes import router

# 挂载 API 路由
app.include_router(router, prefix="/api")

# 挂载主页面
from fastapi.responses import HTMLResponse
from .server import get_html_content


@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面"""
    return get_html_content()
