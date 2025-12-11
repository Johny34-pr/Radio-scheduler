# AzuraCast Playout Ütemező

Ez az alkalmazás az **azuracast-playout.service** automatikus indítását és leállítását kezeli órarend szerint.

## Az AzuraCast Playout Szolgáltatás

A jelenlegi szolgáltatás:
- **Név**: `azuracast-playout.service`
- **Funkció**: AzuraCast stream lejátszása mixerhez
- **Stream URL**: `http://10.204.131.131:8000/radio.mp3`
- **Audio device**: `alsa/plughw:1,0`
- **Lejátszó**: `mpv`

## Telepítés

### 1. Fájlok feltöltése a szerverre

```bash
# SCP-vel
scp -r radio_scheduler root@szerver-ip:/root/

# Vagy WinSCP / FileZilla GUI-val
```

### 2. Telepítés a szerveren

```bash
ssh root@szerver-ip
cd /root/radio_scheduler

# Jogosultságok
bash setup-permissions.sh

# Telepítés
sudo bash install.sh
```

### 3. Ellenőrzés

```bash
# Scheduler szolgáltatás
sudo systemctl status radio-scheduler

# AzuraCast playout szolgáltatás
sudo systemctl status azuracast-playout

# Tűzfal (FONTOS!)
sudo bash open-firewall.sh

# Web felület (SSH-n)
curl http://localhost:86

# Böngészőből
# http://szerver-ip:86
```

## Használat

### Web felület

Nyisd meg böngészőben: `http://szerver-ip:86`

### Órarend beállítása

**Példa 1: Hétköznap reggeli műsor (Hétfő-Péntek 06:00 - 09:00)**

1. Nyisd meg a web felületet
2. Adj hozzá új órarendet:
   - Név: "Reggeli műsor"
   - Nap (kezdő): Hétfő
   - Nap (vég): Péntek
   - Indítás: 06:00
   - Leállítás: 09:00

**Példa 2: Csak hétfői speciális műsor (07:30 - 08:00)**

1. Új órarend:
   - Név: "Hétfői speciál"
   - Nap (kezdő): Hétfő
   - Nap (vég): Hétfő
   - Indítás: 07:30
   - Leállítás: 08:00

**Példa 3: Hétvégi non-stop (Szombat-Vasárnap 00:00 - 23:59)**

1. Új órarend:
   - Név: "Hétvégi non-stop"
   - Nap (kezdő): Szombat
   - Nap (vég): Vasárnap
   - Indítás: 00:00
   - Leállítás: 23:59

**Példa 4: Hétfő-Kedd délelőtti blokk (10:00 - 12:00)**

1. Új órarend:
   - Név: "H-K délelőtt"
   - Nap (kezdő): Hétfő
   - Nap (vég): Kedd
   - Indítás: 10:00
   - Leállítás: 12:00

### Manuális vezérlés

A web felületen vagy parancssorban:

```bash
# Azonnali indítás
sudo systemctl start azuracast-playout

# Azonnali leállítás
sudo systemctl stop azuracast-playout

# Státusz
sudo systemctl status azuracast-playout
```

## Működés

Az alkalmazás:
1. **Figyeli az órarendeket** - 30 másodpercenként ellenőrzi
2. **Pontosan indít** - A megadott időpontban `systemctl start azuracast-playout`
3. **Pontosan leállít** - A megadott időpontban `systemctl stop azuracast-playout`
4. **Logol** - Minden műveletet naplóz

## Logok és monitorozás

### Radio Scheduler logok

```bash
# Élő logok
sudo journalctl -u radio-scheduler -f

# Utolsó 50 sor
sudo journalctl -u radio-scheduler -n 50

# Csak az indítás/leállítás események
sudo journalctl -u radio-scheduler | grep "Service started\|Service stopped"
```

### AzuraCast Playout logok

```bash
# Élő logok
sudo journalctl -u azuracast-playout -f

# Státusz
sudo systemctl status azuracast-playout
```

## Tipikus beállítások

### Rádió műsor órarend példák

**Teljes hétköznap (Hétfő-Péntek 06:00 - 22:00)**
- Név: "Hétköznapi adás"
- Napok: Hétfő - Péntek
- Indítás: 06:00
- Leállítás: 22:00

**Hétvége más időpontban (Szombat-Vasárnap 08:00 - 20:00)**
- Név: "Hétvégi adás"
- Napok: Szombat - Vasárnap
- Indítás: 08:00
- Leállítás: 20:00

**Reggeli műsor hétköznap (Hétfő-Péntek 06:00 - 09:00)**
- Név: "Reggeli show"
- Napok: Hétfő - Péntek
- Indítás: 06:00
- Leállítás: 09:00

**Csak pénteki különkiadás (Péntek 20:00 - 23:00)**
- Név: "Pénteki buli"
- Napok: Péntek - Péntek
- Indítás: 20:00
- Leállítás: 23:00

### Energia takarékosság

**Éjszakai leállítás minden nap**
- Név: "Napi adás"
- Napok: Hétfő - Vasárnap
- Indítás: 06:00
- Leállítás: 23:00

**Csak munkaidőben (Hétfő-Péntek 08:00 - 17:00)**
- Név: "Munkaidő"
- Napok: Hétfő - Péntek
- Indítás: 08:00
- Leállítás: 17:00

## Hibaelhárítás

### Az AzuraCast playout nem indul

```bash
# 1. Ellenőrizd a szolgáltatást
sudo systemctl status azuracast-playout

# 2. Nézd meg a hibákat
sudo journalctl -u azuracast-playout -n 50

# 3. Teszteld manuálisan
sudo systemctl start azuracast-playout

# 4. Ellenőrizd az audio device-ot
aplay -l  # Lista az audio eszközökről
amixer -c 1 scontrols  # Mixer beállítások
```

### A scheduler nem indítja/állítja a szolgáltatást

```bash
# 1. Scheduler logok
sudo journalctl -u radio-scheduler -f

# 2. Órarendek az adatbázisban
sqlite3 /opt/radio_scheduler/scheduler.db "SELECT * FROM schedules WHERE enabled=1;"

# 3. Manuális teszt a web felületről
# Kattints a "▶ Indítás" gombra és figyeld a logokat
```

### Stream URL nem elérhető

Az AzuraCast playout szolgáltatás `http://10.204.131.131:8000/radio.mp3` URL-t használ.

```bash
# Ellenőrizd a stream elérhetőségét
curl -I http://10.204.131.131:8000/radio.mp3

# Vagy hallgass bele
mpv http://10.204.131.131:8000/radio.mp3
```

Ha nem elérhető:
1. Ellenőrizd az AzuraCast szolgáltatást
2. Ellenőrizd a hálózati kapcsolatot
3. Módosítsd az URL-t a szolgáltatás fájlban, ha szükséges

### Stream URL módosítása

Ha az AzuraCast stream URL megváltozott:

```bash
# Szerkeszd a service fájlt
sudo nano /etc/systemd/system/azuracast-playout.service

# Módosítsd ezt a sort:
# Environment=STREAM_URL=http://10.204.131.131:8000/radio.mp3

# Újratöltés
sudo systemctl daemon-reload
sudo systemctl restart azuracast-playout
```

### Böngészőből nem elérhető a web felület (port 86)

**Probléma:** SSH-n `curl http://localhost:86` működik, de böngészőből nem.

**OK:** Tűzfal blokkolja a portot.

**Megoldás:**
```bash
# Automatikus
sudo bash open-firewall.sh

# VAGY manuálisan
sudo ufw allow 86/tcp
# vagy
sudo firewall-cmd --add-port=86/tcp --permanent && sudo firewall-cmd --reload
```

**Ellenőrzés:**
```bash
# Böngészőben próbáld újra
http://szerver-ip:86

# Vagy curl másik gépről
curl http://szerver-ip:86
```

## Hasznos parancsok

```bash
# Scheduler státusz
sudo systemctl status radio-scheduler

# AzuraCast playout státusz
sudo systemctl status azuracast-playout

# Scheduler újraindítás (pl. kód frissítés után)
sudo systemctl restart radio-scheduler

# Órarendek listázása
sqlite3 /opt/radio_scheduler/scheduler.db "SELECT * FROM schedules ORDER BY day_of_week, start_time;"

# Web felület port ellenőrzés
sudo netstat -tulpn | grep :86

# Mindkét szolgáltatás élő logja egyszerre
sudo journalctl -u radio-scheduler -u azuracast-playout -f
```

## Fejlesztési ötletek

- 📊 Stream státusz megjelenítése a web felületen
- 🔊 Hangerő vezérlés (amixer) a web felületről
- 📈 Statisztikák: mikor fut, mennyi ideig
- 🔔 Email vagy webhook értesítés indításkor/leállításkor
- 🎵 Több stream profil kezelése
- 📅 Egyedi dátumok támogatása (ünnepnapok, különleges műsorok)

## Támogatás

Ha problémád van:

1. Futtasd a diagnosztikát: `bash diagnose.sh`
2. Ellenőrizd a logokat: `sudo journalctl -u radio-scheduler -n 100`
3. Nézd meg az AzuraCast szolgáltatás státuszát
4. Teszteld a web felületet: `bash test.sh`

---

**Tipp**: Az első beállítás után érdemes néhány órát várni és ellenőrizni a logokat, hogy minden rendben működik-e!
