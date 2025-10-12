
# create_api_db.py - runs migration to create loyalty_api.db and copy clients safely
from api import init_api_db
import sqlite3, os, datetime, json

BASE_DIR = os.path.dirname(__file__)
LEGACY_DB = os.path.join(BASE_DIR, "loyalty.db")
API_DB = os.path.join(BASE_DIR, "loyalty_api.db")

def migrate():
    if not os.path.exists(LEGACY_DB):
        print("Legacy DB not found, skipping migration.")
        return
    src = sqlite3.connect(LEGACY_DB)
    src.row_factory = sqlite3.Row
    s = src.cursor()
    try:
        s.execute("SELECT * FROM clients")
        rows = s.fetchall()
    except Exception as e:
        print("Error reading legacy DB:", e)
        rows = []
    conn = sqlite3.connect(API_DB)
    cur = conn.cursor()
    for r in rows:
        phone = r['phone']
        name = r['name'] if 'name' in r.keys() else ''
        created_at = r['created_at'] if 'created_at' in r.keys() and r['created_at'] else datetime.datetime.utcnow().isoformat()
        # find or create client
        cur.execute("SELECT id FROM clients WHERE phone=?", (phone,))
        c = cur.fetchone()
        if c:
            client_id = c[0]
        else:
            cur.execute("INSERT INTO clients (name, phone, created_at) VALUES (?,?,?)", (name, phone, created_at))
            client_id = cur.lastrowid
        # insert car
        pl = r['plate_letters'] if 'plate_letters' in r.keys() else ''
        pn = r['plate_numbers'] if 'plate_numbers' in r.keys() else ''
        washes = r['washes'] if 'washes' in r.keys() and r['washes'] is not None else 0
        points = r['points'] if 'points' in r.keys() and r['points'] is not None else 0
        last_rating = r['last_rating'] if 'last_rating' in r.keys() else None
        notes = r['notes'] if 'notes' in r.keys() else ''
        try:
            cur.execute("INSERT INTO cars (client_id, plate_letters, plate_numbers, washes, points, last_rating, notes) VALUES (?,?,?,?,?,?,?)",
                        (client_id, pl, pn, washes, points, last_rating, notes))
        except Exception as e:
            pass
    conn.commit()
    conn.close()
    src.close()
    print("Migration done. Inserted", len(rows), "rows.")

if __name__ == '__main__':
    init_api_db()
    migrate()
