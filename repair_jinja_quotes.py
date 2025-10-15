# repair_jinja_quotes.py
# يزيل \ قبل ' و " داخل تعابير Jinja {{ ... }} و {% ... %} في جميع قوالب العملاء
from pathlib import Path
import re

ROOT = Path(__file__).parent
TPL_DIRS = [
    ROOT/"customers_app"/"templates",
    ROOT/"vipwash_client_only"/"templates",
]

# نمطان لالتقاط كتل Jinja
JINJA_EXPR = re.compile(r"\{\{\s*.*?\s*\}\}", re.DOTALL)
JINJA_STMT = re.compile(r"\{\%\s*.*?\s*\%\}", re.DOTALL)

def unescape_in_blocks(text: str) -> str:
    def _fix_block(m):
        block = m.group(0)
        # داخل الكتلة فقط: \' -> ' و \" -> "
        fixed = block.replace(r"\'", "'").replace(r'\"', '"')
        return fixed
    text = JINJA_EXPR.sub(_fix_block, text)
    text = JINJA_STMT.sub(_fix_block, text)
    return text

def run():
    changed_any = False
    for d in TPL_DIRS:
        if not d.exists(): continue
        for f in d.rglob("*.html"):
            s = f.read_text(encoding="utf-8", errors="ignore")
            o = s
            s = unescape_in_blocks(s)
            # علاوة على ذلك: صلح url_for لو بقى مسار static خاطئ
            s = re.sub(r'href="/static/([^"]+)"',  r'href="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)
            s = re.sub(r'src="/static/([^"]+)"',   r'src="{{ url_for(\'static\', filename=\'\g<1>\') }}"', s)
            if s != o:
                f.write_text(s, encoding="utf-8")
                print(f"[fixed] {f}")
                changed_any = True
    if not changed_any:
        print("No changes were necessary.")
    else:
        print("All done.")
if __name__ == "__main__":
    run()
