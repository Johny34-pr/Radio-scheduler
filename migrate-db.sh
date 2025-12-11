#!/bin/bash

# Adatbázis migráció script - régi formátumról az új napcsoport alapú formátumra

echo "=========================================="
echo "Adatbázis Migráció"
echo "=========================================="
echo ""

DB_PATH="${DB_PATH:-scheduler.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "✓ Új telepítés - nincs szükség migrációra"
    echo "  Az adatbázis első indításkor létrejön."
    exit 0
fi

echo "Adatbázis található: $DB_PATH"
echo ""

# Ellenőrizzük a régi struktúrát
if sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='schedules';" | grep -q "schedules"; then
    echo "Schedules tábla létezik"
    
    # Ellenőrizzük az oszlopokat
    if sqlite3 "$DB_PATH" "PRAGMA table_info(schedules);" | grep -q "day_of_week"; then
        echo "⚠️  RÉGI FORMÁTUM ÉSZLELVE (day_of_week oszlop)"
        echo ""
        echo "Migráció indítása..."
        echo ""
        
        # Backup készítése
        BACKUP_FILE="${DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$DB_PATH" "$BACKUP_FILE"
        echo "✓ Backup készült: $BACKUP_FILE"
        
        # Migráció SQL
        sqlite3 "$DB_PATH" << 'EOF'
-- Ideiglenes tábla létrehozása új struktúrával
CREATE TABLE schedules_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    day_start INTEGER NOT NULL,
    day_end INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    stop_time TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Adatok migrálása (day_of_week -> day_start és day_end)
INSERT INTO schedules_new (id, name, day_start, day_end, start_time, stop_time, enabled, created_at)
SELECT 
    id,
    CASE day_of_week
        WHEN 0 THEN 'Hétfő'
        WHEN 1 THEN 'Kedd'
        WHEN 2 THEN 'Szerda'
        WHEN 3 THEN 'Csütörtök'
        WHEN 4 THEN 'Péntek'
        WHEN 5 THEN 'Szombat'
        WHEN 6 THEN 'Vasárnap'
    END || ' ' || start_time || '-' || stop_time as name,
    day_of_week as day_start,
    day_of_week as day_end,
    start_time,
    stop_time,
    enabled,
    created_at
FROM schedules;

-- Régi tábla törlése
DROP TABLE schedules;

-- Új tábla átnevezése
ALTER TABLE schedules_new RENAME TO schedules;
EOF
        
        echo "✓ Migráció sikeres!"
        echo ""
        
        # Statisztika
        MIGRATED_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM schedules;")
        echo "Migrált órarendek száma: $MIGRATED_COUNT"
        
    elif sqlite3 "$DB_PATH" "PRAGMA table_info(schedules);" | grep -q "day_start"; then
        echo "✓ Már új formátum (day_start, day_end oszlopok)"
        echo "  Nincs szükség migrációra"
    else
        echo "⚠️  Ismeretlen tábla struktúra"
    fi
else
    echo "✓ Új telepítés - schedules tábla még nem létezik"
fi

echo ""
echo "=========================================="
echo "Migráció kész!"
echo "=========================================="
echo ""
echo "Most indíthatod az alkalmazást:"
echo "  sudo python3 app.py"
echo ""
