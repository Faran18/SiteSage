# backend/core/vector_db.py

import uuid
import chromadb
from chromadb.utils import embedding_functions
from typing import Optional

VECTOR_DB_PATH = "E:/web_scraper/data/vectors"
EMBEDDING_MODEL_PATH = "sentence-transformers/all-MiniLM-L6-v2"

client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
sentence_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_PATH
)

def get_agent_collection(agent_id: str):
    """Get or create a ChromaDB collection for a specific agent."""
    collection_name = f"agent_{agent_id}"
    
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=sentence_ef,
        metadata={"agent_id": agent_id}
    )
    
    return collection


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 50) -> list[str]:
    """
    Chunk text intelligently by sentences to avoid word breaks.
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


def store_scraped_data(agent_id: str, url: str, text: str, 
                       css_selector: str = None, xpath: str = None):
    """Store scraped data with better chunking"""
    
    collection = get_agent_collection(agent_id)
    
    scrape_id = str(uuid.uuid4())
    
    # Chunk text with better algorithm
    chunks = chunk_text(text, chunk_size=600, overlap=50)
    
    print(f"📦 Created {len(chunks)} chunks from {len(text)} characters")
    
    # Generate IDs
    chunk_ids = [
        f"{agent_id}_{scrape_id}_chunk_{i}" 
        for i in range(len(chunks))
    ]
    
    metadatas = [
        {
            "agent_id": agent_id,
            "scrape_id": scrape_id,
            "source_url": url,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "css_selector": css_selector if css_selector else "",
            "xpath": xpath if xpath else "",
        }
        for i in range(len(chunks))
    ]
    
    # Add to ChromaDB
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=chunk_ids
    )
    
    print(f"✅ Stored {len(chunks)} chunks for agent {agent_id}")
    
    return {
        "status": "stored",
        "agent_id": agent_id,
        "collection_name": f"agent_{agent_id}",
        "scrape_id": scrape_id,
        "url": url,
        "chunks": len(chunks),
        "chars": len(text),
        "preview": text[:200] + "..."
    }


def query_similar(agent_id: str, text_query: str, top_k: int = 5):
    """Query with more results to ensure we don't miss content"""
    
    collection = get_agent_collection(agent_id)
    
    if collection.count() == 0:
        print(f"⚠️ No data found for agent {agent_id}")
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "ids": [[]]
        }
    
    # Query for similar documents
    results = collection.query(
        query_texts=[text_query],
        n_results=min(top_k, collection.count())
    )
    
    print(f"🔍 Query results for agent {agent_id}:")
    print(f"   Query: '{text_query}'")
    print(f"   Found: {len(results['documents'][0])} results")
    
    # Debug: Show which chunks were retrieved
    if results.get('metadatas') and results['metadatas'][0]:
        for i, meta in enumerate(results['metadatas'][0]):
            chunk_idx = meta.get('chunk_index', '?')
            print(f"   - Chunk {chunk_idx}: {results['documents'][0][i][:100]}...")
    
    return results


def get_agent_stats(agent_id: str):
    """Get statistics about an agent's stored data."""
    collection = get_agent_collection(agent_id)
    
    all_data = collection.get()
    
    unique_urls = set()
    if all_data and all_data.get("metadatas"):
        for metadata in all_data["metadatas"]:
            if "source_url" in metadata:
                unique_urls.add(metadata["source_url"])
    
    return {
        "agent_id": agent_id,
        "collection_name": f"agent_{agent_id}",
        "total_chunks": collection.count(),
        "unique_urls": len(unique_urls),
        "urls": list(unique_urls)
    }


def clear_agent_data(agent_id: str) -> bool:
    """Clear all data from an agent's collection."""
    try:
        collection = get_agent_collection(agent_id)
        
        all_data = collection.get()
        if all_data and all_data.get("ids"):
            collection.delete(ids=all_data["ids"])
            print(f"✅ Cleared {len(all_data['ids'])} chunks from agent {agent_id}")
        
        return True
    except Exception as e:
        print(f"❌ Error clearing agent data: {e}")
        return False


def list_agent_collections():
    """List all agent collections"""
    collections = client.list_collections()
    
    result = []
    for collection in collections:
        if collection.name.startswith("agent_"):
            agent_id = collection.name.replace("agent_", "")
            result.append({
                "name": collection.name,
                "agent_id": agent_id,
                "count": collection.count()
            })
    
    return result


def delete_agent_collection(agent_id: str):
    try:
        client.delete_collection(name=f"agent_{agent_id}")
    except Exception:
        pass
