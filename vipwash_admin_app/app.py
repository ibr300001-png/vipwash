# -*- coding: utf-8 -*-
import os, sqlite3, random, io
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","vipwash-secret")
DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

STRINGS = {
    "ar": {"login_title":"تسجيل الدخول","username":"اسم المستخدم","password":"كلمة المرور","login":"دخول","logout":"تسجيل الخروج","dashboard":"الرئيسية","scanner":"قارئ الباركود","start":"بدء","stop":"إيقاف","approve":"اعتماد","token_label":"(TOKEN) إدخال يدوي (عرض فقط)","may_need_cam":"قد يتطلب إذن الكاميرا","total_visits":"إجمالي الزيارات","avg_rating":"متوسط التقييم","stats":"الإحصائيات","per_acc":"عمليات الغسيل لكل محاسب","accountant":"محاسب","count":"عدد","ratings_dist":"توزيع التقييمات","draw":"سحب عشوائي","settings":"الإعدادات","points_per_visit":"نقاط لكل زيارة","redeem_limit":"حد الاستبدال","front_text":"نص الفوتر بواجهة العملاء","front_link":"رابط الفوتر","draw_btn_text":"نص زر السحب العشوائي","save":"حفظ","users":"المستخدمون","add_user":"إضافة مستخدم","role":"الدور","admin":"أدمن","acc":"محاسب","actions":"إجراءات","edit":"تعديل","delete":"حذف","lang":"اللغة","theme":"الوضع","light":"نهاري","dark":"ليلي","no_data":"لا توجد بيانات","winner":"الفائز","send_whatsapp":"إرسال واتساب","export_pdf":"تصدير PDF","invalid":"خطأ في الاسم أو كلمة المرور"},
    "en": {"login_title":"Sign In","username":"Username","password":"Password","login":"Login","logout":"Logout","dashboard":"Home","scanner":"QR Scanner","start":"Start","stop":"Stop","approve":"Approve","token_label":"(TOKEN) Manual input (read-only)","may_need_cam":"May require camera permission","total_visits":"Total Visits","avg_rating":"Average Rating","stats":"Statistics","per_acc":"Washes per Accountant","accountant":"Accountant","count":"Count","ratings_dist":"Ratings Distribution","draw":"Random Draw","settings":"Settings","points_per_visit":"Points per Visit","redeem_limit":"Redeem Limit","front_text":"Clients footer text","front_link":"Footer link","draw_btn_text":"Draw button text","save":"Save","users":"Users","add_user":"Add User","role":"Role","admin":"Admin","acc":"Accountant","actions":"Actions","edit":"Edit","delete":"Delete","lang":"Language","theme":"Theme","light":"Light","dark":"Dark","no_data":"No data","winner":"Winner","send_whatsapp":"Send WhatsApp","export_pdf":"Export PDF","invalid":"Invalid username or password"}
}
def tr(key):
    lang = session.get("lang","ar")
    return STRINGS.get(lang, STRINGS["ar"]).get(key, key)
app.jinja_env.globals.update(tr=tr)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH); g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None: db.close()

def init_db():
    db = get_db(); c = db.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,password_hash TEXT,role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK (id=1),points_per_visit INTEGER DEFAULT 10,redeem_limit INTEGER DEFAULT 50,front_text TEXT DEFAULT 'أهلاً بك في غسيل وتلميع VIP',front_link TEXT DEFAULT 'https://vipwash.com',draw_text TEXT DEFAULT 'سحب عشوائي')")
    c.execute("INSERT OR IGNORE INTO settings(id) VALUES (1)")
    def seed_user(u,p,role):
        try: c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",(u, generate_password_hash(p), role))
        except sqlite3.IntegrityError: pass
    seed_user("admin","admin123","admin"); seed_user("acc","acc123","acc")
    c.execute("CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY AUTOINCREMENT,accountant TEXT,phone TEXT,plate TEXT,rating INTEGER DEFAULT 0,created_at TEXT)")
    db.commit()

def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if not session.get("user"): return redirect(url_for('login'))
        return f(*a, **kw)
    return wrap

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = request.form.get("username","").strip(); p=request.form.get("password","")
        row = get_db().execute("SELECT * FROM users WHERE username=?",(u,)).fetchone()
        if row and check_password_hash(row["password_hash"], p):
            session["user"]={"username":row["username"],"role":row["role"]}
            return redirect(url_for("cashier" if row["role"]=="acc" else "admin_home"))
        flash(tr("invalid"),"err")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.route("/lang/<code>")
def set_lang(code):
    session["lang"] = "en" if code=="en" else "ar"; return redirect(request.referrer or url_for('admin_home'))

@app.route("/theme/<mode>")
def set_theme(mode):
    session["theme"] = "light" if mode=="light" else "dark"; return redirect(request.referrer or url_for('admin_home'))

@app.route("/")
@login_required
def root():
    return redirect(url_for('cashier' if session.get('user',{}).get('role')=='acc' else 'admin_home'))

@app.route("/admin")
@login_required
def admin_home():
    if session['user']['role']!='admin': return redirect(url_for('cashier'))
    c = get_db().cursor()
    total_visits = c.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    avg_rating = c.execute("SELECT COALESCE(AVG(rating),0) FROM visits").fetchone()[0] or 0
    per_acc = c.execute("SELECT accountant, COUNT(*) cnt FROM visits GROUP BY accountant").fetchall()
    dist = {r: c.execute("SELECT COUNT(*) FROM visits WHERE rating=?", (r,)).fetchone()[0] for r in range(1,6)}
    st = c.execute("SELECT * FROM settings WHERE id=1").fetchone()
    return render_template("admin.html", total_visits=total_visits, avg_rating=round(avg_rating,2), per_acc=per_acc, dist=dist, st=st, user=session.get("user"))

@app.route("/cashier")
@login_required
def cashier():
    if session['user']['role']!='acc': return redirect(url_for('admin_home'))
    return render_template("accountant.html", user=session.get("user"))

@app.route("/api/save_settings", methods=["POST"])
@login_required
def api_save_settings():
    if session['user']['role']!='admin': return jsonify(ok=False),403
    d = request.json or {}
    get_db().execute("UPDATE settings SET points_per_visit=?, redeem_limit=?, front_text=?, front_link=?, draw_text=? WHERE id=1",
        (int(d.get("points_per_visit",10)), int(d.get("redeem_limit",50)), d.get("front_text",""), d.get("front_link",""), d.get("draw_text","")))
    get_db().commit(); return jsonify(ok=True)

@app.route("/api/users", methods=["GET","POST","DELETE"])
@login_required
def api_users():
    if session['user']['role']!='admin': return jsonify(ok=False),403
    db=get_db(); c=db.cursor()
    if request.method=="GET":
        rows=c.execute("SELECT id,username,role FROM users ORDER BY id").fetchall()
        return jsonify(ok=True, users=[dict(r) for r in rows])
    payload=request.json or {}
    if request.method=="POST":
        uid=payload.get("id"); u=payload.get("username","").strip(); role=payload.get("role","acc"); pw=payload.get("password")
        if uid:
            if pw: c.execute("UPDATE users SET username=?, role=?, password_hash=? WHERE id=?",(u,role,generate_password_hash(pw),uid))
            else:  c.execute("UPDATE users SET username=?, role=? WHERE id=?",(u,role,uid))
            db.commit(); return jsonify(ok=True)
        else:
            c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",(u,generate_password_hash(pw or "123456"),role))
            db.commit(); return jsonify(ok=True,created=True)
    if request.method=="DELETE":
        uid=payload.get("id"); row=c.execute("SELECT username FROM users WHERE id=?",(uid,)).fetchone()
        if row and row['username']=="admin": return jsonify(ok=False, msg="protected"),400
        c.execute("DELETE FROM users WHERE id=?",(uid,)); db.commit(); return jsonify(ok=True)

@app.route("/api/scan", methods=["POST"])
@login_required
def api_scan():
    token = (request.json or {}).get("token","").strip()
    if not token: return jsonify(ok=False),400
    info = {"name":"VIP","phone":"05"+token[-8:].rjust(8,'1'),"plate":f"{token[-4:]}-VIP","rating":random.randint(3,5),"visits":random.randint(1,20)}
    session["last_token"]=token; return jsonify(ok=True, client=info)

@app.route("/api/approve", methods=["POST"])
@login_required
def api_approve():
    p = request.json or {}; acc=session["user"]["username"]; phone=p.get("phone",""); plate=p.get("plate",""); rating=int(p.get("rating",5))
    get_db().execute("INSERT INTO visits(accountant, phone, plate, rating, created_at) VALUES(?,?,?,?,?)",(acc,phone,plate,rating, datetime.utcnow().isoformat())); get_db().commit()
    return jsonify(ok=True)

@app.route("/api/draw", methods=["POST"])
@login_required
def api_draw():
    if session['user']['role']!='admin': return jsonify(ok=False),403
    c=get_db().cursor(); rows=c.execute("SELECT phone,plate FROM visits ORDER BY RANDOM() LIMIT 1").fetchall()
    phone,plate=(rows[0]['phone'], rows[0]['plate']) if rows else ("0551112222","9999-VIP")
    return jsonify(ok=True, winner={"name":"VIP","phone":phone,"plate":plate})

@app.route("/export/pdf")
@login_required
def export_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import arabic_reshaper
    from bidi.algorithm import get_display

    def shape_ar(t):
        try: return get_display(arabic_reshaper.reshape(str(t)))
        except Exception: return str(t)

    tried=["C:/Windows/Fonts/trado.ttf","C:/Windows/Fonts/tahoma.ttf","C:/Windows/Fonts/arial.ttf","/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    font_name="Helvetica"
    for p in tried:
        if os.path.exists(p):
            try: pdfmetrics.registerFont(TTFont("Arabic",p)); font_name="Arabic"; break
            except: pass
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    c.setFont(font_name,18); title = "تقرير العملاء" if session.get("lang","ar")=="ar" else "Clients Report"
    if session.get("lang","ar")=="ar":
        c.drawRightString(w-40,h-50, shape_ar(title))
    else:
        c.drawString(40,h-50,title)
    rows=get_db().execute("SELECT phone,plate,rating FROM visits ORDER BY id DESC LIMIT 100").fetchall()
    c.setFont(font_name,14); y=h-100
    if not rows:
        txt="لا توجد بيانات" if session.get("lang","ar")=="ar" else "No data"
        if session.get("lang","ar")=="ar": c.drawRightString(w-40,y,shape_ar(txt))
        else: c.drawString(40,y,txt)
    else:
        for r in rows:
            if session.get("lang","ar")=="ar":
                line=f"الهاتف: {r['phone']} | اللوحة: {r['plate']} | التقييم: {r['rating']}"
                c.drawRightString(w-40,y, shape_ar(line))
            else:
                line=f"Phone: {r['phone']} | Plate: {r['plate']} | Rating: {r['rating']}"
                c.drawString(40,y,line)
            y-=22
            if y<60: c.showPage(); c.setFont(font_name,14); y=h-60
    c.save(); buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="vipwash_report.pdf")

if __name__=="__main__":
    with app.app_context(): init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",6500)), debug=False)
