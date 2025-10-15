# repair_templates.py
# يُصلح قوالب العملاء التي تحتوي على {{ url_for('static', filename='\1') }}
# ويعيد كتابة الروابط إلى ملفات موجودة فعلاً داخل customers_app/static أو vipwash_client_only/static

from pathlib import Path
import re

ROOT = Path(__file__).parent
CANDIDATE_APP_DIRS = [
    ("customers_app", ROOT / "customers_app"),
    ("vipwash_client_only", ROOT / "vipwash_client_only"),
]

PREF_CSS = ["style.css", "app.css", "main.css", "styles.css"]
PREF_JS  = ["app.js", "main.js", "bundle.js", "script.js"]

def pick_file(static_dir: Path, exts, prefs):
    if not static_dir or not static_dir.exists():
        return None
    files = [p for p in static_dir.rglob("*") if p.suffix.lower() in exts]
    if not files:
        return None
    # تفضيل أسماء شائعة
    for name in prefs:
        for p in files:
            if p.name.lower() == name:
                return p
    # وإلا خذ أول ملف بالمسار الأقصر
    files.sort(key=lambda p: (len(p.parts), p.name.lower()))
    return files[0]

def rel_from_static(static_dir: Path, file_path: Path):
    # حوّل المسار إلى اسم نسبي من داخل مجلد static
    return str(file_path.relative_to(static_dir).as_posix())

BROKEN = r"url_for\('static', filename='\\1'\)"  # النمط المكسور

def fix_template(tpl_path: Path, static_dir: Path):
    s = tpl_path.read_text(encoding="utf-8", errors="ignore")
    o = s

    # 1) لو النمط المكسور موجود داخل <link rel="stylesheet"...> عالّجه بملف CSS
    if re.search(BROKEN, s):
        css = pick_file(static_dir, exts={".css"}, prefs=PREF_CSS)
        js  = pick_file(static_dir, exts={".js"},  prefs=PREF_JS)

        if css:
            css_rel = rel_from_static(static_dir, css)
            s = re.sub(
                r'href="\{\{ ' + BROKEN + r' \}\}"',
                f'href="{{ url_for(\'static\', filename=\'{css_rel}\') }}"',
                s
            )
        if js:
            js_rel = rel_from_static(static_dir, js)
            s = re.sub(
                r'src="\{\{ ' + BROKEN + r' \}\}"',
                f'src="{{ url_for(\'static\', filename=\'{js_rel}\') }}"',
                s
            )

        # وأي بقايا \1 داخل خصائص أخرى (مثلاً صور)
        # حاوِل التقاط الامتدادات الشائعة ووضع ملف فعلي مماثل
        # صور
        img = None
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
            cand = pick_file(static_dir, exts={ext}, prefs=[])
            if cand:
                img = cand; break
        if img:
            img_rel = rel_from_static(static_dir, img)
            s = re.sub(
                r'src="\{\{ ' + BROKEN + r' \}\}"',
                f'src="{{ url_for(\'static\', filename=\'{img_rel}\') }}"',
                s
            )

    # 2) لو بقي نمطنا القديم الصحيح لكن مع \1 (أي في أي مكان)، استبدله آمنًا بملف مفضّل
    if "\\1" in s:
        # اختر CSS/JS احتياطيًا
        css = pick_file(static_dir, exts={".css"}, prefs=PREF_CSS)
        js  = pick_file(static_dir, exts={".js"},  prefs=PREF_JS)
        if css:
            css_rel = rel_from_static(static_dir, css)
            s = s.replace("filename='\\1'", f"filename='{css_rel}'")
        if js:
            js_rel = rel_from_static(static_dir, js)
            s = s.replace("filename='\\1'", f"filename='{js_rel}'")

    if s != o:
        tpl_path.write_text(s, encoding="utf-8")
        print(f"[fixed] {tpl_path}")
        return True
    return False

def run():
    any_fixed = False
    for app_name, base in CANDIDATE_APP_DIRS:
        tpl_dir = base / "templates"
        static_dir = base / "static"
        if not tpl_dir.exists():
            continue
        for p in tpl_dir.rglob("*.html"):
            changed = fix_template(p, static_dir if static_dir.exists() else None)
            any_fixed = any_fixed or changed
    if not any_fixed:
        print("No broken patterns found. If error persists, share the first 20 lines of the failing template.")
    print("Done.")

if __name__ == "__main__":
    run()
