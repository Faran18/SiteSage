# backend/api/routes/agents.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.models.agent import Agent
from backend.models.user import User
from backend.core.auth import get_current_user

router = APIRouter()

class CreateAgentRequest(BaseModel):
    """Request body for creating a new agent"""
    name: str
    role: str


class UpdateAgentRequest(BaseModel):
    """Request body for updating an agent"""
    name: str | None = None
    role: str | None = None


class StatusUpdateRequest(BaseModel):
    """Request body for changing agent status"""
    status: str  


@router.post("/agents/create")
async def create_agent(data: CreateAgentRequest, user: User = Depends(get_current_user)):
    """
    Create a new agent (requires authentication).
    After creating, use /scrape to add knowledge base.
    """
    try:
        agent = Agent.create(
            user_id=user.user_id,  # ✅ Add user_id
            name=data.name,
            role=data.role
        )
        
        print(f"✅ Created agent: {agent.agent_id} - {agent.name} (user: {user.email})")

        # Nothing to pre-create in pgvector - rows just get inserted into
        # agent_chunks once /scrape actually runs for this agent.

        return {
            "message": "Agent created successfully",
            "agent": agent.to_dict(),
            "next_step": "Use POST /api/scrape to add knowledge from URLs"
        }
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/list")
def list_agents(
    status: str | None = None,
    user: User = Depends(get_current_user)  # ✅ Require auth
):
    """Get list of user's agents"""
    try:
        agents = Agent.get_all(status=status, user_id=user.user_id)  # ✅ Filter by user
        return {
            "count": len(agents),
            "agents": [agent.to_dict() for agent in agents]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Get agent details with scrape configs"""
    try:
        agent = Agent.get_by_id(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get scrape configs
        from backend.models.agent import ScrapeConfig
        configs = ScrapeConfig.get_by_agent(agent_id)
        
        return {
            "agent": agent.to_dict(),
            "scrape_configs": [c.to_dict() for c in configs]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/agents/{agent_id}")
def update_agent(
    agent_id: str, 
    data: UpdateAgentRequest,
    user: User = Depends(get_current_user)  # ✅ Require auth
):
    """Update agent details"""
    try:
        agent = Agent.get_by_id(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        updates = {}
        if data.name is not None:
            updates['name'] = data.name
        if data.role is not None:
            updates['role'] = data.role
        
        agent.update(**updates)
        
        return {
            "message": "Agent updated successfully",
            "agent": agent.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/agents/{agent_id}/status")
def update_agent_status(
    agent_id: str, 
    data: StatusUpdateRequest,
    user: User = Depends(get_current_user)  # ✅ Require auth
):
    """Update agent status"""
    try:
        if data.status not in ['active', 'inactive']:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'active' or 'inactive'"
            )
        
        agent = Agent.get_by_id(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        agent.update(status=data.status)
        
        return {
            "message": f"Agent {data.status}d successfully",
            "agent": agent.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Delete agent and all its data"""
    try:
        agent = Agent.get_by_id(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete from Postgres (cascades to scrape_configs, and
        # Agent.delete() internally clears the agent's vector chunks too)
        success = Agent.delete(agent_id)
        
        if success:
            return {
                "message": "Agent deleted successfully",
                "deleted_agent_id": agent_id
            }
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))