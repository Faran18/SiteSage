# backend/core/vector_db.py

import uuid
import numpy as np
from chromadb.utils import embedding_functions
from backend.models.database import get_db_connection
from backend.core.llm_service import clean_scraped_content

EMBEDDING_MODEL_PATH = "sentence-transformers/all-MiniLM-L6-v2"

sentence_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_PATH
)

# ── Semantic small-talk detection ────────────────────────────────────
# A handful of example phrases, embedded once at startup, instead of a
# regex list that needs a manual edit for every new way someone can say
# "hi". Reuses the same local embedding model already loaded above for
# retrieval - no extra API call, no extra model to load.
_SMALL_TALK_EXAMPLES = [
    "hi",
    "hello there",
    "hey, how are you doing",
    "what's up",
    "good morning",
    "yo what's good",
    "howdy",
    "thanks a lot",
    "thank you so much",
    "bye, see you later",
    "goodbye",
]
_small_talk_embeddings = np.array(sentence_ef(_SMALL_TALK_EXAMPLES))


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def is_semantically_small_talk(query: str, threshold: float = 0.75) -> bool:
    """
    True if `query` is semantically close to one of the example small-talk
    phrases above. Catches paraphrases and new phrasings the old hardcoded
    regex list would've missed, without editing code for each new variant.
    """
    query_embedding = np.array(sentence_ef([query])[0])
    similarities = [_cosine_similarity(query_embedding, ex) for ex in _small_talk_embeddings]
    return max(similarities) >= threshold


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 50) -> list[str]:
    """
    Chunk text intelligently by sentences to avoid word breaks.
    (Unchanged from the ChromaDB version - chunking logic has nothing to
    do with where the vectors get stored.)
    """
    if not text or len(text) < chunk_size:
        return [text] if text else []

    # Split by newlines first to preserve structure
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph would exceed chunk size
        if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(current_chunk.strip())

            # Start new chunk with some overlap (last 50 chars from previous chunk)
            if overlap > 0 and len(current_chunk) > overlap:
                overlap_text = current_chunk[-overlap:].strip()
                # Find the start of the last complete word
                space_idx = overlap_text.find(' ')
                if space_idx > 0:
                    overlap_text = overlap_text[space_idx:].strip()
                current_chunk = overlap_text + " " + para
            else:
                current_chunk = para
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += " " + para
            else:
                current_chunk = para

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Filter out very short chunks (less than 50 chars)
    chunks = [c for c in chunks if len(c) >= 50]

    return chunks


def _to_pgvector(embedding) -> str:
    """
    psycopg2 doesn't know how to adapt a Python list/ndarray to pgvector's
    `vector` type on its own - it needs to be sent as a string like
    "[0.1,0.2,...]" and cast with ::vector in the SQL itself.
    """
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


def store_scraped_data(agent_id: str, url: str, text: str,
                       css_selector: str = None, xpath: str = None):
    """Clean, chunk, embed, and store scraped data in the agent_chunks table."""

    scrape_id = str(uuid.uuid4())

    # Hard ceiling per scrape, independent of how clean the content is.
    # Even perfectly legitimate content (a huge product catalog, a page
    # nobody flagged as "noisy") could otherwise blow past Supabase's
    # 500MB pgvector cap on its own - noise filtering fixes content
    # QUALITY, this fixes content QUANTITY. ~100k chars is roughly a long
    # article's worth of real content; anything past that gets truncated,
    # not rejected, so a scrape never fails outright because of size.
    MAX_SCRAPE_CHARS = 100_000
    if len(text) > MAX_SCRAPE_CHARS:
        print(f"⚠️ Scraped content ({len(text)} chars) exceeds the {MAX_SCRAPE_CHARS}-char cap - truncating")
        text = text[:MAX_SCRAPE_CHARS]

    # Clean before chunking, not after - removes boilerplate/citation noise
    # at the source instead of trying to filter it back out of chunks at
    # chat time. See core/llm_service.py: clean_scraped_content().
    text = clean_scraped_content(text)

    chunks = chunk_text(text, chunk_size=600, overlap=50)

    print(f"📦 Created {len(chunks)} chunks from {len(text)} characters")

    if not chunks:
        return {
            "status": "stored",
            "agent_id": agent_id,
            "collection_name": f"agent_{agent_id}",
            "scrape_id": scrape_id,
            "url": url,
            "chunks": 0,
            "chars": len(text),
            "preview": text[:200] + "..." if text else ""
        }

    embeddings = sentence_ef(chunks)  # one 384-dim vector per chunk

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Replace, don't accumulate: delete this agent's previous batch
        # before inserting the new one. Without this, every re-scrape
        # (e.g. the daily auto-scrape) would pile up a full duplicate
        # batch on top of the last one forever - that unbounded growth,
        # not inactive agents, is the real threat to the 500MB cap.
        cursor.execute("DELETE FROM agent_chunks WHERE agent_id = %s", (agent_id,))

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{agent_id}_{scrape_id}_chunk_{i}"
            cursor.execute("""
                INSERT INTO agent_chunks
                    (chunk_id, agent_id, scrape_id, source_url, chunk_index,
                     total_chunks, css_selector, xpath, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            """, (
                chunk_id, agent_id, scrape_id, url, i, len(chunks),
                css_selector or "", xpath or "", chunk, _to_pgvector(embedding)
            ))
        conn.commit()

    print(f"✅ Stored {len(chunks)} chunks for agent {agent_id}")

    return {
        "status": "stored",
        "agent_id": agent_id,
        "collection_name": f"agent_{agent_id}",  # kept for response-shape compatibility
        "scrape_id": scrape_id,
        "url": url,
        "chunks": len(chunks),
        "chars": len(text),
        "preview": text[:200] + "..."
    }


def query_similar(agent_id: str, text_query: str, top_k: int = 5):
    """
    Find the top_k chunks closest to text_query for this agent, using
    pgvector's cosine distance operator (<=>).

    Returns the same nested-list shape ChromaDB used to return, so
    process.py (and anything else reading retrieval["documents"][0], etc.)
    didn't need to change at all.
    """
    query_embedding = _to_pgvector(sentence_ef([text_query])[0])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chunk_id, content, source_url, chunk_index, total_chunks,
                   css_selector, xpath, embedding <=> %s::vector AS distance
            FROM agent_chunks
            WHERE agent_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, agent_id, query_embedding, top_k))
        rows = cursor.fetchall()

    if not rows:
        print(f"⚠️ No data found for agent {agent_id}")
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "ids": [[]]
        }

    documents = [r["content"] for r in rows]
    metadatas = [
        {
            "agent_id": agent_id,
            "source_url": r["source_url"],
            "chunk_index": r["chunk_index"],
            "total_chunks": r["total_chunks"],
            "css_selector": r["css_selector"],
            "xpath": r["xpath"],
        }
        for r in rows
    ]
    distances = [r["distance"] for r in rows]
    ids = [r["chunk_id"] for r in rows]

    print(f"🔍 Query results for agent {agent_id}:")
    print(f"   Query: '{text_query}'")
    print(f"   Found: {len(documents)} results")
    for i, meta in enumerate(metadatas):
        print(f"   - Chunk {meta['chunk_index']}: {documents[i][:100]}...")

    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
        "ids": [ids]
    }


def get_latest_chunk_text(agent_id: str) -> str:
    """
    Returns the oldest stored chunk's text for an agent. Used by the
    scheduler to compare old vs new content when checking for site
    changes (replaces the old collection.get(limit=1) ChromaDB call).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content FROM agent_chunks
            WHERE agent_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (agent_id,))
        row = cursor.fetchone()

    return row["content"] if row else ""


def get_agent_stats(agent_id: str):
    """Get statistics about an agent's stored data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM agent_chunks WHERE agent_id = %s",
            (agent_id,)
        )
        total_chunks = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT DISTINCT source_url FROM agent_chunks WHERE agent_id = %s",
            (agent_id,)
        )
        urls = [r["source_url"] for r in cursor.fetchall() if r["source_url"]]

    return {
        "agent_id": agent_id,
        "collection_name": f"agent_{agent_id}",
        "total_chunks": total_chunks,
        "unique_urls": len(urls),
        "urls": urls
    }


def clear_agent_data(agent_id: str) -> bool:
    """Clear all stored chunks for an agent."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_chunks WHERE agent_id = %s", (agent_id,))
            deleted = cursor.rowcount
            conn.commit()
        print(f"✅ Cleared {deleted} chunks from agent {agent_id}")
        return True
    except Exception as e:
        print(f"❌ Error clearing agent data: {e}")
        return False


def list_agent_collections():
    """List all agents that have stored chunks, with a per-agent count."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT agent_id, COUNT(*) as count
            FROM agent_chunks
            GROUP BY agent_id
        """)
        rows = cursor.fetchall()

    return [
        {"name": f"agent_{r['agent_id']}", "agent_id": r["agent_id"], "count": r["count"]}
        for r in rows
    ]


def delete_agent_collection(agent_id: str):
    """Delete all stored chunks for an agent (called when an agent is deleted)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_chunks WHERE agent_id = %s", (agent_id,))
            conn.commit()
    except Exception:
        pass


def delete_expired_chunks(max_age_days: int = 10) -> int:
    """
    Deletes ALL chunks older than max_age_days, no exceptions - including
    an agent's current/only batch if it's old enough. Supabase's free tier
    caps storage at 500MB.

    This means an agent that hasn't been re-scraped within max_age_days
    loses its entire knowledge base until the next scrape runs (the bot
    will answer "I don't have specific information about that" in the
    meantime). That's intentional per the current requirement, not a bug -
    if you want the current batch protected from this regardless of age,
    that's a different function (an earlier version of this one did that).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM agent_chunks WHERE created_at < NOW() - make_interval(days => %s)",
            (max_age_days,)
        )
        deleted = cursor.rowcount
        conn.commit()

    if deleted:
        print(f"🗑️ Deleted {deleted} chunks older than {max_age_days} days")

    return deleted