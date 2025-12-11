# ⚡ GYORS INDÍTÁS A SZERVEREN

## 📌 Cél

Az `azuracast-playout.service` automatikus indítása és leállítása órarend szerint.

## 1️⃣ Fájlok feltöltése

Töltsd fel ezt a teljes mappát a szerverre:

```bash
# SCP-vel (Windows → Linux)
scp -r radio_scheduler root@szerver-ip:/root/

# VAGY WinSCP / FileZilla GUI-val
```

## 2️⃣ Csatlakozás a szerverhez

```bash
ssh root@szerver-ip
cd /root/radio_scheduler
```

## 3️⃣ Jogosultságok beállítása

```bash
bash setup-permissions.sh
```

## 4️⃣ Telepítés

### Automatikus (egyszerű):
```bash
sudo bash install.sh
```

### VAGY Manuális (teszteléshez):
```bash
pip3 install -r requirements.txt
sudo python3 app.py
```

## 4️⃣B Tűzfal beállítás (FONTOS!)

Ha böngészőből nem érhető el, de SSH-n curl működik:

```bash
# Automatikus tűzfal konfiguráció
sudo bash open-firewall.sh

# VAGY manuálisan UFW esetén:
sudo ufw allow 86/tcp

# VAGY firewalld esetén:
sudo firewall-cmd --add-port=86/tcp --permanent
sudo firewall-cmd --reload
```

## 5️⃣ Tesztelés

```bash
# Helyi teszt a szerveren
curl http://localhost:86

# Böngészőben (a saját gépedről)
http://szerver-ip:86
```

## ❌ Probléma?

### SSH-n működik (curl OK), de böngészőből NEM?
**Ez tűzfal probléma!**

```bash
# Automatikus javítás
sudo bash open-firewall.sh

# VAGY manuálisan
sudo ufw allow 86/tcp
# vagy
sudo firewall-cmd --add-port=86/tcp --permanent && sudo firewall-cmd --reload
```

### Egyéb problémák:

```bash
# Teljes diagnosztika
bash diagnose.sh

# Logok
sudo journalctl -u radio-scheduler -f

# Port ellenőrzés
sudo netstat -tulpn | grep :86
```

## 📚 Teljes dokumentáció

- [README.md](README.md) - Teljes dokumentáció
- [AZURACAST_SETUP.md](AZURACAST_SETUP.md) - AzuraCast specifikus útmutató
- [SZERVER_TELEPITES.md](SZERVER_TELEPITES.md) - Részletes szerver telepítési útmutató

---

**SEGÍTSÉG**: Ha a port 86 nem működik, próbáld meg a 5000-es portot:
```bash
export PORT=5000
sudo python3 app.py
# Majd: curl http://localhost:5000
```
