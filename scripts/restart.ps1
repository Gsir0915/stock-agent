# 停止现有进程
Write-Host "停止现有进程..."
Get-Process | Where-Object { $_.ProcessName -like '*cloudflared*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.Path -like '*stock-agent*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 启动机器人和 tunnel
$BOT_DIR = "C:\Users\47064\stock-agent"
$CLOUDFLARED = "C:\Users\47064\bin\cloudflared.exe"

Write-Host "启动机器人..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BOT_DIR'; python -m app.bot --port 8080"

Start-Sleep -Seconds 5

Write-Host "启动 Cloudflare Tunnel..."
Start-Process $CLOUDFLARED -ArgumentList "tunnel", "--url", "http://localhost:8080"

Write-Host "完成！请查看新窗口中的 URL"
