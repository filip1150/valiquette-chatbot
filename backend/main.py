import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database import (
    get_db, init_db,
    AIInstructions, KnowledgeEntry, Conversation, Message, Lead,
)
from chat import process_chat, get_instructions, DEFAULT_INSTRUCTIONS
from knowledge_base import get_all_entries, create_entry, update_entry, delete_entry, sync_from_pinecone
from embeddings import save_instructions_to_pinecone

app = FastAPI(title="Valiquette Mechanical Chat API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "valiquette-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str = Depends(lambda: None)) -> str:
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    raise HTTPException(status_code=401, detail="Not authenticated")


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/api/admin/login")
def login(req: LoginRequest):
    admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip()
    admin_pass = os.environ.get("ADMIN_PASSWORD", "valiquette2024").strip()
    if req.username != admin_user or req.password != admin_pass:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(req.username)}


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@app.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    result = process_chat(db, req.message, req.conversation_id)
    return result


@app.get("/api/widget/config")
def widget_config():
    return {
        "greeting": "Hi! I'm the Valiquette Mechanical assistant. How can I help you today?",
        "suggestions": [
            "I need a new furnace",
            "Emergency — no heat!",
            "Book a free estimate",
            "Do you service my area?",
        ],
        "theme": {
            "primaryColor": "#1557A0",
            "headerText": "Valiquette Mechanical",
            "subText": "Answers in seconds, 24/7",
        },
    }


# ─── Admin — Knowledge Base ───────────────────────────────────────────────────

class KnowledgeEntryCreate(BaseModel):
    category: str
    title: str
    content: str


class KnowledgeEntryUpdate(BaseModel):
    category: str
    title: str
    content: str


@app.get("/api/admin/knowledge-base")
def list_knowledge(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    entries = get_all_entries(db)
    return [
        {
            "id": e.id,
            "category": e.category,
            "title": e.title,
            "content": e.content,
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
        }
        for e in entries
    ]


@app.post("/api/admin/knowledge-base", status_code=201)
def add_knowledge(req: KnowledgeEntryCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    entry = create_entry(db, req.category, req.title, req.content)
    return {"id": entry.id, "category": entry.category, "title": entry.title, "content": entry.content}


@app.put("/api/admin/knowledge-base/{entry_id}")
def edit_knowledge(entry_id: str, req: KnowledgeEntryUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    entry = update_entry(db, entry_id, req.category, req.title, req.content)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"id": entry.id, "category": entry.category, "title": entry.title, "content": entry.content}


@app.delete("/api/admin/knowledge-base/{entry_id}")
def remove_knowledge(entry_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    ok = delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True}


@app.post("/api/admin/knowledge-base/sync")
def sync_knowledge(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    count = sync_from_pinecone(db, force=True)
    return {"ok": True, "synced": count}


# ─── Admin — AI Instructions ─────────────────────────────────────────────────

class InstructionsUpdate(BaseModel):
    instructions: str


@app.get("/api/admin/instructions")
def get_ai_instructions(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    row = db.query(AIInstructions).order_by(AIInstructions.id.desc()).first()
    if not row:
        return {"instructions": DEFAULT_INSTRUCTIONS, "updated_at": None}
    return {"instructions": row.instructions, "updated_at": row.updated_at.isoformat()}


@app.put("/api/admin/instructions")
def update_ai_instructions(req: InstructionsUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    row = db.query(AIInstructions).order_by(AIInstructions.id.desc()).first()
    if row:
        row.instructions = req.instructions
        row.updated_at = datetime.utcnow()
    else:
        row = AIInstructions(instructions=req.instructions)
        db.add(row)
    db.commit()
    save_instructions_to_pinecone(req.instructions)  # persist so cold starts restore correctly
    return {"ok": True, "updated_at": row.updated_at.isoformat()}


# ─── Admin — Conversations ────────────────────────────────────────────────────

@app.get("/api/admin/conversations")
def list_conversations(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    offset = (page - 1) * limit
    total = db.query(Conversation).count()
    convs = db.query(Conversation).order_by(Conversation.last_message_at.desc()).offset(offset).limit(limit).all()
    result = []
    for c in convs:
        first_msg = db.query(Message).filter(Message.conversation_id == c.id, Message.role == "user").first()
        result.append({
            "id": c.id,
            "started_at": c.started_at.isoformat(),
            "last_message_at": c.last_message_at.isoformat(),
            "message_count": c.message_count,
            "flagged": c.flagged,
            "preview": (first_msg.content[:100] if first_msg else ""),
        })
    return {"total": total, "page": page, "limit": limit, "conversations": result}


@app.get("/api/admin/conversations/{conv_id}")
def get_conversation(conv_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp).all()
    return {
        "id": conv.id,
        "started_at": conv.started_at.isoformat(),
        "last_message_at": conv.last_message_at.isoformat(),
        "message_count": conv.message_count,
        "flagged": conv.flagged,
        "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in msgs],
    }


@app.put("/api/admin/conversations/{conv_id}/flag")
def flag_conversation(conv_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.flagged = not conv.flagged
    db.commit()
    return {"flagged": conv.flagged}


@app.delete("/api/admin/conversations/{conv_id}")
def delete_conversation(conv_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.query(Message).filter(Message.conversation_id == conv_id).delete()
    db.delete(conv)
    db.commit()
    return {"ok": True}


# ─── Admin — Leads ────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    address: str | None = None
    service_needed: str | None = None
    conversation_id: str | None = None


class LeadStatusUpdate(BaseModel):
    status: str


@app.get("/api/admin/leads")
def list_leads(
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    total = query.count()
    leads = query.order_by(Lead.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "leads": [
            {
                "id": l.id,
                "name": l.name,
                "phone": l.phone,
                "email": l.email,
                "address": l.address,
                "service_needed": l.service_needed,
                "status": l.status,
                "conversation_id": l.conversation_id,
                "created_at": l.created_at.isoformat(),
            }
            for l in leads
        ],
    }


@app.post("/api/admin/leads", status_code=201)
def create_lead(req: LeadCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    lead = Lead(**req.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"id": lead.id}


@app.put("/api/admin/leads/{lead_id}")
def update_lead_status(lead_id: int, req: LeadStatusUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    valid_statuses = {"new", "contacted", "booked", "closed"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")
    lead.status = req.status
    db.commit()
    return {"ok": True}


# ─── Admin — Stats ────────────────────────────────────────────────────────────

@app.get("/api/admin/stats")
def get_stats(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    total_convs = db.query(Conversation).count()
    today_convs = db.query(Conversation).filter(Conversation.started_at >= today_start).count()
    total_leads = db.query(Lead).count()
    uncontacted = db.query(Lead).filter(Lead.status == "new").count()
    week_leads = db.query(Lead).filter(Lead.created_at >= week_start).count()
    month_leads = db.query(Lead).filter(Lead.created_at >= month_start).count()
    kb_count = db.query(KnowledgeEntry).count()

    return {
        "total_conversations": total_convs,
        "today_conversations": today_convs,
        "total_leads": total_leads,
        "uncontacted_leads": uncontacted,
        "this_week_leads": week_leads,
        "this_month_leads": month_leads,
        "knowledge_base_count": kb_count,
    }


# ─── Booking endpoint (public — no auth required) ─────────────────────────────

class BookingRequest(BaseModel):
    name: str
    phone: str
    email: str | None = None
    service_needed: str | None = None
    preferred_time: str | None = None
    notes: str | None = None
    conversation_id: str | None = None


def send_booking_email(req: BookingRequest):
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    to_email = os.environ.get("FEEDBACK_EMAIL", "filip1150@gmail.com")
    if not resend_key:
        return
    try:
        import resend as resend_lib
        resend_lib.api_key = resend_key.strip()
        body = f"""NEW BOOKING REQUEST — Valiquette Mechanical Chatbot

Name:           {req.name}
Phone:          {req.phone}
Email:          {req.email or '—'}
Service:        {req.service_needed or '—'}
Preferred time: {req.preferred_time or '—'}
Notes:          {req.notes or '—'}
Conversation:   {req.conversation_id or '—'}
Time:           {datetime.utcnow().isoformat()} UTC
"""
        params: resend_lib.Emails.SendParams = {
            "from": os.environ.get("FEEDBACK_FROM", "Valiquette Mechanical <onboarding@resend.dev>"),
            "to": [to_email],
            "subject": f"[Valiquette] New Booking Request — {req.name} — {req.phone}",
            "text": body,
        }
        resend_lib.Emails.send(params)
    except Exception as e:
        print(f"Booking email failed: {e}")


@app.post("/api/book")
def book_appointment(req: BookingRequest, db: Session = Depends(get_db)):
    lead = Lead(
        name=req.name,
        phone=req.phone,
        email=req.email,
        service_needed=req.service_needed,
        conversation_id=req.conversation_id,
    )
    db.add(lead)
    db.commit()
    send_booking_email(req)
    return {"ok": True}


# ─── Static Files & Pages ─────────────────────────────────────────────────────

PUBLIC_DIR = BASE_DIR / "public"
widget_dir = PUBLIC_DIR / "widget" if (PUBLIC_DIR / "widget").exists() else BASE_DIR / "widget"
admin_dir = PUBLIC_DIR / "admin" if (PUBLIC_DIR / "admin").exists() else BASE_DIR / "admin"

if widget_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(widget_dir)), name="widget")

if admin_dir.exists():
    app.mount("/admin-static", StaticFiles(directory=str(admin_dir)), name="admin-static")

if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


@app.get("/admin", response_class=FileResponse)
def admin_page():
    return str(admin_dir / "index.html")


@app.get("/", response_class=FileResponse)
def index_page():
    idx = PUBLIC_DIR / "index.html"
    if idx.exists():
        return str(idx)
    from fastapi.responses import JSONResponse
    return JSONResponse({"status": "ok", "service": "Valiquette Mechanical Chat API"})


@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
