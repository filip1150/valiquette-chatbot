import uuid
from sqlalchemy.orm import Session
from database import KnowledgeEntry, AIInstructions
from embeddings import embed_text, upsert_vector, delete_vector, list_all_vectors, save_instructions_to_pinecone, fetch_instructions_from_pinecone


def sync_from_pinecone(db: Session, force: bool = False) -> int:
    """Repopulate SQLite from Pinecone. On cold start runs only when empty; force=True always re-syncs."""
    if not force:
        existing = db.query(KnowledgeEntry).count()
        if existing > 0:
            return existing
    vectors = list_all_vectors()
    # Delete entries no longer in Pinecone
    pinecone_ids = {v["id"] for v in vectors if v.get("title") and v.get("content")}
    db.query(KnowledgeEntry).filter(~KnowledgeEntry.id.in_(pinecone_ids)).delete(synchronize_session=False)
    for v in vectors:
        if not v.get("title") or not v.get("content"):
            continue
        entry = KnowledgeEntry(
            id=v["id"],
            category=v.get("category", "General"),
            title=v["title"],
            content=v["content"],
        )
        db.merge(entry)
    db.commit()

    # Restore AI instructions from Pinecone if SQLite has none
    if db.query(AIInstructions).count() == 0:
        text = fetch_instructions_from_pinecone()
        if text:
            db.add(AIInstructions(instructions=text))
            db.commit()

    return len(vectors)


def get_all_entries(db: Session) -> list[KnowledgeEntry]:
    return db.query(KnowledgeEntry).order_by(KnowledgeEntry.category, KnowledgeEntry.title).all()


def get_entry(db: Session, entry_id: str) -> KnowledgeEntry | None:
    return db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()


def create_entry(db: Session, category: str, title: str, content: str) -> KnowledgeEntry:
    entry_id = str(uuid.uuid4())
    embedding = embed_text(content)
    upsert_vector(entry_id, embedding, {"category": category, "title": title, "content": content})
    entry = KnowledgeEntry(id=entry_id, category=category, title=title, content=content)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, entry_id: str, category: str, title: str, content: str) -> KnowledgeEntry | None:
    entry = get_entry(db, entry_id)
    if not entry:
        return None
    embedding = embed_text(content)
    upsert_vector(entry_id, embedding, {"category": category, "title": title, "content": content})
    entry.category = category
    entry.title = title
    entry.content = content
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry_id: str) -> bool:
    entry = get_entry(db, entry_id)
    if not entry:
        return False
    delete_vector(entry_id)
    db.delete(entry)
    db.commit()
    return True
