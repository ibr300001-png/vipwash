# fix_images_all.py
# يصلّح كل مراجع الصور داخل القوالب:
#  - اكتشاف مسار الشعار تلقائيًا (customers_app/static أو vipwash_client_only/static)
#  - توحيد <img ... src=...> ليستخدم url_for('static', filename='...') الصحيح
#  - إزالة أي اقتباسات مُهربة داخل تعابير Jinja

from pathlib import Path
import re

ROOT = Path(__file__).parent
APP_DIRS = [
    ROOT / "customers_app",
    ROOT / "vipwash_client_only",
]

IMG_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
LOGO_CAND = [
    "img/logo.png","logo.png","logo.jpg","logo.jpeg","logo.svg","logo.webp",
    "img/brand.png","brand.png","branding.png","mark.png","icon.png"
]
PREF_LOGO_PREFIX = ("logo", "brand")

def find_logo(static_dir: Path):
    if not static_dir.exists():
        return None
    # 1) أسماء شائعة
    for rel in LOGO_CAND:
        p = static_dir / rel
        if p.exists():
            return p
    # 2) أي ملف يبدأ بـ logo/brand
    cands = [p for p in static_dir.rglob("*") if p.suffix.lower() in IMG_EXTS]
    for p in cands:
        n = p.name.lower()
        if n.startswith(PREF_LOGO_PREFIX) or "logo" in n or "brand" in n:
            return p
    # 3) fallback أول صورة
    return cands[0] if cands else None

def rel_from_static(static_dir: Path, file_path: Path):
    return str(file_path.relative_to(static_dir).as_posix())

# داخل كتل Jinja فقط: الغِ \ قبل ' و "
JINJA_EXPR = re.compile(r"\{\{\s*.*?\s*\}\}", re.DOTALL)
JINJA_STMT = re.compile(r"\{\%\s*.*?\s*\%\}", re.DOTALL)
def unescape_jinja(text: str) -> str:
    def _fix(m):
        t = m.group(0)
        return t.replace(r"\'", "'").replace(r'\"', '"')
    return JINJA_STMT.sub(_fix, JINJA_EXPR.sub(_fix, text))

def fix_template(html_path: Path, static_dir: Path, logo_rel: str):
    s = html_path.read_text(encoding="utf-8", errors="ignore")
    o = s

    # 0) نظّف اقتباسات جينجا المهرّبة
    s = unescape_jinja(s)

    # 1) حوّل أي /static/... إلى url_for صحيح
    s = re.sub(r'src="/static/([^"]+)"',  r'src="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)
    s = re.sub(r'href="/static/([^"]+)"', r'href="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)

    # 2) الحالات المعطوبة التي تحتوي \1
    for tok in ["filename='\\1'", 'filename="\\1"', r"filename=\'\1\'", r'filename=\"\1\"']:
        if tok in s:
            s = s.replace(tok, f"filename='{logo_rel}'")

    # 3) ثبّت الشعار: أي <img> يحمل logo/id/class/alt أو src فارغ/كلمة Logo/#
    #    اجعله يشير لملف الشعار المكتشف
    logo_pat = re.compile(
        r'(<img\b[^>]*?(?:class="[^"]*\blogo\b[^"]*"|id="logo"|alt="logo"|alt="Logo"|src="(?:#|Logo|logo|)")'
        r'[^>]*?\bsrc=)"[^"]*"',
        re.IGNORECASE
    )
    s = logo_pat.sub(r'\1"{{ url_for(\'static\', filename=\'' + logo_rel + r'\') }}"', s)

    # 4) صور بدون url_for لكن ليست مطلقة: src="img/..." -> url_for
    s = re.sub(r'src="(img/[^"]+)"',
               r'src="{{ url_for(\'static\', filename=\'\1\') }}"', s)

    if s != o:
        html_path.write_text(s, encoding="utf-8")
        print(f"[fixed] {html_path}")
        return True
    return False

def main():
    changed = False
    for app_dir in APP_DIRS:
        tpl = app_dir / "templates"
        static = app_dir / "static"
        if not tpl.exists() or not static.exists():
            continue
        logo = find_logo(static)
        logo_rel = rel_from_static(static, logo) if logo else None
        if logo_rel:
            print(f"[logo] {app_dir.name}: using static '{logo_rel}'")
        else:
            print(f"[logo] {app_dir.name}: no image found under static — سأُصلح الروابط العامة فقط.")
        for f in tpl.rglob("*.html"):
            changed |= fix_template(f, static, logo_rel or "")
    if not changed:
        print("No changes needed.")
    else:
        print("[OK] templates updated.")

if __name__ == "__main__":
    main()
