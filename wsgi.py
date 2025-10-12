bash -lc '
set -e
cd /opt/render/project/src

echo "==> Sync repo"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
  git remote add origin https://github.com/ibr300001-png/vipwash.git
fi
git fetch origin main
git reset --hard origin/main

echo "==> Write wsgi.py (clients=/ , admin=/admin)"
cat > wsgi.py << "PY"
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix
from customers_app.app import app as client_app
from vipwash_admin_app.app import app as admin_app
client_app = ProxyFix(client_app, x_for=1, x_proto=1, x_host=1, x_port=1)
admin_app  = ProxyFix(admin_app,  x_for=1, x_proto=1, x_host=1, x_port=1)
app = DispatcherMiddleware(client_app, {"/admin": admin_app})
PY

echo "==> Install deps"
python -m pip install --no-cache-dir -r requirements.txt || true

echo "==> Restart"
sv restart web 2>/dev/null || true
sleep 2

echo "==> Quick check"
curl -I http://localhost:$PORT/            || true   # clients: 200/302
curl -I http://localhost:$PORT/admin/      || true   # admin: 200
curl -I http://localhost:$PORT/admin/login || true   # 200 أو 302
'
