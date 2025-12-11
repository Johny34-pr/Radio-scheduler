#!/bin/bash

# Tűzfal port megnyitó script a Radio Scheduler számára

PORT=${PORT:-86}

echo "=========================================="
echo "Tűzfal beállítása"
echo "=========================================="
echo ""
echo "Port: $PORT"
echo ""

# Root jogosultság ellenőrzése
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  FIGYELEM: Root jogosultság szükséges!"
    echo "Használd: sudo bash open-firewall.sh"
    exit 1
fi

# UFW ellenőrzése
if command -v ufw &> /dev/null; then
    echo "[1/3] UFW észlelve"
    
    if ufw status | grep -q "Status: active"; then
        echo "  UFW aktív, port megnyitása..."
        ufw allow $PORT/tcp
        
        if ufw status | grep -q "$PORT"; then
            echo "  ✓ Port $PORT/tcp megnyitva!"
        else
            echo "  ⚠️  Nem sikerült megnyitni a portot"
        fi
    else
        echo "  UFW nincs aktív állapotban"
    fi
    echo ""
fi

# Firewalld ellenőrzése
if command -v firewall-cmd &> /dev/null; then
    echo "[2/3] Firewalld észlelve"
    
    if firewall-cmd --state 2>/dev/null | grep -q "running"; then
        echo "  Firewalld fut, port megnyitása..."
        firewall-cmd --add-port=$PORT/tcp --permanent
        firewall-cmd --reload
        
        if firewall-cmd --list-ports 2>/dev/null | grep -q "$PORT/tcp"; then
            echo "  ✓ Port $PORT/tcp megnyitva!"
        else
            echo "  ⚠️  Nem sikerült megnyitni a portot"
        fi
    else
        echo "  Firewalld nem fut"
    fi
    echo ""
fi

# IPTables ellenőrzése
if command -v iptables &> /dev/null; then
    echo "[3/3] IPTables észlelve"
    
    if iptables -L INPUT -n 2>/dev/null | grep -q "dpt:$PORT"; then
        echo "  ✓ IPTables már tartalmaz szabályt a $PORT portra"
    else
        echo "  IPTables szabály hozzáadása..."
        iptables -A INPUT -p tcp --dport $PORT -j ACCEPT
        
        # Mentés (Ubuntu/Debian esetén)
        if command -v netfilter-persistent &> /dev/null; then
            netfilter-persistent save
            echo "  ✓ IPTables szabály mentve (netfilter-persistent)"
        elif command -v iptables-save &> /dev/null; then
            iptables-save > /etc/iptables/rules.v4 2>/dev/null || \
            iptables-save > /etc/sysconfig/iptables 2>/dev/null
            echo "  ✓ IPTables szabály mentve"
        else
            echo "  ⚠️  FIGYELEM: IPTables szabály hozzáadva, de nem mentve!"
            echo "     Újraindítás után el fog veszni!"
        fi
    fi
    echo ""
fi

echo "=========================================="
echo "Tűzfal beállítás kész!"
echo "=========================================="
echo ""
echo "Teszteld most a böngészőből:"
echo "  http://$(hostname -I | awk '{print $1}'):$PORT"
echo ""
echo "Vagy parancssorból:"
echo "  curl http://localhost:$PORT"
echo ""
