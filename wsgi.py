from werkzeug.middleware.proxy_fix import ProxyFix
from vipwash_admin_app.app import app as application
app = ProxyFix(application, x_for=1, x_proto=1, x_host=1, x_port=1)