from pathlib import Path

ROOT = Path(__file__).parent
css_paths = [
    ROOT / "customers_app" / "static" / "app.css",
    ROOT / "customers_app" / "static" / "css" / "style.css",
]

# قواعد CSS مضبوطة للشعار
logo_css = """
/* === Auto Logo Responsive Fix === */
.logo-img {
    display: block;
    margin: 0 auto 15px auto;
    max-width: 180px;   /* يمكنك تعديل القيمة هنا لو تبي تكبر أو تصغر */
    width: 100%;
    height: auto;
}
"""

for css_file in css_paths:
    if css_file.exists():
        content = css_file.read_text(encoding="utf-8")
        if "Auto Logo Responsive Fix" not in content:
            content += "\n" + logo_css
            css_file.write_text(content, encoding="utf-8")
            print(f"[+] تم تحديث ملف CSS: {css_file}")
    else:
        css_file.parent.mkdir(parents=True, exist_ok=True)
        css_file.write_text(logo_css, encoding="utf-8")
        print(f"[+] تم إنشاء ملف CSS جديد: {css_file}")

# تحديث القالب لإضافة class للشعار
tpl = ROOT / "customers_app" / "templates" / "index.html"
if tpl.exists():
    s = tpl.read_text(encoding="utf-8")
    import re
    s = re.sub(
        r'<img([^>]*)>',
        r'<img class="logo-img"\1>',
        s,
        count=1,
        flags=re.IGNORECASE
    )
    tpl.write_text(s, encoding="utf-8")
    print("[+] تم ضبط وسم الشعار في القالب")

print("✅ تم ضبط حجم وموضع الشعار تلقائيًا")
