# 飞书机器人 - 快速启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  飞书股票分析机器人 + Cloudflare Tunnel" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BOT_DIR = "C:\Users\47064\stock-agent"
$CLOUDFLARED = "C:\Users\47064\bin\cloudflared.exe"

# 检查是否已有进程运行
Write-Host "检查现有进程..."
$existingPython = Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.Path -like '*stock-agent*' }
$existingCloudflared = Get-Process | Where-Object { $_.ProcessName -like '*cloudflared*' }

if ($existingCloudflared) {
    Write-Host "停止现有的 cloudflared 进程..." -ForegroundColor Yellow
    $existingCloudflared | Stop-Process -Force
}

# 启动机器人
Write-Host ""
Write-Host "[1/2] 启动飞书机器人..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BOT_DIR'; python -m app.bot --port 8080" -WindowStyle Normal

# 等待机器人启动
Start-Sleep -Seconds 3

# 启动 Tunnel
Write-Host ""
Write-Host "[2/2] 启动 Cloudflare Tunnel..." -ForegroundColor Green
Start-Process $CLOUDFLARED -ArgumentList "tunnel", "--url", "http://localhost:8080" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "请查看新打开的 Cloudflare Tunnel 窗口" -ForegroundColor Yellow
Write-Host "复制 https 地址并配置到飞书开放平台：" -ForegroundColor Yellow
Write-Host ""
Write-Host "  https://xxx.trycloudflare.com/feishu/event" -ForegroundColor White
Write-Host ""
Write-Host "按任意键退出此窗口..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
