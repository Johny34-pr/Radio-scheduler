from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, time
import sqlite3
import subprocess
import threading
import schedule
import time as time_module
import os
import sys

app = Flask(__name__)
CORS(app)

# Konfigurálható systemd szolgáltatás neve és port
SYSTEMD_SERVICE = os.getenv('RADIO_SERVICE', 'azuracast-playout.service')
PORT = int(os.getenv('PORT', '86'))
DB_PATH = os.getenv('DB_PATH', 'scheduler.db')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

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

def systemd_start():
    """Systemd szolgáltatás indítása"""
    try:
        # Sudo használata ha nem root user
        cmd = ['systemctl', 'start', SYSTEMD_SERVICE]
        if os.geteuid() != 0:
            cmd = ['sudo'] + cmd
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[{datetime.now()}] Service started: {SYSTEMD_SERVICE}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error starting service: {e.stderr}")
        return False
    except (FileNotFoundError, AttributeError):
        print(f"[{datetime.now()}] systemctl not found (Windows?), simulating start")
        return True

def systemd_stop():
    """Systemd szolgáltatás leállítása"""
    try:
        # Sudo használata ha nem root user
        cmd = ['systemctl', 'stop', SYSTEMD_SERVICE]
        if os.geteuid() != 0:
            cmd = ['sudo'] + cmd
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[{datetime.now()}] Service stopped: {SYSTEMD_SERVICE}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error stopping service: {e.stderr}")
        return False
    except (FileNotFoundError, AttributeError):
        print(f"[{datetime.now()}] systemctl not found (Windows?), simulating stop")
        return True

def systemd_status():
    """Systemd szolgáltatás állapotának lekérdezése"""
    try:
        # Sudo használata ha nem root user
        cmd = ['systemctl', 'is-active', SYSTEMD_SERVICE]
        if os.geteuid() != 0:
            cmd = ['sudo'] + cmd
            
        result = subprocess.run(
            cmd,
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
            return status
    except (FileNotFoundError, AttributeError):
        return "unknown"

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
    return jsonify({'service': SYSTEMD_SERVICE, 'status': status})

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

def run_scheduler():
    """Időzítő futtatása külön szálon"""
    while True:
        schedule.run_pending()
        time_module.sleep(30)  # 30 másodpercenként ellenőriz

if __name__ == '__main__':
    init_db()
    setup_scheduler()
    
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
