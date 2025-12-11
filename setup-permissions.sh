#!/bin/bash
# Fájl jogosultságok beállítása

echo "Executable jogosultságok beállítása..."

chmod +x install.sh
chmod +x start.sh
chmod +x restart.sh
chmod +x diagnose.sh
chmod +x test.sh
chmod +x show-config.sh
chmod +x open-firewall.sh
chmod +x migrate-db.sh

echo "✓ Kész!"
echo ""
echo "Most már futtathatod:"
echo "  - ./install.sh       (teljes telepítés)"
echo "  - ./start.sh         (alkalmazás indítása)"
echo "  - ./restart.sh       (újraindítás)"
echo "  - ./open-firewall.sh (tűzfal port megnyitása)"
echo "  - ./migrate-db.sh    (adatbázis migráció)"
echo "  - ./diagnose.sh      (hibadiagnosztika)"
echo "  - ./test.sh          (gyors működés teszt)"
echo "  - ./show-config.sh   (konfiguráció megjelenítése)"
