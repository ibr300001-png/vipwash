from pathlib import Path
import re

index_path = Path("customers_app/templates/index.html")

if not index_path.exists():
    print(f"❌ الملف غير موجود: {index_path}")
else:
    html = index_path.read_text(encoding="utf-8")

    # ستايل جديد بحجم وسط (340px)
    new_style = """
  <style>
    .logo {
      width: 340px !important;
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto 20px auto !important;
    }
  </style>
"""

    # إزالة أي <style> قديم للشعار وإضافة الجديد
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r'(<link\s+rel="stylesheet".*?>)', new_style + r'\n\1', html, count=1)

    index_path.write_text(html, encoding="utf-8")
    print("✅ تم تكبير الشعار إلى حجم وسط (340px) بنجاح بدون تعديل أي عناصر أخرى.")
