from pathlib import Path

ROOT = Path(__file__).parent
CSS_DIR = ROOT / "customers_app" / "static"

RULE = """
/* === Force VIP logo size (final) === */
.page-index .hero img.logo,
.page-index .hero img.logo-img,
.page-index .hero img[alt="Logo"] {
  width: 320px !important;
  max-width: none !important;
  height: auto !important;
  display: block !important;
  margin: 0 auto 20px !important;
}
"""

if not CSS_DIR.exists():
    print("❌ لم أجد customers_app/static")
else:
    changed = 0
    for css in CSS_DIR.rglob("*.css"):
        txt = css.read_text(encoding="utf-8", errors="ignore")
        if "Force VIP logo size (final)" not in txt:
            css.write_text(txt.rstrip() + "\n" + RULE, encoding="utf-8")
            changed += 1
            print(f"[+] updated: {css}")
    print(f"✅ تم حقن القاعدة في {changed} ملف CSS (إن وُجدت).")
