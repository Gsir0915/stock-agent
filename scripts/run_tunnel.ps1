# 重新启动并获取 URL

Write-Host "停止现有进程..."
Get-Process | Where-Object { $_.ProcessName -like '*cloudflared*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "启动 Cloudflare Tunnel (前台运行)..." -ForegroundColor Cyan
Write-Host "URL 将显示在此窗口中" -ForegroundColor Yellow
Write-Host ""

# 前台运行 tunnel，这样可以看到输出
& C:\Users\47064\bin\cloudflared.exe tunnel --url http://localhost:8080
