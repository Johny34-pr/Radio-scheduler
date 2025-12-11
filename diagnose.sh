#!/bin/bash

# Diagnosztikai script a Radio Scheduler hibakereséséhez

echo "==========================================="
echo "Radio Scheduler Diagnosztika"
echo "==========================================="
echo ""

# 1. Python verzió
echo "[1] Python verzió:"
python3 --version
echo ""

# 2. Alkalmazás fut-e
echo "[2] Alkalmazás folyamat:"
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✓ Az alkalmazás FUT"
    ps aux | grep -v grep | grep "python.*app.py"
else
    echo "✗ Az alkalmazás NEM fut"
fi
echo ""

# 3. Systemd szolgáltatás
echo "[3] Systemd szolgáltatás:"
if systemctl is-active --quiet radio-scheduler; then
    echo "✓ radio-scheduler.service AKTÍV"
    systemctl status radio-scheduler --no-pager -l
else
    echo "✗ radio-scheduler.service NEM AKTÍV"
    systemctl status radio-scheduler --no-pager -l 2>&1 | head -10
fi
echo ""

# 4. Port figyelés
echo "[4] Port 86 figyelés:"
if netstat -tuln 2>/dev/null | grep -q ":86 " || ss -tuln 2>/dev/null | grep -q ":86 "; then
    echo "✓ Port 86 NYITVA"
    netstat -tuln 2>/dev/null | grep ":86 " || ss -tuln 2>/dev/null | grep ":86 "
else
    echo "✗ Port 86 NEM hallgat"
fi
echo ""

# 5. Tűzfal
echo "[5] Tűzfal ellenőrzése:"
FIREWALL_ISSUE=0
if command -v ufw &> /dev/null; then
    echo "UFW státusz:"
    UFW_STATUS=$(sudo ufw status 2>/dev/null)
    echo "$UFW_STATUS" | grep -E "86|Status"
    
    if echo "$UFW_STATUS" | grep -q "Status: active"; then
        if ! echo "$UFW_STATUS" | grep -q "86"; then
            echo "⚠️  FIGYELEM: UFW aktív, de a 86-os port NINCS engedélyezve!"
            echo "   Megoldás: sudo ufw allow 86/tcp"
            FIREWALL_ISSUE=1
        fi
    fi
elif command -v firewall-cmd &> /dev/null; then
    echo "Firewalld státusz:"
    if sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
        if sudo firewall-cmd --list-ports 2>/dev/null | grep -q "86/tcp"; then
            echo "✓ Port 86/tcp engedélyezve"
        else
            echo "⚠️  FIGYELEM: Firewalld fut, de a 86/tcp port NINCS engedélyezve!"
            echo "   Megoldás: sudo firewall-cmd --add-port=86/tcp --permanent && sudo firewall-cmd --reload"
            FIREWALL_ISSUE=1
        fi
    else
        echo "Firewalld nem fut"
    fi
elif command -v iptables &> /dev/null; then
    echo "IPTables ellenőrzése:"
    if sudo iptables -L -n 2>/dev/null | grep -q "Chain INPUT"; then
        if sudo iptables -L INPUT -n 2>/dev/null | grep -q "dpt:86"; then
            echo "✓ IPTables szabály található a 86-os portra"
        else
            echo "⚠️  FIGYELEM: IPTables fut, lehet hogy blokkolja a 86-os portot"
            FIREWALL_ISSUE=1
        fi
    fi
else
    echo "Nincs felismert tűzfal (ufw/firewalld/iptables)"
fi

if [ $FIREWALL_ISSUE -eq 1 ]; then
    echo ""
    echo "🔥 TŰZFAL PROBLÉMA ÉSZLELVE!"
    echo "   Ez lehet az oka, hogy böngészőből nem elérhető a szolgáltatás."
fi
echo ""

# 6. Hálózat teszt
echo "[6] Hálózati kapcsolat teszt:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:86 2>/dev/null | grep -q "200\|302\|404"; then
    echo "✓ HTTP válasz SIKERES localhost:86-on"
    curl -s -o /dev/null -w "HTTP Státusz: %{http_code}\n" http://localhost:86
else
    echo "✗ Nem elérhető http://localhost:86"
    echo "Hiba: $(curl http://localhost:86 2>&1 | head -1)"
fi
echo ""

# 7. Adatbázis
echo "[7] Adatbázis:"
if [ -f "scheduler.db" ]; then
    echo "✓ scheduler.db létezik"
    echo "Órarendek száma: $(sqlite3 scheduler.db "SELECT COUNT(*) FROM schedules;" 2>/dev/null || echo "Nem lekérdezhető")"
else
    echo "✗ scheduler.db NEM található"
fi
echo ""

# 8. Utolsó logok
echo "[8] Utolsó 20 log bejegyzés:"
if systemctl is-active --quiet radio-scheduler; then
    sudo journalctl -u radio-scheduler -n 20 --no-pager
else
    echo "A szolgáltatás nem fut systemd-ből, nincs journal log"
fi
echo ""

# 9. Környezeti változók
echo "[9] Környezeti változók:"
echo "RADIO_SERVICE: ${RADIO_SERVICE:-<nincs beállítva, alapértelmezett: radio.service>}"
echo "PORT: ${PORT:-<nincs beállítva, alapértelmezett: 86>}"
echo ""

# 10. Jogosultságok
echo "[10] Felhasználó és jogosultságok:"
echo "Jelenlegi user: $(whoami)"
echo "UID: $(id -u)"
if [ "$(id -u)" -eq 0 ]; then
    echo "✓ Root jogosultság VAN"
else
    echo "✗ Root jogosultság NINCS (sudo lehet szükséges)"
fi
echo ""

echo "==========================================="
echo "Diagnosztika befejezve"
echo "==========================================="
echo ""
echo "Gyors javítások:"
echo "  - Alkalmazás indítása: sudo python3 app.py"
echo "  - Systemd újraindítás: sudo systemctl restart radio-scheduler"
echo "  - Logok követése: sudo journalctl -u radio-scheduler -f"
echo "  - Port ellenőrzés: sudo netstat -tulpn | grep 86"
echo ""
echo "🔥 Ha csak SSH-n működik, de böngészőből NEM:"
echo "  - UFW esetén:       sudo ufw allow 86/tcp"
echo "  - Firewalld esetén: sudo firewall-cmd --add-port=86/tcp --permanent && sudo firewall-cmd --reload"
echo "  - IPTables esetén:  sudo iptables -A INPUT -p tcp --dport 86 -j ACCEPT"
echo ""
