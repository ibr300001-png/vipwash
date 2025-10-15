# fix_logo_paths.py
# هذا السكربت يصلح كل روابط الصور المكسورة (خاصة الشعار) في كل القوالب

from pathlib import Path
import re

ROOT = Path(__file__).parent
TEMPLATE_DIRS = [
    ROOT / "customers_app" / "templates",
    ROOT / "vipwash_client_only" / "templates",
]

# النمط القديم أو المكسور داخل <img>
IMG_PATTERN = re.compile(r'<img[^>]+(src|href)=["\'](Logo|logo|{{[^}]+\\1[^}]+}})["\']', re.IGNORECASE)

def fix_html(file_path: Path):
    s = file_path.read_text(encoding="utf-8", errors="ignore")
    o = s

    # استبدال أي شعار مكسور بالرابط الصحيح للملف
    s = IMG_PATTERN.sub(
        '<img src="{{ url_for(\'static\', filename=\'img/logo.png\') }}" alt="Logo">',
        s
    )

    # إصلاح أي استخدام خاطئ لـ \1 في url_for
    s = s.replace("\\1", "img/logo.png")
    s = s.replace("\\", "/")

    if s != o:
        file_path.write_text(s, encoding="utf-8")
        print(f"[fixed] {file_path}")
        return True
    return False

def run():
    total_fixed = 0
    for tdir in TEMPLATE_DIRS:
        if not tdir.exists():
            continue
        for html_file in tdir.rglob("*.html"):
            if fix_html(html_file):
                total_fixed += 1
    if total_fixed == 0:
        print("✅ لا توجد روابط صور مكسورة")
    else:
        print(f"✅ تم إصلاح {total_fixed} قالب(ات) بنجاح")

if __name__ == "__main__":
    run()
