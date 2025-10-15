from wsgi import application
from werkzeug.serving import run_simple
if __name__ == "__main__":
    port = 8000
    print(f"Serving on http://localhost:{port}")
    run_simple("0.0.0.0", port, application, use_reloader=True, use_debugger=True)
