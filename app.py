from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, time
import sqlite3
import subprocess
import threading
import schedule
import time as time_module
import os
import sys
import requests
import glob

app = Flask(__name__)
CORS(app)

# Konfigurálható systemd szolgáltatás neve és port
SYSTEMD_SERVICE = os.getenv('RADIO_SERVICE', 'azuracast-playout.service')
PORT = int(os.getenv('PORT', '86'))
DB_PATH = os.getenv('DB_PATH', 'scheduler.db')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Hangfájlok könyvtára
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_files')
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    """Adatbázis inicializálása"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Új tábla struktúra - napcsoport alapú
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day_start INTEGER NOT NULL,
            day_end INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            stop_time TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Beállítások tábla (stream URL, AzuraCast API stb.)
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    # Rádió állomások tábla
    c.execute('''
        CREATE TABLE IF NOT EXISTS radios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stream_url TEXT NOT NULL,
            is_azuracast INTEGER DEFAULT 0,
            azuracast_station_id TEXT DEFAULT '',
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Alapértelmezett beállítások
    default_settings = {
        'azuracast_api_url': 'http://127.0.0.1',
        'azuracast_api_key': '',
        'control_azuracast': '0'  # 0 = csak mpv, 1 = mpv + AzuraCast szüneteltetés/folytatás
    }
    
    for key, value in default_settings.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    # Alapértelmezett rádió állomások (ha üres a tábla)
    existing_radios = c.execute('SELECT COUNT(*) FROM radios').fetchone()[0]
    if existing_radios == 0:
        default_radios = [
            ('Helyi AzuraCast', 'http://127.0.0.1:8000/radio.mp3', 1, '1', 1),
            ('Retro Rádió', 'https://icast.connectmedia.hu/4738/live.mp3', 0, '', 0),
            ('Rádió1', 'http://icast.connectmedia.hu/5201/live.mp3', 0, '', 0),
            ('Christmas FM', 'https://stream1.christmasfm.hu/live.mp3', 0, '', 0),
            ('Christmas Classics', 'http://listen.livestreamingservice.com/181-xmix_128k.mp3', 0, '', 0),
        ]
        for name, url, is_azura, station_id, is_active in default_radios:
            c.execute('INSERT INTO radios (name, stream_url, is_azuracast, azuracast_station_id, is_active) VALUES (?, ?, ?, ?, ?)',
                      (name, url, is_azura, station_id, is_active))
    
    # Régi tábla migrálása, ha létezik
    try:
        c.execute("SELECT day_of_week FROM schedules LIMIT 1")
        # Ha van day_of_week oszlop, migráljuk
        old_schedules = c.execute("SELECT * FROM schedules").fetchall()
        if old_schedules:
            # Töröljük a régi táblát
            c.execute("DROP TABLE schedules")
            # Újra létrehozzuk az új struktúrával
            c.execute('''
                CREATE TABLE schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    day_start INTEGER NOT NULL,
                    day_end INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    stop_time TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Visszamásoljuk a régi adatokat (day_of_week -> day_start és day_end ugyanaz)
            for old in old_schedules:
                day = old[1]  # day_of_week
                start_t = old[2]
                stop_t = old[3]
                enabled = old[4]
                days_hu = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']
                name = f"{days_hu[day]} {start_t}-{stop_t}"
                c.execute('''
                    INSERT INTO schedules (name, day_start, day_end, start_time, stop_time, enabled)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, day, day, start_t, stop_t, enabled))
    except sqlite3.OperationalError:
        # Már új formátum
        pass
    
    conn.commit()
    conn.close()

def get_db():
    """Adatbázis kapcsolat létrehozása"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_setting(key, default=''):
    """Beállítás lekérdezése"""
    conn = get_db()
    result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return result['value'] if result else default

def set_setting(key, value):
    """Beállítás mentése"""
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_active_radio():
    """Aktív rádió lekérdezése"""
    conn = get_db()
    radio = conn.execute('SELECT * FROM radios WHERE is_active = 1').fetchone()
    conn.close()
    return dict(radio) if radio else None

def with_privileges(cmd):
    """Parancs futtatása rootként vagy sudo-val"""
    if os.geteuid() == 0:
        return cmd
    return ['sudo'] + cmd

def systemd_unit_exists(service_name):
    """Létezik-e a systemd unit"""
    try:
        result = subprocess.run(
            with_privileges(['systemctl', 'cat', service_name]),
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def azuracast_api_control(action, station_id):
    """AzuraCast vezérlés API-n keresztül (fallback)"""
    api_url = get_setting('azuracast_api_url', '').rstrip('/')
    api_key = get_setting('azuracast_api_key', '')
    if not api_url or not api_key:
        return False

    headers = {'X-API-Key': api_key}

    if action == 'start':
        urls = [
            f"{api_url}/api/station/{station_id}/restart",
            f"{api_url}/api/station/{station_id}/backend/start",
            f"{api_url}/api/station/{station_id}/frontend/start",
        ]
    else:
        urls = [
            f"{api_url}/api/station/{station_id}/frontend/stop",
            f"{api_url}/api/station/{station_id}/backend/stop",
        ]

    any_success = False
    last_error = None
    for url in urls:
        try:
            response = requests.post(url, headers=headers, timeout=15)
            if 200 <= response.status_code < 300:
                any_success = True
        except Exception as e:
            last_error = e

    if any_success:
        return True

    if last_error is not None:
        print(f"[{datetime.now()}] AzuraCast API control error: {type(last_error).__name__}: {last_error}")
    return False

def azuracast_control(action):
    """AzuraCast backend és frontend vezérlése supervisorctl-lel"""
    control_enabled = get_setting('control_azuracast', '0') == '1'
    
    print(f"[{datetime.now()}] AzuraCast control called: action={action}, enabled={control_enabled}")
    
    if not control_enabled:
        print(f"[{datetime.now()}] AzuraCast control disabled, skipping")
        return True
    
    # Aktív rádió lekérdezése
    active_radio = get_active_radio()
    if not active_radio or not active_radio.get('is_azuracast'):
        print(f"[{datetime.now()}] Active radio is not AzuraCast, skipping")
        return True
    
    station_id = active_radio.get('azuracast_station_id', '1')
    
    try:
        def run_supervisor(supervisor_action, target):
            result = subprocess.run(
                with_privileges(['docker', 'exec', 'azuracast', 'supervisorctl', supervisor_action, target]),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                print(f"[{datetime.now()}] Supervisor command failed: action={supervisor_action}, target={target}, rc={result.returncode}, stderr={result.stderr.strip()}")
                return False
            return True

        if action == 'start':
            # Backend indítása
            backend_ok = run_supervisor('start', f'station_{station_id}:station_{station_id}_backend')
            print(f"[{datetime.now()}] Backend started")
            
            time_module.sleep(2)
            
            # Frontend indítása
            frontend_ok = run_supervisor('start', f'station_{station_id}:station_{station_id}_frontend')
            print(f"[{datetime.now()}] Frontend started")
            
            if backend_ok and frontend_ok:
                print(f"[{datetime.now()}] ✅ AzuraCast station started")
                return True

            # Fallback API vezérlésre
            api_ok = azuracast_api_control('start', station_id)
            print(f"[{datetime.now()}] AzuraCast start fallback API result: {api_ok}")
            return api_ok
        
        elif action == 'stop':
            # Frontend leállítása
            frontend_ok = run_supervisor('stop', f'station_{station_id}:station_{station_id}_frontend')
            print(f"[{datetime.now()}] Frontend stopped")
            
            # Backend leállítása
            backend_ok = run_supervisor('stop', f'station_{station_id}:station_{station_id}_backend')
            print(f"[{datetime.now()}] Backend stopped")
            
            if frontend_ok and backend_ok:
                print(f"[{datetime.now()}] ✅ AzuraCast station stopped")
                return True

            # Fallback API vezérlésre
            api_ok = azuracast_api_control('stop', station_id)
            print(f"[{datetime.now()}] AzuraCast stop fallback API result: {api_ok}")
            return api_ok
    
    except Exception as e:
        print(f"[{datetime.now()}] ❌ AzuraCast control error: {type(e).__name__}: {e}")
        return False
    
    return True

def systemd_start():
    """Systemd szolgáltatás indítása"""
    try:
        # AzuraCast backend indítása (ha engedélyezve)
        azura_ok = azuracast_control('start')

        if not systemd_unit_exists(SYSTEMD_SERVICE):
            print(f"[{datetime.now()}] Systemd unit not found ({SYSTEMD_SERVICE}), AzuraCast-only start mode")
            return azura_ok
        
        # Service environment frissítése az aktuális stream URL-lel
        update_service_environment()
        
        result = subprocess.run(
            with_privileges(['systemctl', 'start', SYSTEMD_SERVICE]),
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[{datetime.now()}] Service started: {SYSTEMD_SERVICE}")
        return azura_ok
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error starting service: {e.stderr}")
        return False
    except (FileNotFoundError, AttributeError):
        print(f"[{datetime.now()}] systemctl not found (Windows?), simulating start")
        return True

def systemd_stop():
    """Systemd szolgáltatás leállítása"""
    try:
        if systemd_unit_exists(SYSTEMD_SERVICE):
            result = subprocess.run(
                with_privileges(['systemctl', 'stop', SYSTEMD_SERVICE]),
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[{datetime.now()}] Service stopped: {SYSTEMD_SERVICE}")
        else:
            print(f"[{datetime.now()}] Systemd unit not found ({SYSTEMD_SERVICE}), AzuraCast-only stop mode")
        
        # AzuraCast backend leállítása (ha engedélyezve)
        azura_ok = azuracast_control('stop')
        
        return azura_ok
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error stopping service: {e.stderr}")
        return False
    except (FileNotFoundError, AttributeError):
        print(f"[{datetime.now()}] systemctl not found (Windows?), simulating stop")
        return True

def update_service_environment():
    """Service environment változók frissítése az aktív rádió alapján"""
    try:
        active_radio = get_active_radio()
        if not active_radio:
            print(f"[{datetime.now()}] No active radio found")
            return
        
        stream_url = active_radio['stream_url']
        service_file = f'/etc/systemd/system/{SYSTEMD_SERVICE}'
        
        # Ellenőrizzük, hogy a service file létezik-e
        result = subprocess.run(with_privileges(['test', '-f', service_file]), capture_output=True)
        if result.returncode != 0:
            print(f"[{datetime.now()}] Service file not found, skipping environment update")
            return
        
        # Systemd environment override directory
        override_dir = f'/etc/systemd/system/{SYSTEMD_SERVICE}.d'
        override_file = f'{override_dir}/override.conf'
        
        # Override konfig létrehozása
        override_content = f"""[Service]
Environment="STREAM_URL={stream_url}"
"""
        
        # Könyvtár létrehozása és fájl írása
        if os.geteuid() == 0:
            os.makedirs(override_dir, exist_ok=True)
            with open(override_file, 'w', encoding='utf-8') as f:
                f.write(override_content)
            subprocess.run(['systemctl', 'daemon-reload'], check=True, capture_output=True, text=True)
        else:
            mkdir_cmd = with_privileges(['mkdir', '-p', override_dir])
            subprocess.run(mkdir_cmd, check=True, capture_output=True, text=True)

            write_cmd = f'echo "{override_content}" | tee {override_file} > /dev/null'
            subprocess.run(with_privileges(['bash', '-lc', write_cmd]), shell=False, check=True, capture_output=True, text=True)
            subprocess.run(with_privileges(['systemctl', 'daemon-reload']), check=True, capture_output=True, text=True)

        print(f"[{datetime.now()}] Service environment updated: STREAM_URL={stream_url}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error updating service environment: {e}")

def azuracast_station_status():
    """AzuraCast station állapot lekérdezése supervisorctl-ből"""
    try:
        control_enabled = get_setting('control_azuracast', '0') == '1'
        active_radio = get_active_radio()

        if not control_enabled or not active_radio or not active_radio.get('is_azuracast'):
            return 'unknown'

        station_id = active_radio.get('azuracast_station_id', '1') or '1'
        result = subprocess.run(
            with_privileges([
                'docker', 'exec', 'azuracast', 'supervisorctl', 'status',
                f'station_{station_id}:station_{station_id}_backend',
                f'station_{station_id}:station_{station_id}_frontend'
            ]),
            capture_output=True,
            text=True,
            timeout=20
        )

        # supervisorctl gyakran non-zero kóddal tér vissza STOPPED állapot esetén,
        # ezért a státuszt mindig a szöveges kimenetből olvassuk ki.
        output = f"{result.stdout or ''}\n{result.stderr or ''}".upper()
        has_running = 'RUNNING' in output
        has_stopped_like = any(x in output for x in ['STOPPED', 'EXITED', 'FATAL', 'BACKOFF'])
        has_transitional = any(x in output for x in ['STARTING', 'STOPPING'])

        if 'NO SUCH PROCESS' in output or 'ERROR' in output:
            return 'unknown'

        if has_running:
            return 'active'
        if has_transitional:
            return 'active'
        if has_stopped_like:
            return 'inactive'
        return 'unknown'
    except Exception:
        return 'unknown'

def systemd_status():
    """Systemd szolgáltatás állapotának lekérdezése"""
    try:
        azura_state = azuracast_station_status()

        # Ha AzuraCast station állapot biztosan ismert, azt tekintjük forrásigazságnak.
        if azura_state in ['active', 'inactive']:
            return azura_state

        if not systemd_unit_exists(SYSTEMD_SERVICE):
            return azura_state
            
        result = subprocess.run(
            with_privileges(['systemctl', 'is-active', SYSTEMD_SERVICE]),
            capture_output=True,
            text=True
        )
        status = result.stdout.strip()
        # A systemctl is-active visszaadhat: active, inactive, failed, unknown, stb.
        # Normalizáljuk az értékeket
        if status in ['active', 'activating', 'reloading']:
            return 'active'
        elif status in ['inactive', 'deactivating', 'failed']:
            return 'inactive'
        else:
            return azura_state
    except (FileNotFoundError, AttributeError):
        return azuracast_station_status()

# API endpointok
@app.route('/')
def index():
    """Főoldal"""
    return render_template('index.html')

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Összes órarend lekérdezése"""
    conn = get_db()
    schedules = conn.execute('SELECT * FROM schedules ORDER BY day_start, start_time').fetchall()
    conn.close()
    
    return jsonify([dict(s) for s in schedules])

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Új órarend létrehozása"""
    data = request.json
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO schedules (name, day_start, day_end, start_time, stop_time, enabled)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['name'], data['day_start'], data['day_end'], data['start_time'], data['stop_time'], data.get('enabled', 1)))
    conn.commit()
    schedule_id = c.lastrowid
    conn.close()
    
    reload_scheduler()
    return jsonify({'id': schedule_id, 'message': 'Schedule created'}), 201

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Órarend módosítása"""
    data = request.json
    
    conn = get_db()
    conn.execute('''
        UPDATE schedules
        SET name = ?, day_start = ?, day_end = ?, start_time = ?, stop_time = ?, enabled = ?
        WHERE id = ?
    ''', (data['name'], data['day_start'], data['day_end'], data['start_time'], data['stop_time'], data.get('enabled', 1), schedule_id))
    conn.commit()
    conn.close()
    
    reload_scheduler()
    return jsonify({'message': 'Schedule updated'})

@app.route('/api/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Egy órarend lekérdezése"""
    conn = get_db()
    schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
    conn.close()
    
    if schedule is None:
        return jsonify({'error': 'Schedule not found'}), 404
    
    return jsonify(dict(schedule))

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Órarend törlése"""
    conn = get_db()
    conn.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()
    
    reload_scheduler()
    return jsonify({'message': 'Schedule deleted'})

@app.route('/api/service/status', methods=['GET'])
def service_status():
    """Szolgáltatás állapotának lekérdezése"""
    status = systemd_status()
    active_radio = get_active_radio()
    return jsonify({
        'service': SYSTEMD_SERVICE, 
        'status': status,
        'active_radio': active_radio
    })

@app.route('/api/service/start', methods=['POST'])
def service_start():
    """Szolgáltatás manuális indítása"""
    success = systemd_start()
    return jsonify({'success': success, 'status': systemd_status()})

@app.route('/api/service/stop', methods=['POST'])
def service_stop():
    """Szolgáltatás manuális leállítása"""
    success = systemd_stop()
    return jsonify({'success': success, 'status': systemd_status()})

# Rádió állomások API
@app.route('/api/radios', methods=['GET'])
def get_radios():
    """Összes rádió állomás lekérdezése"""
    conn = get_db()
    radios = conn.execute('SELECT * FROM radios ORDER BY is_active DESC, name').fetchall()
    conn.close()
    return jsonify([dict(r) for r in radios])

@app.route('/api/radios', methods=['POST'])
def create_radio():
    """Új rádió hozzáadása"""
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO radios (name, stream_url, is_azuracast, azuracast_station_id, is_active)
        VALUES (?, ?, ?, ?, 0)
    ''', (data['name'], data['stream_url'], data.get('is_azuracast', 0), data.get('azuracast_station_id', '')))
    conn.commit()
    radio_id = c.lastrowid
    conn.close()
    return jsonify({'id': radio_id, 'message': 'Radio created'}), 201

@app.route('/api/radios/<int:radio_id>', methods=['PUT'])
def update_radio(radio_id):
    """Rádió módosítása"""
    data = request.json
    conn = get_db()
    conn.execute('''
        UPDATE radios SET name = ?, stream_url = ?, is_azuracast = ?, azuracast_station_id = ?
        WHERE id = ?
    ''', (data['name'], data['stream_url'], data.get('is_azuracast', 0), data.get('azuracast_station_id', ''), radio_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Radio updated'})

@app.route('/api/radios/<int:radio_id>', methods=['DELETE'])
def delete_radio(radio_id):
    """Rádió törlése"""
    conn = get_db()
    # Ne engedjük törölni az aktív rádiót
    radio = conn.execute('SELECT is_active FROM radios WHERE id = ?', (radio_id,)).fetchone()
    if radio and radio['is_active']:
        conn.close()
        return jsonify({'error': 'Aktív rádió nem törölhető'}), 400
    
    conn.execute('DELETE FROM radios WHERE id = ?', (radio_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Radio deleted'})

@app.route('/api/radios/<int:radio_id>/activate', methods=['POST'])
def activate_radio(radio_id):
    """Rádió aktiválása (a többi deaktiválása)"""
    conn = get_db()
    
    # Régi aktív rádió lekérdezése (AzuraCast leállításhoz)
    old_active = conn.execute('SELECT * FROM radios WHERE is_active = 1').fetchone()
    old_was_azuracast = old_active and old_active['is_azuracast']
    
    # Új rádió lekérdezése
    new_radio = conn.execute('SELECT * FROM radios WHERE id = ?', (radio_id,)).fetchone()
    new_is_azuracast = new_radio and new_radio['is_azuracast']
    
    # Minden rádió deaktiválása
    conn.execute('UPDATE radios SET is_active = 0')
    # Kiválasztott aktiválása
    conn.execute('UPDATE radios SET is_active = 1 WHERE id = ?', (radio_id,))
    conn.commit()
    conn.close()
    
    service_was_running = systemd_status() == 'active'
    
    # Ha a szolgáltatás futott, leállítjuk (és ha AzuraCast volt, azt is)
    if service_was_running:
        systemd_stop()  # Ez leállítja az AzuraCast-ot is, ha az volt aktív
        time_module.sleep(1)
    
    # Ha régi AzuraCast volt, de az új nem az, akkor biztosan leállítjuk
    if old_was_azuracast and not new_is_azuracast:
        control_enabled = get_setting('control_azuracast', '0') == '1'
        if control_enabled and old_active:
            station_id = old_active['azuracast_station_id'] or '1'
            try:
                subprocess.run(['sudo', 'docker', 'exec', 'azuracast', 'supervisorctl', 'stop', 
                    f'station_{station_id}:station_{station_id}_frontend'], 
                    capture_output=True, text=True, timeout=30)
                subprocess.run(['sudo', 'docker', 'exec', 'azuracast', 'supervisorctl', 'stop', 
                    f'station_{station_id}:station_{station_id}_backend'], 
                    capture_output=True, text=True, timeout=30)
                print(f"[{datetime.now()}] Old AzuraCast station stopped")
            except Exception as e:
                print(f"[{datetime.now()}] Error stopping old AzuraCast: {e}")
    
    # Ha a szolgáltatás futott, újraindítjuk az új stream URL-lel
    if service_was_running:
        systemd_start()
    
    return jsonify({'message': 'Radio activated'})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Összes beállítás lekérdezése"""
    conn = get_db()
    settings = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    return jsonify({s['key']: s['value'] for s in settings})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Beállítások frissítése"""
    data = request.json
    
    for key, value in data.items():
        set_setting(key, str(value))
    
    return jsonify({'message': 'Settings updated'})

@app.route('/api/azuracast/test', methods=['POST'])
def test_azuracast():
    """AzuraCast API tesztelése"""
    control_enabled = get_setting('control_azuracast', '0') == '1'
    
    if not control_enabled:
        return jsonify({'success': False, 'message': 'AzuraCast vezérlés nincs engedélyezve'}), 400
    
    api_url = get_setting('azuracast_api_url')
    api_key = get_setting('azuracast_api_key')
    
    # Aktív rádió station_id-ja
    active_radio = get_active_radio()
    station_id = active_radio.get('azuracast_station_id', '1') if active_radio else '1'
    
    if not api_url or not api_key:
        return jsonify({'success': False, 'message': 'Hiányoznak az API beállítások'}), 400
    
    try:
        # Station status lekérdezése
        headers = {'X-API-Key': api_key}
        url = f"{api_url}/api/station/{station_id}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return jsonify({
            'success': True,
            'message': 'API kapcsolat sikeres',
            'station_name': data.get('name', 'N/A'),
            'backend_running': data.get('backend_running', False),
            'is_public': data.get('is_public', False)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'API hiba: {type(e).__name__}: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Váratlan hiba: {type(e).__name__}: {str(e)}'
        }), 500

# Hangfájl API endpointok
@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    """Hangfájl feltöltése"""
    if 'file' not in request.files:
        return jsonify({'error': 'Nincs fájl a kérésben'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nincs kiválasztva fájl'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Egyedi név ha már létezik
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            filename = f"{base}_{counter}{ext}"
            counter += 1
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Fájl méret
        size = os.path.getsize(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'size': size,
            'message': 'Fájl sikeresen feltöltve'
        }), 201
    
    return jsonify({'error': 'Nem támogatott fájltípus'}), 400

@app.route('/api/audio/files', methods=['GET'])
def list_audio_files():
    """Feltöltött hangfájlok listázása"""
    files = []
    for ext in ALLOWED_EXTENSIONS:
        files.extend(glob.glob(os.path.join(UPLOAD_FOLDER, f'*.{ext}')))
    
    result = []
    for filepath in files:
        filename = os.path.basename(filepath)
        stat = os.stat(filepath)
        result.append({
            'filename': filename,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    # Rendezés név szerint
    result.sort(key=lambda x: x['filename'].lower())
    return jsonify(result)

@app.route('/api/audio/files/<filename>', methods=['DELETE'])
def delete_audio_file(filename):
    """Hangfájl törlése"""
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'message': 'Fájl törölve'})
    return jsonify({'error': 'Fájl nem található'}), 404

@app.route('/api/audio/play/<filename>', methods=['POST'])
def play_audio_file(filename):
    """Hangfájl lejátszása (megszakítja a rádiót)"""
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({'error': 'Fájl nem található'}), 404
    
    try:
        # Rádió leállítása
        was_playing = systemd_status() == 'active'
        if was_playing:
            systemd_stop()
            time_module.sleep(0.5)
        
        # Hangfájl lejátszása mpv-vel (háttérben, amíg le nem játszódik)
        cmd = ['mpv', '--no-video', '--audio-device=alsa/plughw:0,0', filepath]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"[{datetime.now()}] Playing audio file: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'Lejátszás: {filename}',
            'was_playing_radio': was_playing
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/stop', methods=['POST'])
def stop_audio():
    """Hangfájl lejátszás leállítása"""
    try:
        # Összes mpv process leállítása
        subprocess.run(['pkill', '-9', 'mpv'], capture_output=True)
        return jsonify({'success': True, 'message': 'Lejátszás leállítva'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio_files/<filename>')
def serve_audio(filename):
    """Hangfájl kiszolgálása (előnézethez)"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# Scheduler logika
def setup_scheduler():
    """Időzítő beállítása az adatbázis alapján"""
    schedule.clear()
    
    conn = get_db()
    schedules = conn.execute('SELECT * FROM schedules WHERE enabled = 1').fetchall()
    conn.close()
    
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    days_hu = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap']
    
    for s in schedules:
        day_start = s['day_start']
        day_end = s['day_end']
        start_time = s['start_time']
        stop_time = s['stop_time']
        name = s['name']
        
        # Napok範围 (day_start-tól day_end-ig, beleértve mindkettőt)
        for day_idx in range(day_start, day_end + 1):
            day = days[day_idx]
            
            # Indítás időzítése
            getattr(schedule.every(), day).at(start_time).do(systemd_start)
            # Leállítás időzítése
            getattr(schedule.every(), day).at(stop_time).do(systemd_stop)
        
        day_range = f"{days_hu[day_start]}" if day_start == day_end else f"{days_hu[day_start]}-{days_hu[day_end]}"
        print(f"Scheduled: {name} ({day_range}) - Start: {start_time}, Stop: {stop_time}")


def reload_scheduler():
    """Időzítő újratöltése"""
    setup_scheduler()
    reconcile_schedule_state()

def reconcile_schedule_state():
    """Újraindítás után is érvényesítjük az aktuális órarend állapotot."""
    try:
        now = datetime.now()
        today = now.weekday()  # 0=Hétfő
        now_hm = now.strftime('%H:%M')

        conn = get_db()
        active_now = conn.execute('''
            SELECT 1
            FROM schedules
            WHERE enabled = 1
              AND day_start <= ?
              AND day_end >= ?
              AND start_time <= ?
              AND stop_time > ?
            LIMIT 1
        ''', (today, today, now_hm, now_hm)).fetchone() is not None
        conn.close()

        current_state = systemd_status()
        if active_now and current_state != 'active':
            print(f"[{datetime.now()}] Reconcile: should be active now, starting service")
            systemd_start()
        elif (not active_now) and current_state == 'active':
            print(f"[{datetime.now()}] Reconcile: should be inactive now, stopping service")
            systemd_stop()
    except Exception as e:
        print(f"[{datetime.now()}] Reconcile error: {type(e).__name__}: {e}")

def run_scheduler():
    """Időzítő futtatása külön szálon"""
    while True:
        schedule.run_pending()
        time_module.sleep(30)  # 30 másodpercenként ellenőriz

if __name__ == '__main__':
    init_db()
    setup_scheduler()
    reconcile_schedule_state()
    
    # Scheduler indítása külön szálon
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("=" * 50)
    print(f"Radio Scheduler started")
    print("=" * 50)
    print(f"Managing service: {SYSTEMD_SERVICE}")
    print(f"Web interface: http://localhost:{PORT}")
    print(f"Database: {DB_PATH}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
