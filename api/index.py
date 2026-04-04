import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_import_error = None
app = None

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

    from backend.database import init_db
    from backend.main import app as fastapi_app
    from a2wsgi import ASGIMiddleware

    init_db()
    app = ASGIMiddleware(fastapi_app)

except Exception as _e:
    _import_error = traceback.format_exc()

    def app(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "application/json")])
        return [json.dumps({"error": str(_e), "detail": _import_error}).encode()]
