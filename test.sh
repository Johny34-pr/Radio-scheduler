#!/bin/bash

# Gyors teszt script a Radio Scheduler működésének ellenőrzésére

echo "=========================================="
echo "Radio Scheduler Gyorsteszt"
echo "=========================================="
echo ""

PORT=${PORT:-86}

# 1. HTTP válasz teszt
echo "[1/4] HTTP kapcsolat tesztelése..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT 2>/dev/null)

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "302" ]; then
    echo "✓ SIKERES - HTTP $HTTP_CODE válasz érkezett"
else
    echo "✗ HIBA - HTTP $HTTP_CODE (vagy nincs válasz)"
    echo "  Tipp: Fut-e az alkalmazás? sudo python3 app.py"
    exit 1
fi

# 2. API teszt - státusz endpoint
echo ""
echo "[2/4] API státusz endpoint..."
STATUS=$(curl -s http://localhost:$PORT/api/service/status 2>/dev/null)

if echo "$STATUS" | grep -q "service"; then
    echo "✓ SIKERES - API válaszol"
    echo "  Válasz: $STATUS"
else
    echo "✗ HIBA - API nem válaszol megfelelően"
    exit 1
fi

# 3. Adatbázis teszt
echo ""
echo "[3/4] Adatbázis ellenőrzése..."
if [ -f "scheduler.db" ]; then
    SCHEDULE_COUNT=$(sqlite3 scheduler.db "SELECT COUNT(*) FROM schedules;" 2>/dev/null)
    echo "✓ SIKERES - Adatbázis elérhető"
    echo "  Órarendek száma: $SCHEDULE_COUNT"
else
    echo "✗ FIGYELEM - scheduler.db nem található"
fi

# 4. Port figyelés
echo ""
echo "[4/4] Port figyelés ellenőrzése..."
if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
    echo "✓ SIKERES - Port $PORT hallgat"
else
    echo "✗ HIBA - Port $PORT nem hallgat"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓✓✓ Minden teszt SIKERES! ✓✓✓"
echo "=========================================="
echo ""
echo "Web felület: http://localhost:$PORT"
echo "API dokumentáció: README.md"
echo ""
echo "Következő lépés:"
echo "  1. Nyisd meg böngészőben a web felületet"
echo "  2. Adj hozzá egy teszt órarendet"
echo "  3. Ellenőrizd a logokban: sudo journalctl -u radio-scheduler -f"
echo ""
