# 获取 Cloudflare Tunnel URL

# 等待几秒让 tunnel 完全启动
Start-Sleep -Seconds 5

# 尝试读取 tunnel 输出（通过日志）
Write-Host "正在获取 Cloudflare Tunnel URL..."
Write-Host ""

# 使用 cloudflared 命令获取信息
& C:\Users\47064\bin\cloudflared tunnel list 2>&1

Write-Host ""
Write-Host "如果上面没有显示 URL，请查看 cloudflared 窗口" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示：URL 格式为 https://xxx.trycloudflare.com" -ForegroundColor Cyan
Write-Host ""

# 测试本地服务
Write-Host "测试本地服务..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "本地服务响应：$($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "本地服务未响应，请检查机器人窗口" -ForegroundColor Red
}
