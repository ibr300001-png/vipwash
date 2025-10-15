import os
from pathlib import Path

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "customers_app" / "static"

# كود CSS لضبط الشعار
css_rule = """
/* Force logo size */
.logo-img {
    width: 400px !important;
    max-width: 100% !important;
    height: auto !important;
    display: block;
    margin: 0 auto 25px auto !important;
}
"""

# مر على كل ملفات css وعدلها / أضف الكود
for css_file in STATIC_DIR.rglob("*.css"):
    text = css_file.read_text(encoding="utf-8", errors="ignore")
    # احذف أي كود سابق متعلق بالشعار
    lines = [l for l in text.splitlines() if ".logo-img" not in l]
    lines.append(css_rule)
    css_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Updated: {css_file}")

print("✅ تم تعديل جميع ملفات CSS لعرض الشعار بحجم 400px.")
