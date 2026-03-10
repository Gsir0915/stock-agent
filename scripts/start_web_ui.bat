@echo off
chcp 65001 >nul
echo =========================================================
echo   🐢 海龟交易监控系统 - Web 界面
echo =========================================================
echo.
echo 正在启动 Web 服务器...
echo 访问地址：http://localhost:8080
echo.
python -m app.web_ui --port 8080 --reload
pause
