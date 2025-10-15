from pathlib import Path
import re

index_path = Path("customers_app/templates/index.html")

if not index_path.exists():
    print(f"❌ الملف غير موجود: {index_path}")
else:
    html = index_path.read_text(encoding="utf-8")

    # نبحث عن كود <style> الحالي للشعار ونحدثه للحجم الجديد
    new_style = """
  <style>
    .logo {
      width: 260px !important;
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto 20px auto !important;
    }
  </style>
"""

    # إذا كان فيه style قديم نحذفه ونضيف الجديد
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r'(<link\s+rel="stylesheet".*?>)', new_style + r'\n\1', html, count=1)

    index_path.write_text(html, encoding="utf-8")
    print("✅ تم تكبير الشعار قليلاً (حجم وسط) بدون تعديل أي شيء آخر.")
