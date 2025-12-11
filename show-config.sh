#!/bin/bash

# Konfigurációs összefoglaló megjelenítése

echo "=========================================="
echo "Radio Scheduler - Konfiguráció"
echo "=========================================="
echo ""

# Környezeti változók
RADIO_SERVICE_VAR="${RADIO_SERVICE:-azuracast-playout.service}"
PORT_VAR="${PORT:-86}"
DB_PATH_VAR="${DB_PATH:-scheduler.db}"

echo "📋 Környezeti változók:"
echo "  RADIO_SERVICE: $RADIO_SERVICE_VAR"
echo "  PORT: $PORT_VAR"
echo "  DB_PATH: $DB_PATH_VAR"
echo ""

# Systemd service fájl ellenőrzése
if [ -f "/etc/systemd/system/radio-scheduler.service" ]; then
    echo "📄 Systemd service fájl: TELEPÍTVE"
    echo "  Elérési út: /etc/systemd/system/radio-scheduler.service"
    
    # Service fájlból a konfigurált értékek kiolvasása
    if grep -q "RADIO_SERVICE=" /etc/systemd/system/radio-scheduler.service; then
        CONFIGURED_SERVICE=$(grep "RADIO_SERVICE=" /etc/systemd/system/radio-scheduler.service | head -1 | sed 's/.*RADIO_SERVICE=\([^"]*\).*/\1/')
        echo "  Beállított szolgáltatás: $CONFIGURED_SERVICE"
    fi
    
    if grep -q "PORT=" /etc/systemd/system/radio-scheduler.service; then
        CONFIGURED_PORT=$(grep "PORT=" /etc/systemd/system/radio-scheduler.service | head -1 | sed 's/.*PORT=\([^"]*\).*/\1/')
        echo "  Beállított port: $CONFIGURED_PORT"
    fi
else
    echo "📄 Systemd service fájl: NEM TELEPÍTVE"
    echo "  Futtasd: sudo bash install.sh"
fi
echo ""

# Kezelt szolgáltatás ellenőrzése
echo "🎵 Kezelt szolgáltatás ($RADIO_SERVICE_VAR):"
if systemctl list-unit-files | grep -q "$RADIO_SERVICE_VAR"; then
    echo "  Szolgáltatás: LÉTEZIK"
    
    if systemctl is-enabled "$RADIO_SERVICE_VAR" &>/dev/null; then
        echo "  Enabled: IGEN"
    else
        echo "  Enabled: NEM"
    fi
    
    if systemctl is-active "$RADIO_SERVICE_VAR" &>/dev/null; then
        echo "  Aktív: IGEN"
    else
        echo "  Aktív: NEM"
    fi
else
    echo "  ⚠️  FIGYELEM: A szolgáltatás nem található!"
    echo "  Ellenőrizd: systemctl list-unit-files | grep playout"
fi
echo ""

# Adatbázis és órarendek
if [ -f "$DB_PATH_VAR" ]; then
    echo "💾 Adatbázis: LÉTEZIK"
    echo "  Elérési út: $DB_PATH_VAR"
    
    if command -v sqlite3 &>/dev/null; then
        TOTAL_SCHEDULES=$(sqlite3 "$DB_PATH_VAR" "SELECT COUNT(*) FROM schedules;" 2>/dev/null)
        ENABLED_SCHEDULES=$(sqlite3 "$DB_PATH_VAR" "SELECT COUNT(*) FROM schedules WHERE enabled=1;" 2>/dev/null)
        
        echo "  Összes órarend: $TOTAL_SCHEDULES"
        echo "  Engedélyezett: $ENABLED_SCHEDULES"
        
        if [ "$ENABLED_SCHEDULES" -gt 0 ]; then
            echo ""
            echo "  Aktív órarendek:"
            sqlite3 "$DB_PATH_VAR" "SELECT '    ' || CASE day_of_week 
                WHEN 0 THEN 'Hétfő' 
                WHEN 1 THEN 'Kedd' 
                WHEN 2 THEN 'Szerda' 
                WHEN 3 THEN 'Csütörtök' 
                WHEN 4 THEN 'Péntek' 
                WHEN 5 THEN 'Szombat' 
                WHEN 6 THEN 'Vasárnap' 
            END || ': ' || start_time || ' - ' || stop_time
            FROM schedules WHERE enabled=1 ORDER BY day_of_week, start_time;" 2>/dev/null
        fi
    fi
elif [ -f "/opt/radio_scheduler/$DB_PATH_VAR" ]; then
    echo "💾 Adatbázis: LÉTEZIK (telepített helyen)"
    echo "  Elérési út: /opt/radio_scheduler/$DB_PATH_VAR"
else
    echo "💾 Adatbázis: NEM LÉTEZIK"
    echo "  Az első indítás után jön létre"
fi
echo ""

# Telepített fájlok
if [ -d "/opt/radio_scheduler" ]; then
    echo "📦 Telepítés: KÉSZ"
    echo "  Mappa: /opt/radio_scheduler"
else
    echo "📦 Telepítés: NEM TELEPÍTVE"
    echo "  Jelenlegi mappa: $(pwd)"
fi
echo ""

# Hálózat
echo "🌐 Hálózat:"
if netstat -tuln 2>/dev/null | grep -q ":$PORT_VAR " || ss -tuln 2>/dev/null | grep -q ":$PORT_VAR "; then
    echo "  Port $PORT_VAR: HALLGAT ✓"
    echo "  Web felület: http://localhost:$PORT_VAR"
    
    # IP címek megjelenítése
    if command -v hostname &>/dev/null; then
        IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ ! -z "$IP_ADDR" ]; then
            echo "  Távoli elérés: http://$IP_ADDR:$PORT_VAR"
        fi
    fi
else
    echo "  Port $PORT_VAR: NEM HALLGAT"
    echo "  Az alkalmazás valószínűleg nem fut"
fi
echo ""

echo "=========================================="
echo "📚 Dokumentáció:"
echo "  - README.md (általános)"
echo "  - AZURACAST_SETUP.md (AzuraCast specifikus)"
echo "  - QUICKSTART.md (gyors kezdés)"
echo ""
echo "🔧 Hasznos parancsok:"
echo "  - bash diagnose.sh (teljes diagnosztika)"
echo "  - bash test.sh (gyors teszt)"
echo "  - sudo systemctl status radio-scheduler"
echo "  - sudo systemctl status $RADIO_SERVICE_VAR"
echo "=========================================="
