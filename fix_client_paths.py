from pathlib import Path, re

ROOT = Path(__file__).parent
TEMPLATE_DIRS = [
    ROOT / "customers_app" / "templates",
    ROOT / "vipwash_client_only" / "templates",
]

# بدّل أي href/src/action="/xxx" إلى {{ request.script_root }}/xxx
# مع استثناء /static/ لأنها تخدم من الجذر
attr = r'(?:href|src|action)'
pattern = re.compile(rf'({attr}\s*=\s*")/(?!static/)([^"]*)"', re.IGNORECASE)

def patch_file(p: Path) -> bool:
    s = p.read_text(encoding="utf-8", errors="ignore")
    o = s
    s = pattern.sub(r'\1{{ request.script_root }}/\2"', s)
    if s != o:
        p.write_text(s, encoding="utf-8")
        print(f"[patched] {p.relative_to(ROOT)}")
        return True
    return False

changed = False
for d in TEMPLATE_DIRS:
    if not d.exists(): 
        continue
    for f in d.rglob("*.html"):
        changed |= patch_file(f)

print("✅ تم تصحيح روابط القوالب." if changed else "لا تغييرات مطلوبة.")
