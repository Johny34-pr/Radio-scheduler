#!/bin/bash
# AzuraCast vezérlés diagnosztika

echo "=== AzuraCast Integration Diagnostics ==="
echo ""

echo "1. Beállítások az adatbázisban:"
echo "-------------------------------"
cd /opt/radio_scheduler
sqlite3 scheduler.db "SELECT key, CASE WHEN key='azuracast_api_key' THEN '***' || substr(value, -4) ELSE value END as value FROM settings WHERE key LIKE '%azuracast%' OR key='control_azuracast' OR key='stream_url';"
echo ""

echo "2. Service environment:"
echo "----------------------"
if [ -f /etc/systemd/system/azuracast-playout.service.d/override.conf ]; then
    cat /etc/systemd/system/azuracast-playout.service.d/override.conf
else
    echo "Override file nem található"
fi
echo ""

echo "3. Utolsó 20 radio-scheduler log (AzuraCast-tal kapcsolatos):"
echo "-------------------------------------------------------------"
journalctl -u radio-scheduler -n 50 --no-pager | grep -i azuracast | tail -20
echo ""

echo "4. AzuraCast playout service státusz:"
echo "--------------------------------------"
systemctl is-active azuracast-playout.service
echo ""

echo "5. API teszt (ha van API key):"
echo "-------------------------------"
API_URL=$(sqlite3 scheduler.db "SELECT value FROM settings WHERE key='azuracast_api_url';")
STATION_ID=$(sqlite3 scheduler.db "SELECT value FROM settings WHERE key='azuracast_station_id';")
API_KEY=$(sqlite3 scheduler.db "SELECT value FROM settings WHERE key='azuracast_api_key';")

if [ -n "$API_URL" ] && [ -n "$API_KEY" ]; then
    echo "GET $API_URL/api/station/$STATION_ID"
    curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/station/$STATION_ID" | python3 -m json.tool 2>/dev/null | head -30 || echo "API hívás sikertelen"
else
    echo "API URL vagy Key nincs beállítva"
fi

echo ""
echo "=== Diagnosztika kész ==="
