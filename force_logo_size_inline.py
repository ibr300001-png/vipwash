from pathlib import Path, re

p = Path("customers_app/templates/index.html")
s = p.read_text(encoding="utf-8")

# أضف/استبدل style على أول <img ... class="logo"...>
def repl(m):
    tag = m.group(0)
    if 'style=' in tag:
        # استبدل القيمة الحالية فقط
        tag = re.sub(r'style="[^"]*"', 'style="width:320px;height:auto;display:block;margin:0 auto 20px;"', tag)
    else:
        # أضف style جديد قبل >
        tag = tag.replace('>', ' style="width:320px;height:auto;display:block;margin:0 auto 20px;">', 1)
    return tag

new = re.sub(r'<img\s+[^>]*class="[^"]*\blogo\b[^"]*"[^>]*>', repl, s, count=1, flags=re.IGNORECASE)
p.write_text(new, encoding="utf-8")
print("✅ تم ضبط الشعار على 320px (فقط على وسم الصورة).")
