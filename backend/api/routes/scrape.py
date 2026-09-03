# backend/api/routes/scrape.py

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, HttpUrl
import asyncio
import hashlib
from backend.utils.playwright_scraper import scrape_website, extract_text_from_html
from backend.utils.multi_page_scraper import scrape_multiple_pages
from backend.core.vector_db import store_scraped_data
from backend.models.agent import Agent, ScrapeConfig
from backend.models.user import User
from backend.core.auth import get_current_user
from backend.core.limiter import limiter
from datetime import datetime

router = APIRouter()

_scraping_in_progress: set[str] = set()

class ScrapeRequest(BaseModel):
    """Request body for scraping"""
    agent_id: str
    url: HttpUrl
    css_selector: str | None = None
    xpath: str | None = None
    multi_page: bool = False
    max_pages: int = 20
    auto_scrape: bool = False
    scrape_interval_hours: int = 24


@router.post("/scrape")
@limiter.limit("5/minute")
async def scrape_and_store(request: Request, data: ScrapeRequest, user: User = Depends(get_current_user)):  # ✅ Require auth
    """
    Scrape URL(s) and store in agent's knowledge base.
    Supports single page or multi-page crawling.
    """
    agent = Agent.get_by_id(data.agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {data.agent_id}")

    # ✅ Check ownership — only the owner can scrape into their own agent
    if agent.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # ✅ Reject a second concurrent scrape for the same agent (double-click,
    # duplicate request, another tab, etc.) instead of launching a second
    # Chromium instance alongside the first on a resource-constrained box.
    if data.agent_id in _scraping_in_progress:
        raise HTTPException(status_code=409, detail="A scrape is already running for this agent")
    _scraping_in_progress.add(data.agent_id)

    try:
        print(f"🤖 Scraping for agent: {agent.name}")
        print(f"🔗 URL: {data.url}")
        print(f"📄 Multi-page: {data.multi_page}")
        
        # Check if config exists
        existing_configs = ScrapeConfig.get_by_agent(data.agent_id)
        config_exists = any(c.url == str(data.url) for c in existing_configs)
        
        if not config_exists:
            is_primary = len(existing_configs) == 0
            config = ScrapeConfig.create(
                agent_id=data.agent_id,
                url=str(data.url),
                css_selector=data.css_selector,
                xpath=data.xpath,
                is_primary=is_primary,
                auto_scrape=data.auto_scrape,
                scrape_interval_hours=data.scrape_interval_hours
            )
            print(f"💾 Created scrape config (auto: {data.auto_scrape}, interval: {data.scrape_interval_hours}h)")
        else:
            # Update existing config
            config = next(c for c in existing_configs if c.url == str(data.url))
            config.update(
                auto_scrape=data.auto_scrape,
                scrape_interval_hours=data.scrape_interval_hours
            )
        
        # Scrape content
        if data.multi_page:
            # Multi-page crawling
            print(f"🕷️ Starting multi-page crawl (max: {data.max_pages} pages)")
            result = await asyncio.to_thread(
                scrape_multiple_pages,
                str(data.url),
                data.max_pages,
                data.css_selector,
                data.xpath
            )
            
            combined_text = "\n\n=== PAGE SEPARATOR ===\n\n".join([
                f"[{p['title']}]\n{p['text']}" for p in result['pages']
            ])
            
            print(f"✅ Scraped {result['total_pages']} pages, {result['total_chars']:,} chars")
        else:
            # Single page
            html_content = await asyncio.to_thread(scrape_website, str(data.url))
            combined_text = extract_text_from_html(
                html_content,
                css_selector=data.css_selector,
                xpath=data.xpath
            )
            print(f"📄 Extracted {len(combined_text)} characters")
        
        if not combined_text.strip():
            raise HTTPException(status_code=400, detail="No text extracted")
        
        # Calculate content hash
        content_hash = hashlib.sha256(combined_text.encode()).hexdigest()
        
        # Store in vector DB
        vector_result = store_scraped_data(
            agent_id=agent.agent_id,
            url=str(data.url),
            text=combined_text,
            css_selector=data.css_selector,
            xpath=data.xpath
        )
        
        # Update config with new hash
        config.update(last_content_hash=content_hash)
        
        # Update agent
        agent.update(
            chunks_count=vector_result["chunks"],
            last_scraped=datetime.now().isoformat()
        )
        
        print(f"✅ Scraping complete")
        
        return {
            "message": "Scraping successful",
            "agent": agent.to_dict(),
            "vector_db_result": vector_result,
            "pages_scraped": result['total_pages'] if data.multi_page else 1
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _scraping_in_progress.discard(data.agent_id)


@router.post("/scrape/refresh/{agent_id}")
@limiter.limit("5/minute")
async def refresh_agent_data(request: Request, agent_id: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Re-scrape primary URL for an agent"""
    try:
        agent = Agent.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        configs = ScrapeConfig.get_by_agent(agent_id)
        primary = next((c for c in configs if c.is_primary), None)
        
        if not primary:
            raise HTTPException(status_code=404, detail="No scrape config found")
        
        return await scrape_and_store(request, ScrapeRequest(
            agent_id=agent_id,
            url=primary.url,
            css_selector=primary.css_selector,
            xpath=primary.xpath,
            multi_page=False,
            auto_scrape=primary.auto_scrape,
            scrape_interval_hours=primary.scrape_interval_hours
        ), user=user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))