# vipwash_fix_all.py
from pathlib import Path
import re, importlib, sys
from textwrap import dedent

ROOT = Path(__file__).parent
APPS = [ROOT/"customers_app", ROOT/"vipwash_client_only"]

def try_import(cands, label):
    errs=[]
    for mod,attr in cands:
        try:
            m = importlib.import_module(mod)
            a = getattr(m, attr)
            print(f"[detect] {label}: {mod}.{attr}")
            return a, m.__name__
        except Exception as e:
            errs.append(f"{mod}.{attr}: {e}")
    print("!! failed to import", label, "candidates:\n" + "\n".join(errs), file=sys.stderr); sys.exit(1)

# اكتشاف تطبيق الإدارة والعميل
admin_app, admin_mod = try_import([
    ("vipwash_admin_app.app","app"),
    ("vipwash_admin_app","app"),
    ("admin_app.app","app"),
    ("admin","app"),
], "admin")

client_app, client_mod = try_import([
    ("customers_app.app","app"),
    ("customers_app","app"),
    ("vipwash_client_only.app","app"),
    ("vipwash_client_only","app"),
], "client")

# وحدات كشف لتسهيل الاستيراد داخل wsgi
(ROOT/"__wsgi_detect_admin__.py").write_text(f"from {admin_mod} import app\n", encoding="utf-8")
(ROOT/"__wsgi_detect_client__.py").write_text(f"from {client_mod} import app\n", encoding="utf-8")

# wsgi.py — الإدارة على الجذر، العميل تحت /client مع SCRIPT_NAME + /healthz
wsgi_code = dedent("""\
from werkzeug.middleware.proxy_fix import ProxyFix
from __wsgi_detect_admin__ import app as _A
from __wsgi_detect_client__ import app as _C

A = ProxyFix(_A, x_for=1, x_proto=1, x_host=1, x_port=1)
C = ProxyFix(_C, x_for=1, x_proto=1, x_host=1, x_port=1)
P = "/client"

def _sub(app, e, s, p):
    n = e.copy()
    q = n.get("PATH_INFO","") or "/"
    n["PATH_INFO"]   = q[len(p):] or "/"
    n["SCRIPT_NAME"] = (n.get("SCRIPT_NAME","") + p).rstrip("/")
    return app(n, s)

def application(e, s):
    p = e.get("PATH_INFO","") or "/"
    if p == "/healthz":
        s("200 OK",[("Content-Type","text/plain; charset=utf-8")]); return [b"ok"]
    if p == P:
        s("302 Found",[("Location", P + "/")]); return [b""]
    if p.startswith(P + "/"):
        return _sub(C, e, s, P)
    return A(e, s)

app = application
""")
(ROOT/"wsgi.py").write_text(wsgi_code, encoding="utf-8")
print("[OK] wsgi.py written")

# 2) إصلاح القوالب: 
# - تحويل href/src المطلقة /static/... إلى url_for بالسند الصحيح (\g<1>)
# - تصحيح أي حقن خاطئ لـ \1 (escaped أو عادي) واختيار ملف فعلي من static
PREF_CSS = ["style.css","app.css","main.css","styles.css"]
PREF_JS  = ["app.js","main.js","bundle.js","script.js"]
IMG_EXTS = [".png",".jpg",".jpeg",".gif",".svg",".webp"]

def pick(static_dir: Path, exts, prefs=()):
    if not static_dir or not static_dir.exists(): return None
    files = [p for p in static_dir.rglob("*") if p.suffix.lower() in exts]
    if not files: return None
    for name in prefs:
        for p in files:
            if p.name.lower() == name: return p
    files.sort(key=lambda p:(len(p.parts), p.name.lower()))
    return files[0]

def rel(static_dir: Path, p: Path):
    return str(p.relative_to(static_dir).as_posix())

def fix_html(f: Path, static_dir: Path):
    s = f.read_text(encoding="utf-8", errors="ignore"); o = s

    # /static/... -> url_for('static', filename='<path>')
    s = re.sub(r'href="/static/([^"]+)"',  r'href="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)
    s = re.sub(r'src="/static/([^"]+)"',   r'src="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)

    # أنماط filename='\1' (كل الأشكال)
    if "\\1" in s or r"\'\1\'" in s or r'\"\1\"' in s:
        css = pick(static_dir, {".css"}, PREF_CSS)
        js  = pick(static_dir, {".js"},  PREF_JS)
        img = pick(static_dir, set(IMG_EXTS), ())
        # داخل link rel=stylesheet -> CSS
        if css:
            s = re.sub(r'href="\{\{\s*url_for\(\s*[\'\\"]static[\'\\"]\s*,\s*filename\s*=\s*[\'\\"][\\]*1[\'\\"]\s*\)\s*\}\}"',
                       f'href="{{{{ url_for(\'static\', filename=\'{rel(static_dir, css)}\') }}}}"', s)
            s = re.sub(r"href='\{\{\s*url_for\(\s*[\'\\\"]static[\'\\\"]\s*,\s*filename\s*=\s*[\'\\\"][\\]*1[\'\\\"]\s*\)\s*\}\}'",
                       f"href='{{{{ url_for('static', filename='{rel(static_dir, css)}') }}}}'", s)
        # داخل script src -> JS
        if js:
            s = re.sub(r'src="\{\{\s*url_for\(\s*[\'\\"]static[\'\\"]\s*,\s*filename\s*=\s*[\'\\"][\\]*1[\'\\"]\s*\)\s*\}\}"',
                       f'src="{{{{ url_for(\'static\', filename=\'{rel(static_dir, js)}\') }}}}"', s)
            s = re.sub(r"src='\{\{\s*url_for\(\s*[\'\\\"]static[\'\\\"]\s*,\s*filename\s*=\s*[\'\\\"][\\]*1[\'\\\"]\s*\)\s*\}\}'",
                       f"src='{{{{ url_for('static', filename='{rel(static_dir, js)}') }}}}'", s)
        # أي بقايا عامة استبدال احتياطي بـ CSS أو JS ثم صورة
        repl = None
        if css: repl = rel(static_dir, css)
        elif js: repl = rel(static_dir, js)
        if repl:
            for tok in ["filename='\\1'","filename=\"\\1\"", r"filename=\'\1\'", r'filename=\"\1\"']:
                s = s.replace(tok, f"filename='{repl}'")
        if "\\1" in s and img:
            s = s.replace("\\1", rel(static_dir, img))

    if s != o:
        f.write_text(s, encoding="utf-8")
        print(f"[fixed] {f}")

for app_dir in APPS:
    tpl = app_dir/"templates"; static = app_dir/"static"
    if not tpl.exists(): continue
    for f in tpl.rglob("*.html"):
        fix_html(f, static if static.exists() else None)

print("[OK] templates scanned & fixed where needed")

# 3) requirements.txt — ضمان الحزم
req = ROOT/"requirements.txt"
need = [
    "Flask==3.0.3",
    "Flask-Cors==4.0.1",
    "qrcode==7.4.2",
    "Pillow==10.4.0",
    "gunicorn==22.0.0",
    "werkzeug>=3",
    "reportlab",
    "arabic-reshaper",
    "python-bidi",
]
existing = set()
if req.exists():
    existing = {l.strip().lower() for l in req.read_text(encoding="utf-8").splitlines() if l.strip()}
with req.open("a", encoding="utf-8") as f:
    for pkg in need:
        key = pkg.split("==")[0].split(">=")[0].strip().lower()
        if not any(x.startswith(key) for x in existing):
            f.write(pkg+"\n"); print("[req] add", pkg)
print("[OK] requirements ensured")

# 4) تهيئة قاعدة البيانات إن وُجد سكربت مشارك
def try_db_init():
    try:
        db = importlib.import_module("db_shared")
    except Exception:
        print("[db] db_shared.py not found, skip"); return
    candidates = ["init_db","create_tables","setup_db","init_database"]
    for name in candidates:
        fn = getattr(db, name, None)
        if callable(fn):
            try:
                fn(); print(f"[db] {name}() executed")
                return
            except Exception as e:
                print(f"[db] {name}() failed: {e}")
    print("[db] no init function executed")

try_db_init()

# 5) run_local.py (خادم محلي)
run_local = dedent("""\
from wsgi import application
from werkzeug.serving import run_simple
if __name__ == "__main__":
    port = 8000
    print(f"Serving on http://localhost:{port}")
    run_simple("0.0.0.0", port, application, use_reloader=True, use_debugger=True)
""")
(ROOT/"run_local.py").write_text(run_local, encoding="utf-8")
print("[OK] run_local.py ready")

print("\n[READY] Now install deps then run locally:")
print("  py -m pip install -r requirements.txt")
print("  py run_local.py")
