#!/bin/bash

# Alkalmazás újraindítása cache ürítéssel

echo "=========================================="
echo "Radio Scheduler Újraindítása"
echo "=========================================="
echo ""

# Systemd szolgáltatás újraindítása
if systemctl is-active --quiet radio-scheduler; then
    echo "Systemd szolgáltatás újraindítása..."
    sudo systemctl restart radio-scheduler
    
    echo "Várakozás 2 másodperc..."
    sleep 2
    
    echo ""
    echo "Szolgáltatás státusza:"
    sudo systemctl status radio-scheduler --no-pager -l | head -15
    
    echo ""
    echo "✓ Újraindítás kész!"
    echo ""
    echo "Böngésző cache ürítése:"
    echo "  - Chrome/Edge: Ctrl+Shift+R vagy Ctrl+F5"
    echo "  - Firefox: Ctrl+Shift+R vagy Ctrl+F5"
    echo "  - Safari: Cmd+Shift+R"
    echo ""
    echo "Vagy nyisd meg privát/inkognitó módban:"
    echo "  http://$(hostname -I | awk '{print $1}'):86"
    
else
    echo "⚠️  A radio-scheduler szolgáltatás nem fut systemd-ből"
    echo ""
    echo "Ha manuálisan indítottad, állítsd le (Ctrl+C) és indítsd újra:"
    echo "  sudo python3 app.py"
fi

echo ""
echo "=========================================="
