from pathlib import Path
import re

index_path = Path("customers_app/templates/index.html")

# الكود الجديد بحجم مضبوط (220px)
style_block = """
  <style>
    .logo {
      width: 220px !important;
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto 20px auto !important;
    }
  </style>
"""

if not index_path.exists():
    print(f"❌ الملف غير موجود: {index_path}")
else:
    content = index_path.read_text(encoding="utf-8")

    # نحذف أي كود style سابق يخص logo-img أو logo
    content = re.sub(r"<style>.*?</style>", "", content, flags=re.DOTALL)

    # نحقن الكود قبل أول <link rel="stylesheet"...>
    new_content = re.sub(
        r'(<link\s+rel="stylesheet".*?>)',
        style_block + r'\n\1',
        content,
        count=1
    )

    index_path.write_text(new_content, encoding="utf-8")
    print("✅ تم تصغير الشعار وضبط التنسيق بنجاح.")
