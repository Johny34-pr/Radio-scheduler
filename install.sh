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
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_FILE="/etc/systemd/system/radio-scheduler.service"
PLAYOUT_SERVICE_FILE="/etc/systemd/system/azuracast-playout.service"
CURRENT_DIR="$(pwd)"

echo "Telepítési mappa: $INSTALL_DIR"
echo ""

# 1. Python venv létrehozása és függőségek telepítése
echo "[1/6] Python virtual environment létrehozása..."
apt-get install -y python3-venv python3-full >/dev/null 2>&1 || true
mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_DIR"
echo "[2/6] Python függőségek telepítése (venv)..."
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1
"$VENV_DIR/bin/pip" install -r requirements.txt

# 3. Fájlok másolása
echo "[3/6] Fájlok másolása..."
mkdir -p "$INSTALL_DIR"
cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/start.sh"
chmod +x "$INSTALL_DIR/scripts/audio_fade.sh" 2>/dev/null || true

# 4. Systemd service fájl létrehozása
echo "[4/6] Systemd service beállítása..."
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
ExecStart=/opt/radio_scheduler/venv/bin/python /opt/radio_scheduler/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# AzuraCast playout service telepítése (mpv + hangerő fade in/out)
if [ -f "$INSTALL_DIR/azuracast-playout.service" ]; then
    cp "$INSTALL_DIR/azuracast-playout.service" "$PLAYOUT_SERVICE_FILE"
fi

# 5. Systemd újratöltése
echo "[5/6] Systemd daemon újratöltése..."
systemctl daemon-reload

# 6. Szolgáltatás engedélyezése és indítása
echo "[6/6] Szolgáltatás engedélyezése..."
systemctl enable radio-scheduler

# Playout szolgáltatás legyen ismert a rendszernek, de ne induljon automatikusan bootkor.
systemctl disable azuracast-playout >/dev/null 2>&1 || true

echo "Szolgáltatás indítása..."
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
