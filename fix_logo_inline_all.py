# fix_logo_inline_all.py
from pathlib import Path
import re

ROOT = Path(__file__).parent
TEMPLATE_DIRS = [
    ROOT / "customers_app" / "templates",
    ROOT / "vipwash_client_only" / "templates",
]

# نبحث عن أول <img> في البوكس الرئيسي ونفرض له العرض 320px
IMG_TAG = re.compile(r'<img\b[^>]*>', re.IGNORECASE)

def force_inline(tag: str) -> str:
    style_kv = 'width:320px;height:auto;display:block;margin:0 auto 20px;'
    if 'style=' in tag:
        # استبدل أي style موجود
        tag = re.sub(r'style="[^"]*"', f'style="{style_kv}"', tag, flags=re.IGNORECASE)
    else:
        # أضف style قبل >
        tag = tag[:-1] + f' style="{style_kv}">'
    return tag

def process_html(path: Path) -> bool:
    s = path.read_text(encoding="utf-8", errors="ignore")
    o = s

    # نحاول أولاً إيجاد شعار له تلميح (class=logo أو logo-img أو alt=Logo)
    hint = re.compile(r'<img\b[^>]*(class="[^"]*(\blogo-img\b|\blogo\b)[^"]*"|alt="logo"|alt="Logo")[^>]*>', re.IGNORECASE)
    m = hint.search(s)
    if not m:
        # وإلا خذ أول <img> في الصفحة (عادةً هو الشعار)
        m = IMG_TAG.search(s)
    if not m:
        return False

    old = m.group(0)
    new = force_inline(old)

    s = s[:m.start()] + new + s[m.end():]
    if s != o:
        path.write_text(s, encoding="utf-8")
        print(f"[fixed] {path}")
        print("  - before:", old.strip())
        print("  + after :", new.strip())
        return True
    return False

def main():
    changed = False
    for d in TEMPLATE_DIRS:
        if not d.exists(): 
            continue
        # استهداف index.html أولاً، ثم باقي القوالب كاحتياط
        targets = []
        idx = d / "index.html"
        if idx.exists():
            targets.append(idx)
        targets += [p for p in d.rglob("*.html") if p != idx]
        for p in targets:
            if process_html(p):
                changed = True
                break  # يكفي تعديل أول ملف رئيسي (index)
    if not changed:
        print("No <img> tag found to adjust. تأكد أننا نعدّل نفس القالب الذي يُعرض.")

if __name__ == "__main__":
    main()
