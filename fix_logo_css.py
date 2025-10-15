from pathlib import Path

ROOT = Path(__file__).parent
css_files = [
    ROOT / "customers_app" / "static" / "app.css",
    ROOT / "customers_app" / "static" / "css" / "style.css",
]

css_rule = """
/* === Auto Logo Size Fix === */
img {
    max-width: 120px;
    height: auto;
    display: block;
    margin: 0 auto 10px auto;
}
"""

for css_file in css_files:
    if css_file.exists():
        content = css_file.read_text(encoding="utf-8")
        if "Auto Logo Size Fix" not in content:
            content += "\n" + css_rule
            css_file.write_text(content, encoding="utf-8")
            print(f"[+] تم تحديث ملف CSS: {css_file}")
    else:
        # إذا الملف مو موجود ننشئ واحد جديد
        css_file.parent.mkdir(parents=True, exist_ok=True)
        css_file.write_text(css_rule, encoding="utf-8")
        print(f"[+] تم إنشاء ملف CSS جديد: {css_file}")

print("✅ تم إصلاح حجم الشعار")
