# Script to upload updated app.py and restart service
# Usage: .\upload-and-restart.ps1 <server-ip>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP
)

Write-Host "=== Radio Scheduler - Upload and Restart ===" -ForegroundColor Cyan
Write-Host ""

# Upload app.py
Write-Host "1. Uploading app.py to server..." -ForegroundColor Yellow
scp app.py root@${ServerIP}:/root/radio_scheduler/

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload app.py" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ Upload successful" -ForegroundColor Green
Write-Host ""

# Restart service
Write-Host "2. Restarting service on server..." -ForegroundColor Yellow
ssh root@${ServerIP} "cd /root/radio_scheduler && sudo cp app.py /opt/radio_scheduler/ && sudo systemctl restart radio-scheduler && sudo systemctl status radio-scheduler --no-pager"

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Check service status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Open browser to http://${ServerIP}:86" -ForegroundColor White
Write-Host "2. Hard refresh: Ctrl + Shift + R" -ForegroundColor White
Write-Host "3. Try adding a schedule" -ForegroundColor White
