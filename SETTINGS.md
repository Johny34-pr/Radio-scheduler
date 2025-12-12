# Beállítások használata

## Új funkciók

A Radio Scheduler mostantól támogatja:

1. **Stream URL konfigurálás** - Saját rádió URL beállítása
2. **AzuraCast integráció** - Az AzuraCast backend automatikus szüneteltetése/folytatása
3. **Egyedi beállítások** - Minden konfiguráció egy helyen, webes felületen

## Stream URL beállítása

A **Beállítások** panelben megadhatod a stream URL-t, amit az mpv játszik le:

```
Stream URL: http://10.204.131.131:8000/radio.mp3
```

Amikor megváltoztatod és elmented, az alábbiak történnek:
1. A systemd service environment változója frissül
2. Ha a szolgáltatás épp fut, automatikusan újraindul az új URL-lel
3. A systemd override fájl létrejön: `/etc/systemd/system/azuracast-playout.service.d/override.conf`

## AzuraCast integráció

### Alapbeállítás

Ha szeretnéd, hogy amikor az mpv leáll/indul, az AzuraCast backend (Liquidsoap) is leálljon/induljon:

1. Állítsd be az **AzuraCast API URL-t**: `http://10.204.131.131`
2. Állítsd be a **Station ID-t**: `1` (általában ez az első állomás)
3. Generálj egy **API kulcsot** az AzuraCast admin felületén:
   - Bejelentkezés után: **Administration** → **API Keys** → **Generate New Key**
   - Szükséges jogosultság: `Manage Station Broadcasting`
4. Másold be az **API Key-t** a beállításokba
5. Pipáld be az **"AzuraCast szüneteltetése/folytatása"** opciót

### Hogyan működik?

Amikor az órarend szerint vagy manuálisan:

**Szolgáltatás indítása:**
1. AzuraCast backend elindítása (POST `/api/station/{id}/restart`)
2. Systemd service environment frissítése
3. mpv elindítása a megadott stream URL-lel

**Szolgáltatás leállítása:**
1. mpv leállítása (fade-out a scriptekkel)
2. AzuraCast backend leállítása (POST `/api/station/{id}/backend/stop`)

### Előnyök

- **Erőforrás megtakarítás**: Amikor nem kell streaming, az AzuraCast Liquidsoap sem fut
- **Tiszta logika**: Minden központból vezérelhető
- **Automatizmus**: Az órarend szerint minden önműködően történik

## API Kulcs generálása AzuraCast-ban

1. Lépj be az AzuraCast admin felületre
2. Menj az **Administration** → **API Keys** menüpontba
3. Kattints a **"Generate New Key"** gombra
4. Add meg az alábbi beállításokat:
   - **Comment**: `Radio Scheduler`
   - **Permissions**: Pipáld be a `Manage Station Broadcasting` opciót
5. Kattints **"Save Changes"**
6. Másold ki a generált API kulcsot
7. Illeszd be a Radio Scheduler beállításaiba

## Hibaelhárítás

### Az URL nem frissül

Ha megváltoztattad az URL-t, de úgy tűnik nem vált:

```bash
# Ellenőrizd az override fájlt
sudo cat /etc/systemd/system/azuracast-playout.service.d/override.conf

# Manuális frissítés
sudo systemctl daemon-reload
sudo systemctl restart azuracast-playout
```

### AzuraCast API hibák

Ha az AzuraCast szüneteltetés nem működik:

```bash
# Nézd meg a service logot
sudo journalctl -u radio-scheduler -n 50

# Teszteld az API-t manuálisan
curl -X POST http://10.204.131.131/api/station/1/restart \
  -H "X-API-Key: YOUR_API_KEY_HERE"
```

### Nem szükséges AzuraCast vezérlés

Ha csak az URL-t akarod állítani, de nem akarod az AzuraCast-ot leállítani:

1. Hagyd **kikapcsolva** az "AzuraCast szüneteltetése/folytatása" jelölőnégyzetet
2. Csak a Stream URL-t állítsd be
3. Az API URL és API Key mezők üresek maradhatnak

## Példa konfiguráció

### Csak stream URL beállítás (AzuraCast vezérlés nélkül)

```
Stream URL: http://10.204.131.131:8000/radio.mp3
AzuraCast API URL: (üresen hagyva)
Station ID: (üresen hagyva)
API Key: (üresen hagyva)
☐ AzuraCast szüneteltetése/folytatása
```

### Teljes AzuraCast integráció

```
Stream URL: http://10.204.131.131:8000/radio.mp3
AzuraCast API URL: http://10.204.131.131
Station ID: 1
API Key: 1234567890abcdef...
☑ AzuraCast szüneteltetése/folytatása
```

### Külső rádió stream lejátszása

```
Stream URL: http://streams.radio.hu/external-stream.mp3
AzuraCast API URL: (üresen hagyva)
Station ID: (üresen hagyva)
API Key: (üresen hagyva)
☐ AzuraCast szüneteltetése/folytatása
```

## Biztonsági megjegyzések

- Az API kulcs **érzékeny adat**, ne oszd meg senkivel
- Az adatbázisban egyszerű szövegként tárolódik (`scheduler.db`)
- Javasolt: file permissions beállítása
  ```bash
  sudo chmod 600 /opt/radio_scheduler/scheduler.db
  ```
