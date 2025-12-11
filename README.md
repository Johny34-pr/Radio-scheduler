# Rádió Ütemező

Webes alkalmazás systemd szolgáltatások (AzuraCast playout stream) automatikus indítására és leállítására megadott időpontok szerint.

## 🚀 Gyors kezdés

```bash
# 1. Telepítés (root jogosultsággal)
sudo bash install.sh

# 2. Böngészőben nyisd meg
http://your-server-ip:86

# 3. Szolgáltatás ellenőrzése
sudo systemctl status radio-scheduler
sudo systemctl status azuracast-playout
```

**Probléma a port 86-tal?** Lásd a [Hibaelhárítás](#hibaelhárítás) szekciót alul!

**AzuraCast specifikus beállítások?** Nézd meg az [AZURACAST_SETUP.md](AZURACAST_SETUP.md) fájlt!

## Funkciók

- 📅 **Napcsoportos órarend beállítása**: 
  - Egy nap: pl. csak Hétfő 07:30-08:00
  - Naptartomány: pl. Hétfő-Péntek 07:30-08:00
  - Hétvége: pl. Szombat-Vasárnap 09:00-20:00
- ⏰ **Percre pontos időzítés**: Pontos időpontok megadása (HH:MM formátumban)
- 🏷️ **Elnevezett órarendek**: Adj nevet az órarendeknek (pl. "Hétköznapi műsor")
- 🎛️ **Manuális vezérlés**: A szolgáltatás bármikor indítható vagy leállítható kézzel is
- 📊 **Státusz megjelenítés**: Valós idejű információ a szolgáltatás állapotáról
- 🔄 **Enable/Disable**: Órarendek ideiglenesen kikapcsolhatók törlés nélkül

## Telepítés

### Gyors telepítés (ajánlott)

```bash
# 1. Letöltés/másolás a szerverre
cd /root
git clone <repository-url> radio_scheduler
# VAGY másolás: scp -r radio_scheduler/ user@server:/root/

# 2. Belépés a mappába
cd radio_scheduler

# 3. Telepítő script futtatása (root jogosultság szükséges!)
sudo bash install.sh
```

A telepítő automatikusan:
- Telepíti a Python függőségeket
- Beállítja a systemd szolgáltatást
- Elindítja az alkalmazást

### Manuális telepítés

### 1. Függőségek telepítése

```bash
pip3 install -r requirements.txt
```

### 2. Környezeti változók beállítása (opcionális)

```bash
# Systemd szolgáltatás neve (alapértelmezett: azuracast-playout.service)
export RADIO_SERVICE=mas-szolgaltatas.service

# Port (alapértelmezett: 86)
export PORT=86

# Adatbázis elérési út (alapértelmezett: scheduler.db)
export DB_PATH=/var/lib/radio_scheduler/scheduler.db
```

### 3. Alkalmazás indítása

#### Közvetlen indítás (teszt célra):
```bash
# Root jogosultsággal (a 86-os port miatt)
sudo python3 app.py
```

#### Vagy a start.sh script használata:
```bash
sudo bash start.sh
```

## Systemd szolgáltatásként való futtatás

A telepítő script (`install.sh`) automatikusan beállítja, de manuálisan is létrehozhatod:

### Automatikus (install.sh használata):
```bash
sudo bash install.sh
```

### Manuális beállítás:

Hozz létre egy systemd unit file-t: `/etc/systemd/system/radio-scheduler.service`

```ini
[Unit]
Description=Radio Scheduler Web Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/radio_scheduler
Environment="RADIO_SERVICE=radio.service"
Environment="PORT=86"
ExecStart=/usr/bin/python3 /opt/radio_scheduler/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Engedélyezés és indítás:

```bash
sudo systemctl daemon-reload
sudo systemctl enable radio-scheduler
sudo systemctl start radio-scheduler
```

### Szolgáltatás kezelése:

```bash
# Státusz ellenőrzése
sudo systemctl status radio-scheduler

# Logok megtekintése
sudo journalctl -u radio-scheduler -f

# Újraindítás
sudo systemctl restart radio-scheduler

# Leállítás
sudo systemctl stop radio-scheduler
```

## Jogosultságok

A szolgáltatás indításához/leállításához sudo jogosultság szükséges. 

### Opció 1: Root-ként futtatás (egyszerűbb)

Az alkalmazást root userként futtatva automatikusan van joga a systemctl parancsokhoz:

```bash
sudo python3 app.py
```

### Opció 2: Sudoers konfiguráció (biztonságosabb)

Ha nem root felhasználóként szeretnéd futtatni, adj hozzá egy sort a `/etc/sudoers` fájlhoz (`visudo` használatával):

```
radio ALL=(ALL) NOPASSWD: /bin/systemctl start radio.service, /bin/systemctl stop radio.service, /bin/systemctl is-active radio.service
```

Ahol `radio` a felhasználó neve, aki alatt az alkalmazás fut.

Ezután módosítsd a systemd service file-t:
```ini
User=radio  # root helyett
```

## API végpontok

### Órarendek

- `GET /api/schedules` - Összes órarend lekérdezése
- `POST /api/schedules` - Új órarend létrehozása
- `PUT /api/schedules/<id>` - Órarend módosítása
- `DELETE /api/schedules/<id>` - Órarend törlése

### Szolgáltatás vezérlés

- `GET /api/service/status` - Szolgáltatás állapota
- `POST /api/service/start` - Szolgáltatás indítása
- `POST /api/service/stop` - Szolgáltatás leállítása

## Hibaelhárítás

### A szolgáltatás nem indul el a 86-os porton

**Probléma:** `curl localhost:86` - Kapcsolat elutasítva

**Megoldások:**

1. **Ellenőrizd, hogy fut-e az alkalmazás:**
```bash
sudo systemctl status radio-scheduler
# VAGY ha közvetlenül indítottad:
ps aux | grep app.py
```

2. **Nézd meg a logokat:**
```bash
sudo journalctl -u radio-scheduler -n 50
# VAGY
sudo journalctl -u radio-scheduler -f  # élő logok
```

3. **Privilegizált port jogosultság:**
A 86-os port < 1024, ezért root jogosultság kell:
```bash
sudo python3 app.py
```

4. **Port már használatban van:**
```bash
sudo netstat -tulpn | grep :86
# VAGY
sudo lsof -i :86
```

5. **Tűzfal beállítás:**
```bash
sudo ufw allow 86/tcp
# VAGY firewalld esetén:
sudo firewall-cmd --add-port=86/tcp --permanent
sudo firewall-cmd --reload
```

6. **Másik portot használni:**
```bash
export PORT=5000
sudo python3 app.py
# Vagy a systemd service-ben módosítsd az Environment változót
```

### Systemctl parancsok nem működnek

**Probléma:** Permission denied vagy sudo kérés

**Megoldás:**
- Root-ként futtasd az alkalmazást: `sudo python3 app.py`
- VAGY állítsd be a sudoers-t (lásd Jogosultságok szekció)

### A scheduler nem indítja/állítja a szolgáltatást

**Ellenőrzés:**
```bash
# Nézd meg a scheduler logokat
sudo journalctl -u radio-scheduler | grep "Service started\|Service stopped"

# Ellenőrizd az órarendeket az adatbázisban
sqlite3 scheduler.db "SELECT * FROM schedules;"
```

**Tipp:** A scheduler 30 másodpercenként ellenőriz, kis késés lehet az időzítésben.

## GYIK (Gyakran Ismételt Kérdések)

### Hogyan futtassam a szerveren?

A legegyszerűbb:
```bash
cd /root/radio_scheduler  # vagy ahol a fájlok vannak
sudo bash install.sh
```

Ez automatikusan telepít mindent és beállítja systemd szolgáltatásként.

### Manuálisan hogyan indítsam?

```bash
cd /root/radio_scheduler
sudo python3 app.py
```

### Hogyan állítsam át más portra?

**Környezeti változóval:**
```bash
export PORT=8080
sudo python3 app.py
```

**Systemd service-ben** módosítsd az `Environment` sort:
```bash
sudo nano /etc/systemd/system/radio-scheduler.service
# Változtasd át: Environment="PORT=8080"
sudo systemctl daemon-reload
sudo systemctl restart radio-scheduler
```

### Hogyan nézem meg a logokat?

```bash
# Systemd logok
sudo journalctl -u radio-scheduler -f

# Utolsó 100 sor
sudo journalctl -u radio-scheduler -n 100

# Csak a hibák
sudo journalctl -u radio-scheduler -p err
```

### Nem indul el, mit tegyek?

Futtasd a diagnosztikai scriptet:
```bash
bash diagnose.sh
```

Vagy manuális ellenőrzés:
```bash
# 1. Fut-e az alkalmazás?
sudo systemctl status radio-scheduler

# 2. Port foglalt?
sudo netstat -tulpn | grep :86

# 3. Jogosultság?
whoami  # root-nak kell lennie

# 4. Újraindítás
sudo systemctl restart radio-scheduler
```

### Hogyan változtatom meg a kezelt szolgáltatást?

**Környezeti változóval:**
```bash
export RADIO_SERVICE=my-custom.service
sudo python3 app.py
```

**Systemd service-ben:**
```bash
sudo nano /etc/systemd/system/radio-scheduler.service
# Változtasd át: Environment="RADIO_SERVICE=my-custom.service"
sudo systemctl daemon-reload
sudo systemctl restart radio-scheduler
```

### Távoli elérésnél nem működik (SSH-n curl OK, böngésző NEM)?

**Ez tűzfal probléma!** A port blokkolva van külső hozzáféréshez.

**Gyors megoldás:**
```bash
sudo bash open-firewall.sh
```

**Vagy manuálisan:**
```bash
# UFW esetén
sudo ufw allow 86/tcp
sudo ufw status

# firewalld esetén
sudo firewall-cmd --add-port=86/tcp --permanent
sudo firewall-cmd --reload

# iptables esetén
sudo iptables -A INPUT -p tcp --dport 86 -j ACCEPT
sudo netfilter-persistent save  # vagy mentsd másképp
```

**Ellenőrzés:**
```bash
# UFW
sudo ufw status | grep 86

# Firewalld
sudo firewall-cmd --list-ports | grep 86

# IPTables
sudo iptables -L INPUT -n | grep 86
```

### Használati példák

### Példa 1: Hétköznapi műsor (Hétfő-Péntek)
```
Név: Hétköznapi adás
Nap (kezdő): Hétfő
Nap (vég): Péntek
Indítás: 07:30
Leállítás: 22:00
```
Ez **automatikusan** minden hétköznap (H-P) 7:30-kor indítja és 22:00-kor állítja le a szolgáltatást.

### Példa 2: Csak hétfői speciális műsor
```
Név: Hétfői speciál
Nap (kezdő): Hétfő
Nap (vég): Hétfő
Indítás: 07:30
Leállítás: 08:00
```
Ez **csak hétfőn** fut 7:30-8:00 között.

### Példa 3: Hétvégi non-stop
```
Név: Hétvégi adás
Nap (kezdő): Szombat
Nap (vég): Vasárnap
Indítás: 00:00
Leállítás: 23:59
```
Szombat és vasárnap egész nap fut.

### Példa 4: Hétfő-Kedd reggeli blokk
```
Név: H-K reggel
Nap (kezdő): Hétfő
Nap (vég): Kedd
Indítás: 06:00
Leállítás: 09:00
```
Hétfőn és kedden reggel 6-9 között.

## Hasznos scriptek

Az alkalmazás számos helper scriptet tartalmaz:

```bash
# Jogosultságok beállítása (először ezt futtasd!)
bash setup-permissions.sh

# Automatikus telepítés
sudo bash install.sh

# Manuális indítás
bash start.sh

# Konfiguráció megjelenítése
bash show-config.sh

# Hibadiagnosztika (ha valami nem működik)
bash diagnose.sh

# Gyors működés teszt
bash test.sh

# Adatbázis migráció (ha frissítesz régi verzióról)
bash migrate-db.sh
```

## Frissítés régi verzióról

Ha már használod az alkalmazást és frissítesz az új napcsoport funkcióra:

```bash
# 1. Állítsd le a szolgáltatást
sudo systemctl stop radio-scheduler

# 2. Backup (opcionális, de ajánlott)
cp scheduler.db scheduler.db.backup

# 3. Futtasd a migrációt
bash migrate-db.sh

# 4. Indítsd újra
sudo systemctl start radio-scheduler
```

Az automatikus migráció:
- Megőrzi a régi órarendeket
- Átalakítja őket az új formátumra (egy nap = day_start és day_end ugyanaz)
- Automatikus nevet ad nekik
- Backupot készít az eredeti adatbázisról

## Adatbázis

Az alkalmazás SQLite adatbázist használ (`scheduler.db`), amely automatikusan létrejön első indításkor.

## Fejlesztés

### Projekt struktúra

```
radio_scheduler/
├── app.py                      # Fő alkalmazás (Flask backend + scheduler)
├── config.py                   # Konfigurációs beállítások
├── templates/
│   └── index.html             # Web UI
├── scheduler.db               # SQLite adatbázis (auto-generált)
├── requirements.txt           # Python függőségek
├── radio-scheduler.service    # Systemd unit file
├── install.sh                 # Automatikus telepítő script
├── start.sh                   # Indító script
├── diagnose.sh                # Hibadiagnosztika script
├── test.sh                    # Gyors teszt script
├── setup-permissions.sh       # Jogosultságok beállítása
├── .gitignore
├── README.md                  # Fő dokumentáció
├── QUICKSTART.md              # Gyors indítási útmutató
├── AZURACAST_SETUP.md         # AzuraCast specifikus beállítások
└── SZERVER_TELEPITES.md       # Részletes telepítési útmutató
```

### Környezeti változók

- `RADIO_SERVICE` - Kezelt systemd szolgáltatás neve (alapértelmezett: `azuracast-playout.service`)
- `PORT` - Web szerver portja (alapértelmezett: `86`)
- `DB_PATH` - SQLite adatbázis elérési útja (alapértelmezett: `scheduler.db`)
- `DEBUG` - Debug mód (alapértelmezett: `False`)

## További dokumentáció

- **[QUICKSTART.md](QUICKSTART.md)** - Gyors telepítési útmutató
- **[AZURACAST_SETUP.md](AZURACAST_SETUP.md)** - AzuraCast specifikus beállítások és tippek
- **[SZERVER_TELEPITES.md](SZERVER_TELEPITES.md)** - Részletes hibaelhárítás

## Licenc

MIT License
