$processes = Get-Process | Where-Object { $_.ProcessName -like '*cloudflared*' }
if ($processes) {
    Write-Host "Cloudflared is running:"
    $processes | Format-Table ProcessName, Id, StartTime
} else {
    Write-Host "Cloudflared not running. Checking tunnel URL..."
    # Try to get tunnel info
}

# Check if bot is running
$python = Get-Process | Where-Object { $_.ProcessName -eq 'python' }
if ($python) {
    Write-Host "Python is running:"
    $python | Format-Table ProcessName, Id
} else {
    Write-Host "Python not running"
}
