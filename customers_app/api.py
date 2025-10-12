
# api.py - Separate REST API for accountants (does NOT change site visuals)
from flask import Flask, request, jsonify
import sqlite3, os, datetime, json

BASE_DIR = os.path.dirname(__file__)
API_DB = os.path.join(BASE_DIR, "loyalty_api.db")
LEGACY_DB = os.path.join(BASE_DIR, "loyalty.db")  # original DB

def normalize_digits(s):
    if s is None: 
        return s
    # Arabic-Indic: ٠١٢٣٤٥٦٧٨٩  | Persian-Indic: ۰۱۲۳۴۵۶۷۸۹
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return str(s).translate(trans)

app = Flask(__name__)

def get_conn(db_path=API_DB):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_api_db():
    conn = get_conn()
    cur = conn.cursor()
    # clients table: one row per phone (user)
    cur.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        created_at TEXT
    )""")
    # cars table: multiple cars per client
    cur.execute("""CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        plate_letters TEXT,
        plate_numbers TEXT,
        washes INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        last_rating INTEGER,
        rating_history TEXT,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER,
        created_at TEXT,
        message TEXT,
        seen INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def migrate_from_legacy():
    # Copy existing clients from legacy DB into API DB without deleting legacy
    if not os.path.exists(LEGACY_DB):
        return
    src = sqlite3.connect(LEGACY_DB)
    src.row_factory = sqlite3.Row
    s = src.cursor()
    try:
        s.execute("SELECT * FROM clients")
        rows = s.fetchall()
    except Exception:
        rows = []
    src.close()
    conn = get_conn(); cur = conn.cursor()
    for r in rows:
        phone = r['phone']
        # find or create client by phone
        cur.execute("SELECT id FROM clients WHERE phone=?", (phone,))
        c = cur.fetchone()
        if c:
            client_id = c['id']
        else:
            cur.execute("INSERT INTO clients (name, phone, created_at) VALUES (?,?,?)", (r['name'], phone, r.get('created_at') or datetime.datetime.utcnow().isoformat()))
            client_id = cur.lastrowid
        # create car entry
        try:
            cur.execute("INSERT INTO cars (client_id, plate_letters, plate_numbers, washes, points, last_rating, notes) VALUES (?,?,?,?,?,?,?)",
                        (client_id, r['plate_letters'], r['plate_numbers'], r.get('washes') or 0, r.get('points') or 0, r.get('last_rating'), r.get('notes')))
        except Exception:
            pass
    conn.commit(); conn.close()

@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.get_json() or {}
    phone = normalize_digits(data.get('phone'))
    plate_letters = (data.get('plate_letters') or '').strip().upper()
    plate_numbers = (data.get('plate_numbers') or '').strip()
    rating = data.get('rating')
    if not all([phone, plate_letters, plate_numbers]):
        return jsonify(success=False, message='missing'), 400
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE phone=?", (phone,))
    c = cur.fetchone()
    if not c:
        cur.execute("INSERT INTO clients (name, phone, created_at) VALUES (?,?,?)", ('', phone, datetime.datetime.utcnow().isoformat()))
        client_id = cur.lastrowid
    else:
        client_id = c['id']
    cur.execute("SELECT * FROM cars WHERE client_id=? AND plate_letters=? AND plate_numbers=?", (client_id, plate_letters, plate_numbers))
    car = cur.fetchone()
    if not car:
        cur.execute("INSERT INTO cars (client_id, plate_letters, plate_numbers, washes, points, last_rating, rating_history, notes) VALUES (?,?,?,?,?,?,?,?)",
                    (client_id, plate_letters, plate_numbers, 0, 0, None, '[]', ''))
        car_id = cur.lastrowid
        washes = 0
        points = 0
    else:
        car_id = car['id']
        washes = car['washes']
        points = car['points']
    if rating is not None:
        cur.execute("SELECT rating_history FROM cars WHERE id=?", (car_id,))
        rh = cur.fetchone()['rating_history'] or '[]'
        try:
            arr = json.loads(rh)
        except:
            arr = []
        arr.append({'at': datetime.datetime.utcnow().isoformat(), 'rating': int(rating)})
        arr = arr[-20:]
        cur.execute("UPDATE cars SET last_rating=?, rating_history=? WHERE id=?", (int(rating), json.dumps(arr, ensure_ascii=False), car_id))
        if len(arr) >= 4:
            last_ratings = [r['rating'] for r in arr[-4:]]
            if last_ratings[-1] < 5 and all(x==5 for x in last_ratings[:-1]):
                cur.execute("INSERT INTO alerts (car_id, created_at, message, seen) VALUES (?,?,?,0)", (car_id, datetime.datetime.utcnow().isoformat(), 'انخفاض مفاجئ في التقييم'))
    conn.commit()
    points_needed = max(0, 60 - points)
    conn.close()
    return jsonify(success=True, client_id=client_id, car_id=car_id, washes=washes, points=points, points_needed=points_needed)

@app.route('/api/confirm_wash', methods=['POST'])
def api_confirm_wash():
    data = request.get_json() or {}
    car_id = data.get('car_id')
    if not car_id:
        return jsonify(success=False, message='missing car_id'), 400
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM cars WHERE id=?", (car_id,))
    car = cur.fetchone()
    if not car:
        conn.close(); return jsonify(success=False, message='car not found'), 404
    washes = (car['washes'] or 0) + 1
    points = (car['points'] or 0) + 10
    cur.execute("UPDATE cars SET washes=?, points=? WHERE id=?", (washes, points, car_id))
    conn.commit()
    free_next = (points >= 60)
    conn.close()
    return jsonify(success=True, washes=washes, points=points, free_next=free_next)

@app.route('/api/alerts', methods=['GET'])
def api_get_alerts():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT a.id,a.car_id,a.created_at,a.message,a.seen,c.plate_letters,c.plate_numbers,cl.phone FROM alerts a JOIN cars c ON a.car_id=c.id JOIN clients cl ON c.client_id=cl.id ORDER BY a.created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(success=True, alerts=rows)

if __name__ == '__main__':
    init_api_db()
    migrate_from_legacy()
    app.run(host='0.0.0.0', port=6000, debug=True)
