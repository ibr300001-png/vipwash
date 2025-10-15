# fix_all_static_paths.py
# يصلّح جميع روابط الصور وملفات CSS/JS في كل القوالب تلقائياً

from pathlib import Path
import re

ROOT = Path(__file__).parent
TEMPLATE_DIRS = [
    ROOT / "customers_app" / "templates",
    ROOT / "vipwash_client_only" / "templates",
]

def fix_html(file_path: Path):
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    original = text

    # إصلاح الروابط القديمة أو المكسورة
    text = re.sub(r'src=["\'](Logo|logo)["\']', r'src="{{ url_for(\'static\', filename=\'img/logo.png\') }}"', text, flags=re.IGNORECASE)

    # إصلاح أي \1 متبقية
    text = text.replace("\\1", "img/logo.png").replace("\\", "/")

    # إصلاح روابط CSS القديمة
    text = re.sub(r'href="/static/([^"]+)"', r'href="{{ url_for(\'static\', filename=\'\1\') }}"', text)
    text = re.sub(r'src="/static/([^"]+)"', r'src="{{ url_for(\'static\', filename=\'\1\') }}"', text)

    if text != original:
        file_path.write_text(text, encoding="utf-8")
        print(f"[fixed] {file_path}")

def run():
    for tdir in TEMPLATE_DIRS:
        if not tdir.exists():
            continue
        for html_file in tdir.rglob("*.html"):
            fix_html(html_file)
    print("✅ تم إصلاح جميع القوالب بنجاح")

if __name__ == "__main__":
    run()
