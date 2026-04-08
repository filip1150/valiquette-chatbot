import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

import os as _os

_db_url = _os.environ.get("POSTGRES_URL") or _os.environ.get("DATABASE_URL")
if _db_url:
    import ssl as _ssl, re as _re
    # Strip query string (sslmode etc) -- pg8000 handles SSL via connect_args
    _db_url = _re.sub(r'\?.*$', '', _db_url)
    _db_url = _db_url.replace("postgres://", "postgresql+pg8000://").replace("postgresql://", "postgresql+pg8000://")
    _ssl_ctx = _ssl.create_default_context()
    engine = create_engine(_db_url, connect_args={"ssl_context": _ssl_ctx})
else:
    _sqlite_path = "sqlite:////tmp/valiquette.db" if _os.environ.get("VERCEL") else "sqlite:///./valiquette.db"
    engine = create_engine(_sqlite_path, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_uuid():
    return str(uuid.uuid4())


class AIInstructions(Base):
    __tablename__ = "ai_instructions"
    id = Column(Integer, primary_key=True, index=True)
    instructions = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id = Column(String, primary_key=True, default=new_uuid)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=new_uuid)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    message_count = Column(Integer, default=0)
    flagged = Column(Boolean, default=False)
    messages = relationship("Message", back_populates="conversation", order_by="Message.timestamp")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String)
    address = Column(String)
    service_needed = Column(String)
    status = Column(String, default="new")  # new, contacted, booked, closed
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
