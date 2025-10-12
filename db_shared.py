import os, sqlite3
from datetime import datetime

DB_DIR = os.environ.get("DB_DIR") or os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
SITE_DB = os.path.join(DB_DIR, "site.db")

def conn():
    c = sqlite3.connect(SITE_DB)
    c.row_factory = sqlite3.Row
    return c

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def init_db():
    c = conn(); cur=c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT UNIQUE,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plate_letters TEXT, plate_numbers TEXT,
        car_type TEXT, car_model TEXT,
        points INTEGER DEFAULT 0,
        washes INTEGER DEFAULT 0,
        last_rating INTEGER,
        created_at TEXT,
        UNIQUE(plate_letters, plate_numbers),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER, user_id INTEGER,
        type TEXT, points_delta INTEGER DEFAULT 0,
        washes_delta INTEGER DEFAULT 0, rating INTEGER,
        token TEXT, token_expires_at TEXT, used INTEGER DEFAULT 0,
        source TEXT, created_at TEXT
    )""")
    c.commit(); c.close()
