#!/bin/bash

# Telepítő script a Radio Scheduler szolgáltatáshoz

set -e

echo "==================================="
echo "Radio Scheduler Telepítő"
echo "==================================="

# Root jogosultság ellenőrzése
if [ "$EUID" -ne 0 ]; then 
    echo "HIBA: Ezt a scriptet root jogosultsággal kell futtatni!"
    echo "Használd: sudo bash install.sh"
    exit 1
fi

# Változók
INSTALL_DIR="/opt/radio_scheduler"
SERVICE_FILE="/etc/systemd/system/radio-scheduler.service"
CURRENT_DIR="$(pwd)"

echo "Telepítési mappa: $INSTALL_DIR"
echo ""

# 1. Függőségek telepítése
echo "[1/5] Python függőségek telepítése..."
pip3 install -r requirements.txt

# 2. Fájlok másolása
echo "[2/5] Fájlok másolása..."
mkdir -p "$INSTALL_DIR"
cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/start.sh"

# 3. Systemd service fájl létrehozása
echo "[3/5] Systemd service beállítása..."
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Radio Scheduler Web Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/radio_scheduler
Environment="RADIO_SERVICE=azuracast-playout.service"
Environment="PORT=86"
ExecStart=/usr/bin/python3 /opt/radio_scheduler/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 4. Systemd újratöltése
echo "[4/5] Systemd daemon újratöltése..."
systemctl daemon-reload

# 5. Szolgáltatás engedélyezése és indítása
echo "[5/5] Szolgáltatás indítása..."
systemctl enable radio-scheduler
systemctl restart radio-scheduler

echo ""
echo "==================================="
echo "✓ Telepítés sikeres!"
echo "==================================="
echo ""

# Tűzfal konfiguráció
echo "Tűzfal beállítása..."
FIREWALL_CONFIGURED=0

if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    echo "  UFW észlelve, 86/tcp port megnyitása..."
    ufw allow 86/tcp > /dev/null 2>&1
    FIREWALL_CONFIGURED=1
fi

if command -v firewall-cmd &> /dev/null && firewall-cmd --state 2>/dev/null | grep -q "running"; then
    echo "  Firewalld észlelve, 86/tcp port megnyitása..."
    firewall-cmd --add-port=86/tcp --permanent > /dev/null 2>&1
    firewall-cmd --reload > /dev/null 2>&1
    FIREWALL_CONFIGURED=1
fi

if [ $FIREWALL_CONFIGURED -eq 1 ]; then
    echo "  ✓ Tűzfal konfiguráció kész!"
else
    echo "  ! Tűzfal nem észlelve vagy nem aktív"
    echo "  Ha távolról nem érhető el, futtasd:"
    echo "    sudo bash open-firewall.sh"
fi

echo ""
echo "Hasznos parancsok:"
echo "  Státusz:        sudo systemctl status radio-scheduler"
echo "  Leállítás:      sudo systemctl stop radio-scheduler"
echo "  Indítás:        sudo systemctl start radio-scheduler"
echo "  Újraindítás:    sudo systemctl restart radio-scheduler"
echo "  Logok:          sudo journalctl -u radio-scheduler -f"
echo ""
echo "Web felület: http://localhost:86"
echo "              http://$(hostname -I | awk '{print $1}'):86"
echo ""
