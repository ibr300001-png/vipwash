# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import sqlite3, os, qrcode, io, base64, socket
from datetime import datetime
import json

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "loyalty.db")

API_DB_PATH = os.path.join(BASE_DIR, "loyalty_api.db")

def combo_exists(phone, plate_letters, plate_numbers):
    phone = normalize_digits(phone); plate_numbers = normalize_digits(plate_numbers)
    # Prefer normalized API DB if available (clients+cars)
    try:
        if os.path.exists(API_DB_PATH):
            conn = sqlite3.connect(API_DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
            cur.execute("SELECT c.id FROM clients cl JOIN cars c ON c.client_id=cl.id WHERE cl.phone=? AND c.plate_letters=? AND c.plate_numbers=?",
                        (phone, plate_letters, plate_numbers))
            found = cur.fetchone() is not None
            conn.close()
            return found
    except Exception:
        pass
    # Fallback: legacy single-table check (best-effort)
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT id FROM clients WHERE phone=? AND plate_letters=? AND plate_numbers=?",
                    (phone, plate_letters, plate_numbers))
        ok = cur.fetchone() is not None
        conn.close()
        return ok
    except Exception:
        return False


def normalize_digits(s):
    if s is None: 
        return s
    # Arabic-Indic: ٠١٢٣٤٥٦٧٨٩  | Persian-Indic: ۰۱۲۳۴۵۶۷۸۹
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return str(s).translate(trans)

app = Flask(__name__, template_folder="templates", static_folder="static")


def get_setting(key, default=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row['value'] if row else default
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit(); conn.close()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        car_type TEXT,
        car_model TEXT,
        plate_letters TEXT,
        plate_numbers TEXT,
        washes INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        last_rating INTEGER,
        notes TEXT,
        created_at TEXT
    )""")
    conn.commit(); conn.close()

def make_qr_base64(text):
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64

@app.route('/')
def index():
    footer_text = get_setting('homepage_footer_text', None)
    footer_url = get_setting('homepage_footer_url', None)
    return render_template('index.html', footer_text=footer_text, footer_url=footer_url)

@app.route('/loyal')
def loyal_page():
    return render_template('loyal.html')

@app.route('/new')
def new_page():
    return render_template('new.html')

@app.route('/clients')
def clients_page():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM clients ORDER BY id DESC")
    rows = cur.fetchall(); conn.close()
    return render_template('clients.html', clients=rows)

@app.route('/api/new', methods=['POST'])
def api_new():
    name = (request.form.get('name') or "").strip()
    phone = normalize_digits((request.form.get('phone') or "").strip())
    car_type = (request.form.get('car_type') or "").strip()
    car_model = (request.form.get('car_model') or "").strip()
    plate_letters = (request.form.get('plate_letters') or "").strip().upper()
    plate_numbers = normalize_digits((request.form.get('plate_numbers') or '').strip())
    rating = request.form.get('rating')
    notes = (request.form.get('notes') or "").strip()

    if not all([name, phone, car_type, car_model, plate_letters, plate_numbers, rating]):
        return jsonify(success=False, message='الرجاء تعبئة جميع الحقول والتقييم'), 400

    token = json.dumps({
        "new": True,
        "name": name,
        "phone": phone,
        "car_type": car_type,
        "car_model": car_model,
        "letters": plate_letters,
        "numbers": plate_numbers,
        "rating": rating,
        "notes": notes
    }, ensure_ascii=False)
    qr_b64 = make_qr_base64(f"VIP|{token}")
    return jsonify(success=True, message="وجّه الباركود للمحاسب للإعتماد", qr=qr_b64)
    
@app.route('/api/loyal', methods=['POST'])
def api_loyal():
    phone = normalize_digits((request.form.get('phone') or "").strip())
    plate_letters = (request.form.get('plate_letters') or "").strip().upper()
    plate_numbers = normalize_digits((request.form.get('plate_numbers') or '').strip())
    rating = request.form.get('rating')
    notes = (request.form.get('notes') or "").strip()

    if not all([phone, plate_letters, plate_numbers, rating]):
        return jsonify(success=False, message='الرجاء تعبئة الحقول والتقييم'), 400

    if not combo_exists(phone, plate_letters, plate_numbers):
        return jsonify(success=False, new=True, message='يبدو أنك عميل جديد، انتقل للتسجيل'), 404

    token = json.dumps({
        "loyal": True,
        "phone": phone,
        "letters": plate_letters,
        "numbers": plate_numbers,
        "rating": rating,
        "notes": notes
    }, ensure_ascii=False)
    qr_b64 = make_qr_base64(f"VIP|{token}")
    return jsonify(success=True, message="وجّه الباركود للمحاسب للإعتماد", qr=qr_b64)

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8',80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    init_db()
    try:
        ip = get_local_ip()
        print(f"📱 افتح هذا الرابط من جوالك: http://{ip}:5000")
    except Exception:
        print("شغل السيرفر ثم افتح http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
