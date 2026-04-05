import os
from openai import OpenAI
from pinecone import Pinecone

_openai_client = None
_pinecone_index = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
    return _openai_client


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"].strip())
        _pinecone_index = pc.Index(os.environ.get("PINECONE_INDEX", "gasman-chatbot").strip())
    return _pinecone_index


def embed_text(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def upsert_vector(vector_id: str, embedding: list[float], metadata: dict):
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman")
    index.upsert(vectors=[{"id": vector_id, "values": embedding, "metadata": metadata}], namespace=namespace)


def delete_vector(vector_id: str):
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman")
    index.delete(ids=[vector_id], namespace=namespace)


INSTRUCTIONS_VECTOR_ID = "__gasman_instructions__"


def save_instructions_to_pinecone(text: str):
    """Persist AI instructions in Pinecone so they survive Vercel cold starts."""
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman").strip()
    # Use a near-zero vector -- we never query this by similarity, only fetch by ID
    dim = 1536  # text-embedding-3-small dimension
    index.upsert(
        vectors=[{"id": INSTRUCTIONS_VECTOR_ID, "values": [0.0001] + [0.0] * (dim - 1), "metadata": {"instructions": text, "_type": "instructions"}}],
        namespace=namespace,
    )


def fetch_instructions_from_pinecone() -> str | None:
    """Retrieve AI instructions stored in Pinecone. Returns None if not found."""
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman").strip()
    try:
        result = index.fetch(ids=[INSTRUCTIONS_VECTOR_ID], namespace=namespace)
        vec = result.vectors.get(INSTRUCTIONS_VECTOR_ID)
        if vec and vec.metadata:
            return vec.metadata.get("instructions")
    except Exception:
        pass
    return None


def list_all_vectors() -> list[dict]:
    """Fetch all vectors from Pinecone (used to resync SQLite on cold start)."""
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman").strip()
    try:
        all_ids = [vid for page in index.list(namespace=namespace) for vid in page]
        if not all_ids:
            return []
        fetched = index.fetch(ids=all_ids, namespace=namespace)
        results = []
        for vid, vec in fetched.vectors.items():
            m = vec.metadata or {}
            if m.get("_type") == "instructions":
                continue  # skip the instructions sentinel vector
            results.append({
                "id": vid,
                "category": m.get("category", ""),
                "title": m.get("title", ""),
                "content": m.get("content", ""),
            })
        return results
    except Exception:
        return []


def query_vectors(embedding: list[float], top_k: int = 6) -> list[dict]:
    index = get_pinecone_index()
    namespace = os.environ.get("PINECONE_NAMESPACE", "gasman")
    results = index.query(vector=embedding, top_k=top_k, include_metadata=True, namespace=namespace)
    return [
        {
            "id": match["id"],
            "score": match["score"],
            "category": match["metadata"].get("category", ""),
            "title": match["metadata"].get("title", ""),
            "content": match["metadata"].get("content", ""),
        }
        for match in results["matches"]
    ]
