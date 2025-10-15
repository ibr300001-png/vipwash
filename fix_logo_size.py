from pathlib import Path
import re

# مسار ملف index.html
index_path = Path("customers_app/templates/index.html")

# كود الـ style المطلوب
style_block = """
  <style>
    .logo-img {
      width: 400px !important;
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto 25px auto !important;
    }
  </style>
"""

if not index_path.exists():
    print(f"❌ الملف غير موجود: {index_path}")
else:
    content = index_path.read_text(encoding="utf-8")
    if "<style>" in content and ".logo-img" in content:
        print("✅ كود الـ style موجود بالفعل.")
    else:
        # نحقن قبل أول <link rel="stylesheet"...>
        new_content = re.sub(
            r'(<link\s+rel="stylesheet".*?>)',
            style_block + r'\n\1',
            content,
            count=1
        )
        index_path.write_text(new_content, encoding="utf-8")
        print("✅ تم حقن كود تكبير الشعار بنجاح.")
