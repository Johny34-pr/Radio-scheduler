# SZERVER TELEPÍTÉSI ÚTMUTATÓ

## Áttekintés

Ez az alkalmazás az **azuracast-playout.service** systemd szolgáltatást kezeli automatikusan, órarend szerint indítva és leállítva azt.

## Jelenlegi helyzet

A szerveren (`root@szerver:~/radio_scheuler#`) a következő hibaüzenet jelent meg:
```
curl: (7) Failed to connect to localhost port 86: Kapcsolat elutasítva
```

Ez azt jelenti, hogy az alkalmazás **nem fut** a 86-os porton.

## Megoldás lépésről lépésre

### 1. Ellenőrizd a mappa nevét és tartalmát

```bash
cd /root
ls -la | grep radio

# Ha radio_scheuler néven van (elírással), nevezd át:
mv radio_scheuler radio_scheduler

cd radio_scheduler
ls -la
```

**Elvárt fájlok:**
- `app.py`
- `templates/index.html`
- `requirements.txt`
- `install.sh`
- `start.sh`
- `diagnose.sh`

### 2. Futtasd a diagnosztikai scriptet

```bash
chmod +x diagnose.sh
bash diagnose.sh
```

Ez megmutatja, mi a probléma.

### 3A. Automatikus telepítés (AJÁNLOTT)

```bash
chmod +x install.sh
sudo bash install.sh
```

Ez:
- Telepíti a függőségeket
- Beállítja a systemd szolgáltatást
- Elindítja az alkalmazást

### 3B. VAGY Manuális indítás (teszteléshez)

```bash
# Függőségek telepítése
pip3 install -r requirements.txt

# Alkalmazás indítása
sudo python3 app.py
```

Látnod kell ezt:
```
==================================================
Radio Scheduler started
==================================================
Managing service: radio.service
Web interface: http://localhost:86
Database: scheduler.db
==================================================
 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:86
 * Running on http://YOUR_IP:86
```

### 4. Ellenőrzés

Új terminálon (vagy háttérben hagyd futni):

```bash
# Curl teszt
curl http://localhost:86

# Böngészőben (ha van GUI)
firefox http://localhost:86

# Vagy távolról (a saját gépedről)
# http://szerver-ip:86
```

### 5. Ha még mindig nem működik

**A. Ellenőrizd a portot:**
```bash
sudo netstat -tulpn | grep :86
# VAGY
sudo ss -tulpn | grep :86
```

Ha nincs output, az app nem hallgat a porton.

**B. Ellenőrizd, fut-e a Python folyamat:**
```bash
ps aux | grep app.py
```

**C. Próbálj meg másik portot:**
```bash
export PORT=5000
sudo python3 app.py
# Majd teszteld: curl http://localhost:5000
```

**D. Nézd meg a hibákat:**
```bash
# Ha systemd-ből fut
sudo journalctl -u radio-scheduler -n 50

# Ha közvetlenül indítottad, nézd a terminál outputot
```

### 6. Systemd szolgáltatásként futtatás (termeléshez)

Miután működik manuálisan, állítsd be systemd-vel:

```bash
sudo bash install.sh
```

Vagy manuálisan:
```bash
# Service fájl másolása
sudo cp radio-scheduler.service /etc/systemd/system/

# Systemd újratöltése
sudo systemctl daemon-reload

# Engedélyezés és indítás
sudo systemctl enable radio-scheduler
sudo systemctl start radio-scheduler

# Státusz
sudo systemctl status radio-scheduler
```

## Gyakori problémák és megoldások

### "Permission denied" a systemctl használatakor

Az app.py már kezeli a sudo-t automatikusan. Csak győződj meg róla, hogy root-ként futtatod:
```bash
sudo python3 app.py
```

### "Address already in use" hiba

A 86-os port foglalt. Használj másik portot:
```bash
export PORT=8080
sudo python3 app.py
```

### Nem éri el távolról

Tűzfal beállítás:
```bash
# UFW
sudo ufw allow 86/tcp

# Firewalld
sudo firewall-cmd --add-port=86/tcp --permanent
sudo firewall-cmd --reload
```

### Windows Subsystem for Linux (WSL) alatt futtatod?

A systemctl nem mindig működik WSL-ben. Használd közvetlenül:
```bash
python3 app.py
```

## Tesztelési checklist

- [ ] Fájlok a helyükön vannak
- [ ] Függőségek telepítve (`pip3 install -r requirements.txt`)
- [ ] Alkalmazás elindul (`sudo python3 app.py`)
- [ ] Port 86 hallgat (`netstat -tulpn | grep :86`)
- [ ] Curl válaszol (`curl http://localhost:86`)
- [ ] Böngészőben betölt a UI
- [ ] Systemd szolgáltatás fut (`systemctl status radio-scheduler`)

## Gyors parancsok referencia

```bash
# Indítás
sudo python3 app.py

# Systemd státusz
sudo systemctl status radio-scheduler

# Logok
sudo journalctl -u radio-scheduler -f

# Újraindítás
sudo systemctl restart radio-scheduler

# Leállítás
sudo systemctl stop radio-scheduler

# Port ellenőrzés
sudo netstat -tulpn | grep :86

# Diagnosztika
bash diagnose.sh
```

## Következő lépések telepítés után

1. Nyisd meg böngészőben: `http://szerver-ip:86`
2. Adj hozzá egy teszt órarendet
3. Ellenőrizd, hogy a szolgáltatás fut-e: `sudo systemctl status radio.service`
4. Nézd meg a scheduler logokat: `sudo journalctl -u radio-scheduler -f`

---

**Bármilyen probléma esetén**, küldd el a `diagnose.sh` kimenetét!
