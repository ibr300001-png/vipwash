from werkzeug.middleware.proxy_fix import ProxyFix
from __wsgi_detect_admin__ import app as _A
from __wsgi_detect_client__ import app as _C

A = ProxyFix(_A, x_for=1, x_proto=1, x_host=1, x_port=1)
C = ProxyFix(_C, x_for=1, x_proto=1, x_host=1, x_port=1)
P = "/client"

def _sub(app, e, s, p):
    n = e.copy()
    q = n.get("PATH_INFO","") or "/"
    n["PATH_INFO"]   = q[len(p):] or "/"
    n["SCRIPT_NAME"] = (n.get("SCRIPT_NAME","") + p).rstrip("/")
    return app(n, s)

def application(e, s):
    p = e.get("PATH_INFO","") or "/"
    if p == "/healthz":
        s("200 OK",[("Content-Type","text/plain; charset=utf-8")]); return [b"ok"]
    if p == P:
        s("302 Found",[("Location", P + "/")]); return [b""]
    if p.startswith(P + "/"):
        return _sub(C, e, s, P)
    return A(e, s)

app = application
