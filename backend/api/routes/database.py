# backend/api/routes/database.py

from fastapi import APIRouter, HTTPException, Depends
from backend.models.database import get_db_connection
from backend.core.vector_db import list_agent_collections, get_agent_stats
from backend.models.agent import Agent
from backend.models.user import User
from backend.core.auth import get_current_user

router = APIRouter()


@router.get("/database/stats")
def get_database_stats(user: User = Depends(get_current_user)):  # ✅ Require auth
    """
    Get overall statistics about the system.
    
    Returns:
        - Total agents count
        - Active/inactive breakdown
        - ChromaDB collections info
    
    Example Response:
    {
        "sqlite": {
            "total_agents": 5,
            "active": 3,
            "inactive": 2
        },
        "chromadb": {
            "total_collections": 5,
            "collections": [...]
        }
    }
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total agents
            cursor.execute("SELECT COUNT(*) as count FROM agents")
            total_agents = cursor.fetchone()["count"]
            
            # Active agents
            cursor.execute("SELECT COUNT(*) as count FROM agents WHERE status = 'active'")
            active_agents = cursor.fetchone()["count"]
            
            # Inactive agents
            cursor.execute("SELECT COUNT(*) as count FROM agents WHERE status = 'inactive'")
            inactive_agents = cursor.fetchone()["count"]
        
        # ChromaDB collections
        collections = list_agent_collections()
        
        return {
            "sqlite": {
                "total_agents": total_agents,
                "active": active_agents,
                "inactive": inactive_agents
            },
            "chromadb": {
                "total_collections": len(collections),
                "collections": collections
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/agent/{agent_id}/stats")
def get_agent_database_stats(agent_id: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """
    Get detailed statistics for a specific agent's data.
    
    Example Response:
    {
        "agent_id": "abc123",
        "collection_name": "agent_abc123",
        "total_chunks": 42,
        "unique_urls": 1,
        "urls": ["https://example.com"]
    }
    """
    try:
        agent = Agent.get_by_id(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        stats = get_agent_stats(agent_id)
        
        if stats["total_chunks"] == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for agent {agent_id}"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/health")
def database_health_check():
    """
    Quick health check for database connections.
    Intentionally left PUBLIC (no auth) so uptime-monitoring bots can ping it
    without needing credentials. It only reports healthy/unhealthy status,
    no user data, so this is safe to leave open.

    Returns:
        Status of SQLite and ChromaDB connections
    """
    health = {
        "sqlite": "unknown",
        "chromadb": "unknown"
    }
    
    # Check SQLite
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            health["sqlite"] = "healthy"
    except Exception as e:
        health["sqlite"] = f"error: {str(e)}"
    
    # Check ChromaDB
    try:
        collections = list_agent_collections()
        health["chromadb"] = "healthy"
    except Exception as e:
        health["chromadb"] = f"error: {str(e)}"
    
    return health