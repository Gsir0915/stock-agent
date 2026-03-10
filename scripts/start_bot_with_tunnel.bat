@echo off
chcp 65001 >nul
echo ========================================
echo   飞书机器人 + Cloudflare Tunnel
echo ========================================
echo.

REM 检查 cloudflared 是否安装
where cloudflared >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 cloudflared
    echo.
    echo 请先安装 cloudflared:
    echo   winget install Cloudflare.cloudflared
    echo.
    pause
    exit /b 1
)

echo [1/3] 启动飞书机器人...
start "飞书机器人" cmd /k "python -m app.bot --port 8080"

REM 等待机器人启动
timeout /t 3 /nobreak >nul

echo [2/3] 启动 Cloudflare Tunnel...
start "Cloudflare Tunnel" cmd /k "cloudflared tunnel --url http://localhost:8080"

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 请查看 'Cloudflare Tunnel' 窗口，复制 https 地址
echo 然后配置到飞书开放平台的事件订阅 URL:
echo   https://xxx.trycloudflare.com/feishu/event
echo.
echo 按任意键退出此窗口...
pause >nul
