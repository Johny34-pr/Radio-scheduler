import os

# Port beállítása környezeti változóból vagy alapértelmezett
PORT = int(os.getenv('PORT', '86'))

# Systemd szolgáltatás neve
SYSTEMD_SERVICE = os.getenv('RADIO_SERVICE', 'azuracast-playout.service')

# Adatbázis elérési út
DB_PATH = os.getenv('DB_PATH', 'scheduler.db')

# Debug mód
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
