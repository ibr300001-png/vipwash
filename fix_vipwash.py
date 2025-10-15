# fix_vipwash.py
# يصلّح التوجيه: الإدارة على الجذر / والعميل تحت /client/ + يضمن المتطلبات + يرقّع القوالب

import importlib
import sys
from pathlib import Path
import re
from textwrap import dedent

ROOT = Path(__file__).parent

def try_import(candidates, label):
    errors = []
    for mod, attr in candidates:
        try:
            m = importlib.import_module(mod)
            a = getattr(m, attr)
            print(f"[detect] {label}: using {mod}.{attr}")
            return a, f"{mod}"
        except Exception as e:
            errors.append(f"{mod}.{attr}: {e}")
    print(f"!! لم أستطع استيراد {label} من المرشحين:\n" + "\n".join(errors), file=sys.stderr)
    sys.exit(1)

# جرّب أسماء شائعة لتطبيق الإدارة
admin_app, admin_mod = try_import([
    ("vipwash_admin_app.app","app"),
    ("vipwash_admin_app","app"),
    ("admin_app.app","app"),
    ("admin","app"),
], "admin")

# جرّب أسماء شائعة لتطبيق العميل
client_app, client_mod = try_import([
    ("customers_app.app","app"),
    ("customers_app","app"),
    ("vipwash_client_only.app","app"),
    ("vipwash_client_only","app"),
], "client")

# اكتب وحدات كاشفة صغيرة كي لا نكسر مسارات الاستيراد
(ROOT / "__wsgi_detect_admin__.py").write_text(
    f"from {admin_mod} import app\n", encoding="utf-8"
)
(ROOT / "__wsgi_detect_client__.py").write_text(
    f"from {client_mod} import app\n", encoding="utf-8"
)

# اكتب wsgi.py (الإدارة على الجذر، العميل على /client، دعم SCRIPT_NAME + healthz)
wsgi_code = dedent("""\
from werkzeug.middleware.proxy_fix import ProxyFix

# هذا الملف تم توليده آليًا بواسطة fix_vipwash.py
from __wsgi_detect_admin__ import app as _A
from __wsgi_detect_client__ import app as _C

A = ProxyFix(_A, x_for=1, x_proto=1, x_host=1, x_port=1)
C = ProxyFix(_C, x_for=1, x_proto=1, x_host=1, x_port=1)

P = "/client"

def _sub(app, e, s, p):
    n = e.copy()
    q = n.get("PATH_INFO", "") or "/"
    n["PATH_INFO"] = q[len(p):] or "/"
    n["SCRIPT_NAME"] = (n.get("SCRIPT_NAME", "") + p).rstrip("/")
    return app(n, s)

def application(e, s):
    p = e.get("PATH_INFO", "") or "/"
    if p == "/healthz":
        s("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]
    if p == P:
        s("302 Found", [("Location", P + "/")])
        return [b""]
    if p.startswith(P + "/"):
        return _sub(C, e, s, P)
    return A(e, s)

app = application
""")
(ROOT / "wsgi.py").write_text(wsgi_code, encoding="utf-8")
print(f"[OK] wsgi.py written (admin={admin_mod}, client={client_mod})")

# ضَمّن المتطلبات في requirements.txt (أضِف إن لم تكن موجودة)
req_path = ROOT / "requirements.txt"
needed = [
    "gunicorn",
    "werkzeug>=3",
    "Flask>=3.0",
    "qrcode[pil]",
    "Pillow",
    "reportlab",
    "arabic-reshaper",
    "python-bidi",
]
existing = set()
if req_path.exists():
    for line in req_path.read_text(encoding="utf-8").splitlines():
        existing.add(line.strip().lower())

with req_path.open("a", encoding="utf-8") as f:
    for pkg in needed:
        key = pkg.split("==")[0].split(">=")[0].strip().lower()
        if not any(line.startswith(key) for line in existing):
            f.write(pkg + "\n")
            print(f"[req] added {pkg}")

print("[OK] requirements.txt ensured")

# ترقيع قوالب العميل إن وجدت (يُبدّل /static/ إلى url_for(..) وروابط داخلية لتستخدم script_root)
def patch_templates(dirpath: Path):
    if not dirpath.exists():
        return
    print(f"[..] patching templates in {dirpath}")
    for p in dirpath.rglob("*.html"):
        s = p.read_text(encoding="utf-8", errors="ignore")
        o = s
        s = re.sub(r'href="/static/([^"]+)"', r'href="{{ url_for(\'static\', filename=\'\\1\') }}"', s)
        s = re.sub(r'src="/static/([^"]+)"',  r'src="{{ url_for(\'static\', filename=\'\\1\') }}"', s)
        s = s.replace('href="/new"',     'href="{{ request.script_root }}/new"')
        s = s.replace('href="/loyal"',   'href="{{ request.script_root }}/loyal"')
        s = s.replace('href="/clients"', 'href="{{ request.script_root }}/clients"')
        if s != o:
            p.write_text(s, encoding="utf-8")
            print(f"[patched] {p}")

patch_templates(ROOT / "customers_app" / "templates")
patch_templates(ROOT / "vipwash_client_only" / "templates")

print("\n[تم] جاهز للرفع على Render.")
print("Start Command على Render:")
print("  gunicorn wsgi:application --workers=2 --threads=8 --bind 0.0.0.0:$PORT")
print("\nللتجربة محليًا على ويندوز (بدون gunicorn)، شغّل:  python run_local.py 8000  ثم افتح:")
print("  http://localhost:8000/         (الإدارة)")
print("  http://localhost:8000/client/  (العملاء)")
print("  http://localhost:8000/healthz  (health)")
