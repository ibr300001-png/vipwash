# set_logo.py — يكتشف ملف اللوقو ويثبّت مساره في القوالب
from pathlib import Path
import re

ROOT = Path(__file__).parent
APP_DIRS = [ROOT/"customers_app", ROOT/"vipwash_client_only"]

# أسماء مرشحة للّوقو
CAND_NAMES = [
    "logo.png","logo.jpg","logo.jpeg","logo.svg","logo.webp",
    "brand.png","brand.svg","branding.png","mark.png","icon.png"
]
IMG_EXTS = {".png",".jpg",".jpeg",".svg",".webp"}

def pick_logo(static: Path):
    if not static or not static.exists(): return None
    # 1) أسماء مطابقة مباشرة
    for name in CAND_NAMES:
        p = static / name
        if p.exists(): return p
    # 2) أي ملف يبدأ بـ logo أو فيه logo
    files = [p for p in static.rglob("*") if p.suffix.lower() in IMG_EXTS]
    for p in files:
        n = p.name.lower()
        if n.startswith("logo") or "logo" in n or n.startswith("brand"):
            return p
    # 3) fallback: أول صورة
    return files[0] if files else None

def rel_from_static(static: Path, p: Path):
    return str(p.relative_to(static).as_posix())

def fix_templates(tpl_dir: Path, static_dir: Path, logo_rel: str):
    changed = False
    if not tpl_dir.exists(): return False
    for f in tpl_dir.rglob("*.html"):
        s = f.read_text(encoding="utf-8", errors="ignore"); o = s
        # أنماط شائعة للّوقو داخل <img>:
        # - class="logo"
        # - id="logo"
        # - alt="Logo" أو "logo"
        # - أي src كان مطلق/مكسور
        s = re.sub(
            r'(<img[^>]*?(?:class="[^"]*\blogo\b[^"]*"|id="logo"|alt="logo"|"Logo")[^>]*?src=)"[^"]*"',
            r'\1"{{ url_for(\'static\', filename=\'' + logo_rel + r'\') }}"',
            s, flags=re.IGNORECASE
        )
        # لو بقي أي <img ... src="{{ url_for('static', filename='\1') }}"
        s = s.replace("filename='\\1'", f"filename='{logo_rel}'")

        if s != o:
            f.write_text(s, encoding="utf-8"); changed = True; print(f"[fixed] {f}")
    return changed

def main():
    any_change = False
    for app in APP_DIRS:
        static = app/"static"
        tpl    = app/"templates"
        logo = pick_logo(static)
        if not logo:
            print(f"[warn] لا توجد صورة لوقو في: {static}"); continue
        rel = rel_from_static(static, logo)
        print(f"[logo] using {logo}  ->  static filename='{rel}'")
        any_change |= fix_templates(tpl, static, rel)
    if not any_change:
        print("No logo references updated. قد يكون القالب يستخدم CSS background أو اسم مختلف—نقدر نضبطه لو أرسلت سطر <img> من القالب.")
    else:
        print("[OK] Logo references updated.")
if __name__ == "__main__":
    main()
