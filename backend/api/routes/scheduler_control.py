# backend/api/routes/scheduler_control.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.core.scheduler import schedule_scrape_config, get_scheduled_jobs
from backend.models.agent import ScrapeConfig, Agent
from backend.models.user import User
from backend.core.auth import get_current_user

router = APIRouter()


class ScheduleConfigRequest(BaseModel):
    """Request to schedule/reschedule a config"""
    config_id: str


@router.post("/scheduler/add")
def add_to_scheduler(data: ScheduleConfigRequest, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Manually add a scrape config to scheduler"""
    try:
        config = ScrapeConfig.get_by_id(data.config_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        # ✅ Trace config -> agent -> owner, then check ownership
        agent = Agent.get_by_id(config.agent_id)
        if not agent or agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not config.auto_scrape:
            raise HTTPException(
                status_code=400, 
                detail="Config must have auto_scrape enabled"
            )
        
        schedule_scrape_config(config)
        
        return {
            "message": "Config added to scheduler",
            "config": config.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/jobs")
def list_scheduled_jobs(user: User = Depends(get_current_user)):  # ✅ Require auth
    """Get all scheduled jobs"""
    try:
        jobs = get_scheduled_jobs()
        
        return {
            "count": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
def scheduler_status(user: User = Depends(get_current_user)):  # ✅ Require auth
    """Check if scheduler is running"""
    from backend.core.scheduler import scheduler
    
    return {
        "running": scheduler.running,
        "jobs_count": len(scheduler.get_jobs())
    }