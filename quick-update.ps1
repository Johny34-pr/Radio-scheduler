# Gyors frissítési script - AzuraCast integráció
# Használat: .\quick-update.ps1 <server-ip>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP
)

Write-Host "=== Radio Scheduler - AzuraCast Integration Update ===" -ForegroundColor Cyan
Write-Host ""

# Fájlok feltöltése
Write-Host "1. Feltöltés..." -ForegroundColor Yellow
scp app.py root@${ServerIP}:/root/radio_scheduler/
scp templates/index.html root@${ServerIP}:/root/radio_scheduler/templates/
scp requirements.txt root@${ServerIP}:/root/radio_scheduler/
scp SETTINGS.md root@${ServerIP}:/root/radio_scheduler/

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Feltöltés sikertelen" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ Feltöltés sikeres" -ForegroundColor Green
Write-Host ""

# Frissítés a szerveren
Write-Host "2. Frissítés..." -ForegroundColor Yellow
ssh root@${ServerIP} @"
cd /root/radio_scheduler
pip3 install -r requirements.txt
sudo cp app.py /opt/radio_scheduler/
sudo cp templates/index.html /opt/radio_scheduler/templates/
sudo cp requirements.txt /opt/radio_scheduler/
sudo systemctl restart radio-scheduler
echo '--- Service Status ---'
sudo systemctl status radio-scheduler --no-pager -l
"@

Write-Host ""
Write-Host "=== Frissítés kész! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Következő lépések:" -ForegroundColor White
Write-Host "1. Nyisd meg: http://${ServerIP}:86" -ForegroundColor White
Write-Host "2. Hard refresh: Ctrl + Shift + R" -ForegroundColor White
Write-Host "3. Görgess le a Beállítások panelhez" -ForegroundColor White
Write-Host "4. Állítsd be a stream URL-t és AzuraCast adatokat" -ForegroundColor White
Write-Host ""
Write-Host "Dokumentáció: SETTINGS.md" -ForegroundColor Cyan
