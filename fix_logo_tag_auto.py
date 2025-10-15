# fix_logo_tag_auto.py
# هذا السكربت يمر على جميع ملفات القوالب ويصلح وسم <img> للشعار تلقائيًا

from pathlib import Path
import re

ROOT = Path(__file__).parent
TEMPLATE_DIRS = [
    ROOT / "customers_app" / "templates",
    ROOT / "vipwash_client_only" / "templates",
]

# الوسم الصحيح الذي نريد تعويضه في كل القوالب
correct_tag = '<img src="{{ url_for(\'static\', filename=\'img/logo.png\') }}" alt="Logo">'

# أنماط مختلفة قد تكون موجودة حالياً (مكسورة)
patterns = [
    r'<img[^>]+Logo[^>]*>',
    r'<img[^>]+logo[^>]*>',
    r'<img[^>]+src=["\']\{\{[^}]+\}\}["\'][^>]*>',
    r'<img[^>]*>',
]

def fix_file(file_path: Path):
    s = file_path.read_text(encoding="utf-8", errors="ignore")
    original = s

    for pat in patterns:
        s = re.sub(pat, correct_tag, s, count=1, flags=re.IGNORECASE)
    
    if s != original:
        file_path.write_text(s, encoding="utf-8")
        print(f"[fixed] {file_path}")
        return True
    return False

def run():
    fixed_count = 0
    for tdir in TEMPLATE_DIRS:
        if not tdir.exists():
            continue
        for html_file in tdir.rglob("*.html"):
            if fix_file(html_file):
                fixed_count += 1
    print(f"✅ تم إصلاح {fixed_count} ملف(ات) قالب")

if __name__ == "__main__":
    run()
