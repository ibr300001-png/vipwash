# force_logo_size_once.py
from pathlib import Path
import re

ROOT = Path(__file__).parent
CANDIDATES = [
    ROOT / "customers_app" / "templates" / "index.html",
    ROOT / "vipwash_client_only" / "templates" / "index.html",
]

IMG_PATTERN = re.compile(r'<img\b[^>]*>', re.IGNORECASE)

def patch_logo_tag(tag: str) -> str:
    # اجعل src فيه ?v=latest
    def bump_cache(src: str) -> str:
        if "?v=" in src:  # بدّلها دائماً بـ latest
            return re.sub(r'\?v=[^"\']*', '?v=latest', src)
        return src + '?v=latest'

    # حدّث/أضف العرض والستايل
    # 1) src
    tag = re.sub(
        r'(src\s*=\s*")([^"]+)(")',
        lambda m: m.group(1) + bump_cache(m.group(2)) + m.group(3),
        tag,
        count=1,
        flags=re.IGNORECASE
    )
    # 2) width attribute
    if re.search(r'\bwidth\s*=\s*"', tag, flags=re.IGNORECASE):
        tag = re.sub(r'\bwidth\s*=\s*"\d+"', 'width="340"', tag, flags=re.IGNORECASE)
    else:
        tag = tag.replace('>', ' width="340">', 1)
    # 3) style inline
    style_val = 'width:340px;height:auto;display:block;margin:0 auto 20px;'
    if re.search(r'\bstyle\s*=\s*"', tag, flags=re.IGNORECASE):
        tag = re.sub(r'style\s*=\s*"[^"]*"', f'style="{style_val}"', tag, flags=re.IGNORECASE)
    else:
        tag = tag.replace('>', f' style="{style_val}">', 1)
    return tag

def is_logo(tag: str) -> bool:
    # اعتبره شعار إذا:
    # - فيه class=logo / logo-img
    # - أو alt=Logo
    # - أو src فيه كلمة logo
    txt = tag.lower()
    return ('class="logo' in txt) or ('class="logo-img' in txt) or ('alt="logo' in txt) or ('src="' in txt and 'logo' in txt)

def process(path: Path) -> bool:
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8", errors="ignore")
    original = html

    # ابحث عن أول <img> مرشح للشعار
    found = None
    for m in IMG_PATTERN.finditer(html):
        tag = m.group(0)
        if is_logo(tag):
            found = (m.start(), m.end(), tag)
            break
    # لو ما لقيناه، استعمل أول <img> في الصفحة كحل أخير
    if not found:
        m = IMG_PATTERN.search(html)
        if m:
            found = (m.start(), m.end(), m.group(0))

    if not found:
        return False

    start, end, old_tag = found
    new_tag = patch_logo_tag(old_tag)
    if new_tag != old_tag:
        html = html[:start] + new_tag + html[end:]
        path.write_text(html, encoding="utf-8")
        print(f"[fixed] {path}")
        print("  - before:", old_tag.strip())
        print("  + after :", new_tag.strip())
        return True
    return False

changed_any = False
for f in CANDIDATES:
    changed_any |= process(f)

if not changed_any:
    print("No changes made. قد يكون القالب مختلفاً عن index.html — أخبرني بالمسار الذي يفتح عندك.")
else:
    print("✅ شعار العملاء مضبوط على 340px مع كسر كاش (?v=latest).")
