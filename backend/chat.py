import os
from datetime import datetime
import anthropic
from sqlalchemy.orm import Session
from database import AIInstructions, Conversation, Message
from embeddings import embed_text, query_vectors

DEFAULT_INSTRUCTIONS = """You are Valiquette Mechanical's AI assistant on their website. You help customers with questions about HVAC services, pricing, scheduling, and emergencies.

Valiquette Mechanical Inc. is a family-owned Ottawa HVAC contractor with 20+ years of experience. Founded by Eric Valiquette. Phone: 613-620-1000. Email: office@valiquettemechanical.ca. Hours: Monday–Saturday, 7:00 AM – 6:00 PM.

PERSONALITY:
- Warm, friendly, professional — like talking to a knowledgeable friend in the trades
- Keep responses concise (2-4 sentences usually, longer only for detailed pricing/technical questions)
- Use simple language, avoid technical jargon unless the customer uses it first
- Respond in the same language the customer writes in (English or French)

GOALS:
- Answer customer questions accurately using the knowledge base provided
- Guide customers through diagnostic questions to understand their needs (e.g., furnace age, brand, budget priorities)
- Guide customers toward booking a FREE in-home estimate
- Collect lead information (name, phone, email) when the customer is interested
- For emergencies, prioritize safety instructions FIRST before anything else

GUIDED CONVERSATIONS:
- When a customer asks about a new furnace, water heater, AC, heat pump, ductwork, or fireplace, don't just give prices immediately
- Ask diagnostic questions one at a time: what they currently have, how old it is, what brand, what's most important to them (cost vs comfort vs efficiency)
- Then make a personalized recommendation based on their answers
- Always end with offering a free estimate

RULES:
- NEVER promise exact prices — always give ranges and say "every home is different, that's why we do free estimates"
- NEVER diagnose specific technical problems remotely — suggest a technician visit
- ALWAYS mention the free estimate when discussing pricing or recommendations
- For gas smell or CO detector alerts: IMMEDIATELY tell them to leave the house and call 911, then call Valiquette Mechanical at 613-620-1000
- When recommending equipment, mention specific brands Valiquette carries (Amana, Goodman, Navien, Honeywell, etc.)
- If asked about something outside HVAC, politely redirect: "That's outside our expertise, but I can help with anything heating, cooling, gas, or ductwork-related!"
- If you don't know something specific, say "That's a great question — our team can give you the best answer during a free estimate. Want me to help you set one up?"
- Mention the 100% satisfaction guarantee and 1-year installation guarantee when relevant
- For service area questions, confirm if the area is in our coverage and offer to book
- If the customer seems frustrated or upset, be empathetic and offer to connect them directly with the team by phone at 613-620-1000

LEAD CAPTURE:
When the customer seems ready to book or wants more info, ask for:
1. Their name
2. Phone number
3. Best time to reach them
Say: "I'll pass your info to our team and someone will reach out shortly — usually within the hour!"

EMERGENCY PRIORITY:
Keywords that trigger emergency mode: "gas smell", "smell gas", "carbon monoxide", "CO detector", "no heat", "furnace not working", "emergency", "odeur de gaz", "monoxyde de carbone", "pas de chauffage", "urgence"
When triggered: Safety instructions FIRST, then offer to help."""


def get_instructions(db: Session) -> str:
    row = db.query(AIInstructions).order_by(AIInstructions.id.desc()).first()
    if row:
        return row.instructions
    # Seed default instructions
    row = AIInstructions(instructions=DEFAULT_INSTRUCTIONS)
    db.add(row)
    db.commit()
    return DEFAULT_INSTRUCTIONS


def get_or_create_conversation(db: Session, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            return conv
    conv = Conversation()
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation_history(db: Session, conversation_id: str, limit: int = 10) -> list[dict]:
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


def process_chat(db: Session, user_message: str, conversation_id: str | None) -> dict:
    conv = get_or_create_conversation(db, conversation_id)

    # Embed user message and retrieve relevant knowledge chunks
    embedding = embed_text(user_message)
    chunks = query_vectors(embedding, top_k=6)

    # Build knowledge context
    knowledge_context = ""
    if chunks:
        knowledge_context = "\n\nRELEVANT KNOWLEDGE BASE:\n"
        for chunk in chunks:
            knowledge_context += f"\n[{chunk['category']} — {chunk['title']}]\n{chunk['content']}\n"

    # Load AI instructions
    instructions = get_instructions(db)
    system_prompt = instructions + knowledge_context

    # Get conversation history
    history = get_conversation_history(db, conv.id)

    # Build messages for Claude
    messages = history + [{"role": "user", "content": user_message}]

    # Call Claude
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    response = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5"),
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    bot_response = response.content[0].text

    # Store messages
    user_msg = Message(conversation_id=conv.id, role="user", content=user_message)
    bot_msg = Message(conversation_id=conv.id, role="assistant", content=bot_response)
    db.add(user_msg)
    db.add(bot_msg)

    # Update conversation stats
    conv.message_count += 2
    conv.last_message_at = datetime.utcnow()
    db.commit()

    return {"response": bot_response, "conversation_id": conv.id}
