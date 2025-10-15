# repair_templates_v2.py
# يلتقط كل أنماط \1 داخل url_for('static', filename=...) سواء باقتباسات مهربة \' \" أو عادية،
# ويستبدلها بملف فعلي من مجلد static (يفضّل style.css و app.js إن وُجدا).

from pathlib import Path
import re

ROOT = Path(__file__).parent
APPS = [ROOT/"customers_app", ROOT/"vipwash_client_only"]

PREF_CSS = ["style.css","app.css","main.css","styles.css"]
PREF_JS  = ["app.js","main.js","bundle.js","script.js"]
IMG_EXTS = [".png",".jpg",".jpeg",".gif",".svg",".webp"]

def pick(static_dir: Path, exts, prefs=()):
    if not static_dir or not static_dir.exists(): return None
    files = [p for p in static_dir.rglob("*") if p.suffix.lower() in exts]
    if not files: return None
    # أفضّل أسماء بعينها
    for name in prefs:
        for p in files:
            if p.name.lower()==name: return p
    # وإلا أقصر مسار
    files.sort(key=lambda p:(len(p.parts), p.name.lower()))
    return files[0]

def rel(static_dir: Path, p: Path):
    return str(p.relative_to(static_dir).as_posix())

# أنماط عامة لالتقاط أي شكل من filename='\1' مع اقتباسات مهربة أو عادية
BACKREF_TOKENS = [
    "filename='\\1'", 'filename="\\1"',
    r"filename=\'\1\'", r'filename=\"\1\"',
]

def fix_file(html: Path, static_dir: Path):
    s = html.read_text(encoding="utf-8", errors="ignore")
    o = s

    css = pick(static_dir, exts={".css"}, prefs=PREF_CSS)
    js  = pick(static_dir, exts={".js"},  prefs=PREF_JS)
    img = pick(static_dir, exts=set(IMG_EXTS), prefs=())

    # 1) خصّص حسب الوسم: <link ... href=...> ⟶ CSS
    if any(tok in s for tok in BACKREF_TOKENS):
        if css:
            css_rel = rel(static_dir, css)
            # link rel=stylesheet
            s = re.sub(
                r'href="\{\{\s*url_for\(\s*[\'\\"]static[\'\\"]\s*,\s*filename\s*=\s*[\'\\"]\\?\\?1[\'\\"]\s*\)\s*\}\}"',
                f'href="{{{{ url_for(\'static\', filename=\'{css_rel}\') }}}}"',
                s
            )
            s = re.sub(
                r"href='\{\{\s*url_for\(\s*[\'\\\"]static[\'\\\"]\s*,\s*filename\s*=\s*[\'\\\"]\\?\\?1[\'\\\"]\s*\)\s*\}\}'",
                f"href='{{{{ url_for('static', filename='{css_rel}') }}}}'",
                s
            )
        if js:
            js_rel = rel(static_dir, js)
            # <script src=...>
            s = re.sub(
                r'src="\{\{\s*url_for\(\s*[\'\\"]static[\'\\"]\s*,\s*filename\s*=\s*[\'\\"]\\?\\?1[\'\\"]\s*\)\s*\}\}"',
                f'src="{{{{ url_for(\'static\', filename=\'{js_rel}\') }}}}"',
                s
            )
            s = re.sub(
                r"src='\{\{\s*url_for\(\s*[\'\\\"]static[\'\\\"]\s*,\s*filename\s*=\s*[\'\\\"]\\?\\?1[\'\\\"]\s*\)\s*\}\}'",
                f"src='{{{{ url_for('static', filename='{js_rel}') }}}}'",
                s
            )
        if img:
            img_rel = rel(static_dir, img)
            # <img src=...> (كـ fallback إن بقت \1)
            s = re.sub(
                r'(<img[^>]+src=)"\{\{\s*url_for\(\s*[\'\\"]static[\'\\"]\s*,\s*filename\s*=\s*[\'\\"]\\?\\?1[\'\\"]\s*\)\s*\}\}"',
                r'\1"{{ url_for(\'static\', filename=\'' + img_rel + r'\') }}"',
                s, flags=re.IGNORECASE
            )

        # 2) أي بقايا عامة لـ \1 داخل url_for … استبدال احتياطي بـ CSS أو JS
        if "\\1" in s or r"\'\1\'" in s or r'\"\1\"' in s:
            if css:
                css_rel = rel(static_dir, css)
                for tok in BACKREF_TOKENS:
                    s = s.replace(tok, f"filename='{css_rel}'")
            elif js:
                js_rel = rel(static_dir, js)
                for tok in BACKREF_TOKENS:
                    s = s.replace(tok, f"filename='{js_rel}'")

    if s != o:
        html.write_text(s, encoding="utf-8")
        print(f"[fixed] {html}")
        return True
    return False

def main():
    any_fixed = False
    for app_dir in APPS:
        tpl = app_dir/"templates"
        static = app_dir/"static"
        if not tpl.exists(): continue
        for f in tpl.rglob("*.html"):
            any_fixed |= fix_file(f, static if static.exists() else None)
    if not any_fixed:
        print("No occurrences fixed. افتح customers_app/templates/index.html وابعت أول 20 سطر.")
    else:
        print("Done.")

if __name__ == "__main__":
    main()
