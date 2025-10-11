# -*- coding: utf-8 -*-
import os, io, json, base64, sqlite3, hashlib, secrets, qrcode
from datetime import datetime
from flask import Flask, Blueprint, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)

# --------- Config: DB paths (override via env) ---------
BASE_DIR = os.path.dirname(__file__)
LOYALTY_API_DB = os.getenv("LOYALTY_API_DB", os.path.join(BASE_DIR, "loyalty_api.db"))
LOYALTY_DB     = os.getenv("LOYALTY_DB",     os.path.join(BASE_DIR, "loyalty.db"))

def now_iso(): return datetime.utcnow().isoformat()

def db_api():
    conn = sqlite3.connect(LOYALTY_API_DB)
    conn.row_factory = sqlite3.Row
    return conn

def db_customer():
    conn = sqlite3.connect(LOYALTY_DB)
    conn.row_factory = sqlite3.Row
    return conn

def phash(p: str) -> str:
    return hashlib.sha256(("vipwash::" + p).encode()).hexdigest()

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    static_folder=os.path.join(BASE_DIR, "adminpanel", "static"),
    template_folder=os.path.join(BASE_DIR, "adminpanel", "static"),
)

# ----------------- Static routes -----------------
@bp.route("/")
def index():
    return send_from_directory(bp.static_folder, "index.html")

@bp.route("/assets/<path:p>")
def serve_assets(p):
    return send_from_directory(os.path.join(bp.static_folder, "assets"), p)

@bp.route("/app.js")
def serve_app_js():
    return send_from_directory(bp.static_folder, "app.js")

# ----------------- AUTH -----------------
@bp.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    role_ui  = (data.get("role") or "ADMIN").strip()     # ADMIN / ACCOUNTANT
    role_db  = "admin" if role_ui == "ADMIN" else "cashier"

    conn = db_api(); cur = conn.cursor()
    # Ensure users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,          -- admin/cashier
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)
    # Seed defaults if missing
    cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                ("qaaz", phash("1234"), "admin",   now_iso()))
    cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                ("amee", phash("1234"), "cashier", now_iso()))
    conn.commit()

    cur.execute("SELECT * FROM users WHERE username=? AND role=? AND active=1", (username, role_db))
    u = cur.fetchone()
    conn.close()

    if (not u) or u["password_hash"] != phash(password):
        return jsonify(ok=False), 401

    return jsonify(ok=True, user={"id": u["id"], "name": u["username"], "email": u["username"], "role": role_ui})

# ----------------- SETTINGS -----------------
@bp.get("/api/settings")
def get_settings():
    conn = db_api(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('points_per_scan','10')")
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('free_wash_threshold','50')")
    conn.commit()
    cur.execute("SELECT key,value FROM settings WHERE key IN ('points_per_scan','free_wash_threshold')")
    m = {r["key"]: r["value"] for r in cur.fetchall()}
    conn.close()
    return jsonify(ok=True, settings={
        "pointsPerVisit":   int(m.get("points_per_scan", "10")),
        "redeemThreshold":  int(m.get("free_wash_threshold", "50"))
    })

@bp.patch("/api/settings")
def patch_settings():
    body = request.get_json(silent=True) or {}
    ppv = int(body.get("pointsPerVisit", 10))
    rt  = int(body.get("redeemThreshold", 50))
    conn = db_api(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('points_per_scan',?)", (str(ppv),))
    cur.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('free_wash_threshold',?)", (str(rt),))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ----------------- USERS CRUD -----------------
@bp.get("/api/users")
def users_list():
    conn = db_api(); cur = conn.cursor()
    cur.execute("SELECT id, username, role, active FROM users WHERE active=1 ORDER BY id")
    arr = [{
        "id": r["id"],
        "email": r["username"],
        "role": "ADMIN" if r["role"] == "admin" else "ACCOUNTANT"
    } for r in cur.fetchall()]
    conn.close()
    return jsonify(ok=True, users=arr)

@bp.post("/api/users")
def users_add():
    d = request.get_json(silent=True) or {}
    username = (d.get("email") or "").strip()
    role_ui  = (d.get("role") or "ACCOUNTANT").strip()
    role_db  = "admin" if role_ui == "ADMIN" else "cashier"
    password = (d.get("password") or "1234").strip()
    if not username:
        return jsonify(ok=False, error="username required"), 400
    conn = db_api(); cur = conn.cursor()
    cur.execute("INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                (username, phash(password), role_db, 1, now_iso()))
    conn.commit(); conn.close()
    return jsonify(ok=True)

@bp.patch("/api/users/<int:uid>")
def users_edit(uid):
    d = request.get_json(silent=True) or {}
    conn = db_api(); cur = conn.cursor()
    if "password" in d:
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (phash(d["password"]), uid))
    if "role" in d:
        cur.execute("UPDATE users SET role=? WHERE id=?", ("admin" if d["role"] == "ADMIN" else "cashier", uid))
    if ("email" in d):
        cur.execute("UPDATE users SET username=? WHERE id=?", (d["email"], uid))
    conn.commit(); conn.close()
    return jsonify(ok=True)

@bp.delete("/api/users/<int:uid>")
def users_delete(uid):
    conn = db_api(); cur = conn.cursor()
    cur.execute("UPDATE users SET active=0 WHERE id=?", (uid,))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ----------------- ALERTS (derived from rating_history) -----------------
def derive_alerts():
    """Rules:
       - If last rating < 5 after three consecutive 5★ earlier -> drop alert
       - If there are two ratings ≤ 2 among last 3 -> low satisfaction alert
    """
    conn = db_api(); cur = conn.cursor()
    alerts = []
    try:
        cur.execute("""
            SELECT c.id car_id, cl.name, cl.phone, c.plate_letters, c.plate_numbers, c.rating_history
            FROM cars c
            JOIN clients cl ON c.client_id = cl.id
        """)
        rows = cur.fetchall()
    except Exception:
        conn.close(); return []

    for r in rows:
        rh_raw = r["rating_history"] or "[]"
        try:
            hist = json.loads(rh_raw)
        except Exception:
            hist = []
        ratings = [int(x.get("rating", 0)) for x in hist]
        if not ratings:
            continue

        last = ratings[-1]

        # rule 1: 5,5,5 then drop
        drop = False
        if len(ratings) >= 4 and last < 5:
            for i in range(len(ratings) - 3):
                if ratings[i] == 5 and ratings[i+1] == 5 and ratings[i+2] == 5:
                    drop = True
                    break
        if drop:
            alerts.append({
                "car_id": r["car_id"], "created_at": now_iso(),
                "message": "عميل كان يقيم 5★ ثم انخفض التقييم مؤخرًا",
                "name": r["name"], "phone": r["phone"],
                "plate_letters": r["plate_letters"], "plate_numbers": r["plate_numbers"], "seen": 0
            })

        # rule 2: two lows (<=2) in last 3
        low_recent = [x for x in ratings[-3:] if x <= 2]
        if len(low_recent) >= 2:
            alerts.append({
                "car_id": r["car_id"], "created_at": now_iso(),
                "message": "عميل قيّم أقل من نجمتين مرتين مؤخرًا",
                "name": r["name"], "phone": r["phone"],
                "plate_letters": r["plate_letters"], "plate_numbers": r["plate_numbers"], "seen": 0
            })

    conn.close()
    return alerts[:50]

@bp.get("/api/alerts")
def alerts_get():
    return jsonify(ok=True, alerts=derive_alerts())

# ----------------- STATS -----------------
@bp.get("/api/stats")
def stats():
    conn = db_api(); cur = conn.cursor()
    out = {"accountants": [], "ratings": {}, "peaks": {}}
    try:
        cur.execute("""
            SELECT user_id, COUNT(*) c
            FROM transactions
            WHERE type='verify'
            GROUP BY user_id
        """)
        rows = cur.fetchall()
        ids = [r["user_id"] for r in rows if r["user_id"] is not None]
        name_map = {}
        if ids:
            q = "SELECT id,username FROM users WHERE id IN (%s)" % ",".join("?"*len(ids))
            cur.execute(q, tuple(ids))
            name_map = {r["id"]: r["username"] for r in cur.fetchall()}
        out["accountants"] = [
            {"user": name_map.get(r["user_id"], str(r["user_id"])), "count": r["c"]}
            for r in rows if r["user_id"] is not None
        ]
    except Exception:
        pass

    try:
        cur.execute("SELECT rating_history FROM cars WHERE rating_history IS NOT NULL")
        hist = {"1":0,"2":0,"3":0,"4":0,"5":0}
        for r in cur.fetchall():
            try:
                arr = json.loads(r["rating_history"] or "[]")
                for it in arr:
                    val = str(int(it.get("rating", 0)))
                    if val in hist:
                        hist[val] += 1
            except Exception:
                continue
        out["ratings"] = hist
    except Exception:
        pass

    try:
        cur.execute("SELECT created_at FROM transactions WHERE type='verify'")
        peaks = {}
        for r in cur.fetchall():
            ts = r["created_at"] or ""
            hh = ts[11:13] if len(ts) >= 13 else "00"
            peaks[hh] = peaks.get(hh, 0) + 1
        out["peaks"] = peaks
    except Exception:
        pass

    conn.close()
    return jsonify(ok=True, stats=out)

# ----------------- CLIENTS (for listing/export) -----------------
@bp.get("/api/clients")
def clients_list():
    # Join cars + clients from API DB (authoritative for car info)
    conn = db_api(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id car_id, cl.name, cl.phone, c.plate_letters, c.plate_numbers, c.washes, c.points, c.rating_history,
                   COALESCE(NULL, '') AS car_type
            FROM cars c
            JOIN clients cl ON c.client_id=cl.id
        """)
        rows = cur.fetchall()
    except Exception as e:
        conn.close(); return jsonify(ok=False, error=str(e)), 500

    out = []
    for r in rows:
        # Sum last 5 ratings
        hist = []
        try:
            hist = json.loads(r["rating_history"] or "[]")
        except Exception:
            hist = []
        last5 = [int(x.get("rating", 0)) for x in hist[-5:]]
        out.append({
            "car_id": r["car_id"],
            "name": r["name"], "phone": r["phone"],
            "car_type": r["car_type"],
            "plate": f"{r['plate_letters']}-{r['plate_numbers']}",
            "visits": int(r["washes"] or 0),
            "points": int(r["points"] or 0),
            "ratings_sum_last5": sum(last5),
            "ratings_last5": last5
        })

    conn.close()
    return jsonify(ok=True, clients=out)

# ----------------- VERIFY / REDEEM -----------------
@bp.post("/api/verify")
def api_verify():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    action = (d.get("action") or "").strip()  # '' | 'visit'
    user_id = int(d.get("user_id") or 0)

    conn = db_api(); cur = conn.cursor()
    # Ensure tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            car_id INTEGER,
            status TEXT,
            points_to_add INTEGER,
            created_at TEXT,
            verified_at TEXT,
            verified_by_user_id INTEGER
        )
    """)
    conn.commit()

    cur.execute("""
        SELECT v.*, c.washes, c.points, c.plate_letters, c.plate_numbers,
               cl.name, cl.phone, c.client_id
        FROM verifications v
        JOIN cars c ON v.car_id=c.id
        JOIN clients cl ON c.client_id=cl.id
        WHERE v.token=?
    """, (token,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error="invalid token"), 404

    # thresholds
    cur.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('free_wash_threshold','50')")
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('points_per_scan','10')")
    conn.commit()
    cur.execute("SELECT value FROM settings WHERE key='free_wash_threshold'")
    rt = int((cur.fetchone() or {"value":"50"})["value"])
    cur.execute("SELECT value FROM settings WHERE key='points_per_scan'")
    ppv = int((cur.fetchone() or {"value":"10"})["value"])

    can_redeem = (row["points"] or 0) >= rt

    # Approve visit
    if action == "visit" and (row["status"] or "pending") != "used":
        cur.execute("UPDATE cars SET washes=COALESCE(washes,0)+1, points=COALESCE(points,0)+? WHERE id=?", (ppv, row["car_id"]))
        cur.execute("UPDATE verifications SET status='used', verified_at=?, verified_by_user_id=? WHERE token=?", (now_iso(), user_id, token))
        # log transaction
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, car_id INTEGER, user_id INTEGER, created_at TEXT
            )
        """)
        cur.execute("INSERT INTO transactions(type,car_id,user_id,created_at) VALUES(?,?,?,?)", ("verify", row["car_id"], user_id, now_iso()))
        conn.commit()

    client = {
        "name": row["name"], "phone": row["phone"],
        "plate": f"{row['plate_letters']}-{row['plate_numbers']}",
        "washes": row["washes"] or 0, "points": row["points"] or 0,
        "car_id": row["car_id"], "client_id": row["client_id"]
    }
    conn.close()
    return jsonify(ok=True, client=client, canRedeem=can_redeem)

@bp.post("/api/redeem")
def api_redeem():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    user_id = int(d.get("user_id") or 0)

    conn = db_api(); cur = conn.cursor()
    cur.execute("""
        SELECT v.*, c.points, c.id as car_id
        FROM verifications v
        JOIN cars c ON v.car_id=c.id
        WHERE v.token=?
    """, (token,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error="invalid token"), 404

    cur.execute("SELECT value FROM settings WHERE key='free_wash_threshold'")
    rt = int((cur.fetchone() or {"value":"50"})["value"])
    if (row["points"] or 0) < rt:
        conn.close(); return jsonify(ok=False, error="not enough points"), 400

    cur.execute("UPDATE cars SET points = COALESCE(points,0) - ? WHERE id=?", (rt, row["car_id"]))
    # log transaction
    cur.execute("INSERT INTO transactions(type,car_id,user_id,created_at) VALUES(?,?,?,?)", ("redeem", row["car_id"], user_id, now_iso()))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ----------------- RAFFLE -----------------
@bp.post("/api/raffle")
def raffle():
    conn = db_api(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id car_id, cl.name, cl.phone, c.plate_letters, c.plate_numbers
            FROM cars c JOIN clients cl ON c.client_id=cl.id
            ORDER BY RANDOM() LIMIT 1
        """)
        w = cur.fetchone()
        if not w:
            conn.close(); return jsonify(ok=False, reason="no candidates"), 404

        token = secrets.token_urlsafe(16)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verifications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE,
                car_id INTEGER,
                status TEXT,
                points_to_add INTEGER,
                created_at TEXT,
                verified_at TEXT,
                verified_by_user_id INTEGER
            )
        """)
        cur.execute(
            "INSERT INTO verifications(token,car_id,status,points_to_add,created_at) VALUES(?,?,?,?,?)",
            (token, w["car_id"], "pending", 0, now_iso())
        )
        conn.commit()

        # QR
        img = qrcode.make(f"VIP|TOKEN:{token}")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        conn.close()

        return jsonify(
            ok=True,
            token=token,
            qr="data:image/png;base64," + b64,
            winner={
                "name":  w["name"],
                "phone": w["phone"],
                "plate": f"{w['plate_letters']}-{w['plate_numbers']}",
                "car_id": w["car_id"],
            },
            wa_message_ar=(
                "مبروووك 🎉\\n"
                "اهلاً عميلنا الوفي 🤍\\n"
                "تم اختيارك عشوائياً من بين عملائنا للحصول على غسيل مجاني في غسيل وتلميع VIP ✨\\n\\n"
                "📌 الرجاء إبراز الباركود أدناه للمحاسب قبل الغسيل للاستفادة من هديتك.\\n"
                "شكرًا لثقتك بنا، ونتمنى لك يوم يلمع مثل سيارتك بعد الغسيل 😄🚗💦\\n"
                "[فريق غسيل وتلميع VIP]\\n"
                "الهدايا عندنا تجي بدون موعد🥳"
            )
        )
    except Exception as e:
        conn.close()
        return jsonify(ok=False, error=str(e)), 500

app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
