import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_error = None

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    from backend.database import init_db, SessionLocal, AIInstructions, KnowledgeEntry, Conversation, Message, Lead
    init_db()
    _step = "database ok"
except Exception as e:
    _error = ("database", traceback.format_exc())

if not _error:
    try:
        from backend.embeddings import embed_text, query_vectors, upsert_vector, delete_vector
        _step = "embeddings ok"
    except Exception as e:
        _error = ("embeddings", traceback.format_exc())

if not _error:
    try:
        from backend.chat import process_chat, get_instructions
        _step = "chat ok"
    except Exception as e:
        _error = ("chat", traceback.format_exc())

if not _error:
    try:
        from backend.main import app as fastapi_app
        from a2wsgi import ASGIMiddleware
        app = ASGIMiddleware(fastapi_app)
        _step = "all ok"
    except Exception as e:
        _error = ("main", traceback.format_exc())

if _error:
    _msg = json.dumps({"failed_at": _error[0], "detail": _error[1]})
    def app(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "application/json")])
        return [_msg.encode()]
