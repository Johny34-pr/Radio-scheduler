#!/bin/bash

# Rádió Scheduler indító script

cd "$(dirname "$0")"

# Környezeti változók
export RADIO_SERVICE="${RADIO_SERVICE:-radio.service}"
export PORT="${PORT:-86}"

echo "==================================="
echo "Radio Scheduler indítása..."
echo "==================================="
echo "Szolgáltatás: $RADIO_SERVICE"
echo "Port: $PORT"
echo "Munkamappa: $(pwd)"
echo "==================================="

# Python környezet ellenőrzése
if ! command -v python3 &> /dev/null; then
    echo "HIBA: python3 nem található!"
    exit 1
fi

# Függőségek ellenőrzése
echo "Függőségek ellenőrzése..."
pip3 install -q -r requirements.txt

# Alkalmazás indítása
echo "Alkalmazás indítása..."
python3 app.py
