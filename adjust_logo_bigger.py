from pathlib import Path

ROOT = Path(__file__).parent
css_paths = [
    ROOT / "customers_app" / "static" / "app.css",
    ROOT / "customers_app" / "static" / "css" / "style.css",
]

# نضبط الحجم على 280px
new_css = """
/* === Logo Size Adjusted (280px) === */
.logo-img {
    max-width: 280px !important;
    height: auto;
    display: block;
    margin: 0 auto 15px auto;
}
"""

for css_file in css_paths:
    if css_file.exists():
        content = css_file.read_text(encoding="utf-8")
        lines = [line for line in content.splitlines() if "logo-img" not in line]
        lines.append(new_css)
        css_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"[+] تم تحديث حجم الشعار في: {css_file}")
    else:
        css_file.parent.mkdir(parents=True, exist_ok=True)
        css_file.write_text(new_css, encoding="utf-8")
        print(f"[+] تم إنشاء ملف CSS جديد: {css_file}")

print("✅ تم تكبير الشعار إلى 280px")
