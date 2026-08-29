# backend/api/routes/process.py

import re
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from better_profanity import profanity
from backend.core.vector_db import query_similar, is_semantically_small_talk
from backend.core.llm_service import run_chat, moderate_message
from backend.models.agent import Agent, ScrapeConfig
from backend.models.conversation import Conversation, Message
from backend.models.user import User
from backend.core.auth import get_current_user
from backend.core.limiter import limiter

router = APIRouter()

profanity.load_censor_words()


def is_abusive(query: str) -> bool:
    """
    True if the message contains profanity/slurs (fast wordlist check,
    checked first since it's free and instant) or is flagged unsafe by
    Llama Guard (catches what the wordlist misses — veiled harassment,
    threats, misspellings designed to dodge a wordlist).
    """
    if profanity.contains_profanity(query):
        return True
    return moderate_message(query)


# Common small-talk openers that don't need the knowledge base searched at all
_SMALL_TALK_PATTERNS = [
    r"^(hi|hello|hey|hola|yo|sup|howdy|greetings)(\s+(there|friend|guys|everyone|folks))?[\s!.,]*$",
    r"^good (morning|afternoon|evening|day)[\s!.,]*$",
    r"^(how are you|how's it going|what's up)[\s?!.,]*$",
    r"^(thanks|thank you|thx|ty)[\s!.,]*$",
    r"^(bye|goodbye|see you|see ya)[\s!.,]*$",
]
_SMALL_TALK_RE = re.compile("|".join(_SMALL_TALK_PATTERNS), re.IGNORECASE)


def is_small_talk(query: str) -> bool:
    """
    True if the message is pure small talk with no real question in it.
    Checks the literal regex first (free, instant), then falls back to a
    semantic check for phrasings the regex doesn't cover.
    """
    query = query.strip()
    if _SMALL_TALK_RE.match(query):
        return True
    return is_semantically_small_talk(query)


class ProcessRequest(BaseModel):
    """Request body for chat/query endpoint"""
    agent_id: str
    query: str


@router.post("/process")
@limiter.limit("10/minute")
def process_data(request: Request, data: ProcessRequest, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Chat with an agent using its knowledge base."""
    try:
        agent = Agent.get_by_id(data.agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent not found: {data.agent_id}"
            )
        
        # ✅ Check ownership — this agent must belong to the caller
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        print(f"💬 Chat with agent: {agent.name}")
        print(f"👤 User query: '{data.query}'")
        
        # Get agent's primary scrape config for URL info
        primary_config = ScrapeConfig.get_primary(data.agent_id)
        source_url = primary_config.url if primary_config else "Unknown source"

        conversation_id = Conversation.get_or_create_for_agent(agent.agent_id)

        # ── Abuse / profanity short-circuit ──────────────────────────
        if is_abusive(data.query):
            print("🚫 Offensive language detected — declining to engage")

            boundary_message = (
                f"I'm happy to help you find a car, but I'm not able to "
                f"continue if the conversation includes offensive language. "
                f"Let me know the make, model, or year you're interested in "
                f"and I'll pull up what's available."
            )

            Message.add(conversation_id, "user", data.query)
            Message.add(conversation_id, "assistant", boundary_message)

            return {
                "message": boundary_message,
                "agent_name": agent.name,
                "source_url": source_url,
                "chunks_used": 0
            }

        # ── Small talk short-circuit ─────────────────────────────────
        # A bare "hello" doesn't need the knowledge base searched — doing
        # so just forces ChromaDB to return 5 weakly-relevant chunks (it
        # always returns top_k results even when nothing truly matches),
        # which then pollutes the prompt and can produce odd, off-topic
        # replies. Skip retrieval entirely for pure small talk.
        if is_small_talk(data.query):
            print("💡 Small talk detected — skipping knowledge base search")

            greeting_system_prompt = f"""You are "{agent.name}", acting as a {agent.role}.
Stay in character as a {agent.role} in tone and manner.

The user just sent a casual greeting or small talk with no specific
question. Reply naturally and briefly (1-2 sentences) as {agent.role}
would, and invite them to ask about the available inventory/content.
Do not invent any specific details, prices, or listings — you have no
inventory context loaded for this reply."""

            # Note: deliberately NOT including conversation history here.
            # A greeting should always get a clean, fresh reply — pulling
            # in old turns (e.g. an earlier question about the system
            # prompt) is exactly what caused "hello" to return unrelated
            # meta-answers before.
            messages = [
                {"role": "system", "content": greeting_system_prompt},
                {"role": "user", "content": data.query},
            ]

            response_text = run_chat(messages, max_new_tokens=150)

            if response_text and response_text.strip():
                Message.add(conversation_id, "user", data.query)
                Message.add(conversation_id, "assistant", response_text.strip())

            return {
                "message": response_text.strip() if response_text else f"Hi! I'm {agent.name}. Ask me anything about our listings.",
                "agent_name": agent.name,
                "source_url": source_url,
                "chunks_used": 0
            }

        # Search agent's knowledge base
        retrieval = query_similar(
            agent_id=data.agent_id,  
            text_query=data.query,
            top_k=5
        )
        
        if not retrieval.get("documents") or not retrieval["documents"][0]:
            return {
                "message": "I don't have specific information about that in my knowledge base. Could you ask something else?",
                "agent_name": agent.name,
                "source_url": source_url,
                "chunks_used": 0
            }
        
        # Filter useful chunks
        useful_chunks = []
        for chunk in retrieval["documents"][0]:
            if len(chunk) < 100:
                continue
            
            lowercase = chunk.lower()
            noise_indicators = ['copyright', 'powered by', 'quick links', 'follow us', 
                               'privacy policy', 'terms & condition', 'whatsapp us']
            
            if any(indicator in lowercase for indicator in noise_indicators):
                continue
            
            useful_chunks.append(chunk)
        
        if not useful_chunks:
            useful_chunks = retrieval["documents"][0][:2]
        
        context = "\n\n".join(useful_chunks[:5])
        chunks_used = len(useful_chunks[:5])
        
        print(f"📚 Using {chunks_used} chunks")
        print(f"📄 Context length: {len(context)} chars")

        # ── Conversation memory ──────────────────────────────────────
        history = Message.get_recent(conversation_id, limit=6)  # last 3 exchanges

        # ── Role-aware system prompt ─────────────────────────────────
        system_prompt = f"""You are "{agent.name}", acting as a {agent.role}.
Stay in character as a {agent.role} in tone and manner for the whole conversation.

Answer the user's questions using ONLY the CONTEXT provided below and, when
relevant, earlier turns in this conversation. Never make up information that
isn't present in the context.

CONTEXT:
{context[:3000]}

RULES:
1. Use ONLY information from the CONTEXT above (and prior conversation turns for continuity).
2. Answer in 2-3 clear, concise sentences unless the user asks for more detail.
3. If the answer is not in the context, say: "I don't have that information in the provided content."
4. Do NOT make assumptions or add information not in the context.
5. Be helpful, direct, and consistent with your role as a {agent.role}."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": data.query})

        print(f"🤖 Generating response...")
        response_text = run_chat(messages, max_new_tokens=800)
        
        # ✅ CRITICAL: Ensure response is valid
        if not response_text or len(response_text.strip()) == 0:
            print("⚠️ Empty response from LLM!")
            return {
                "message": "I'm having trouble generating a response. Please try rephrasing your question.",
                "agent_name": agent.name,
                "source_url": source_url,
                "chunks_used": chunks_used
            }
        
        # Check for error messages
        if response_text.startswith("Error:") or response_text.startswith("❌"):
            print(f"⚠️ LLM error: {response_text}")
            return {
                "message": "Sorry, I encountered an error generating a response. Please try again.",
                "agent_name": agent.name,
                "source_url": source_url,
                "chunks_used": chunks_used
            }
        
        print(f"📤 Response: '{response_text[:100]}...'")
        print(f"✅ Response generated")

        # Save this turn so future messages have memory of it
        Message.add(conversation_id, "user", data.query)
        Message.add(conversation_id, "assistant", response_text.strip())

        # Return response with all required fields
        return {
            "message": response_text.strip(),
            "agent_name": agent.name,
            "source_url": source_url,
            "chunks_used": chunks_used
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Return user-friendly error instead of raising exception
        return {
            "message": "Sorry, I encountered an error. Please try again.",
            "agent_name": "Assistant",
            "source_url": "",
            "chunks_used": 0
        }


@router.post("/agents/{agent_id}/chat/reset")
def reset_conversation(agent_id: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """
    Start a fresh conversation with an agent — wipes stored history so old
    turns (e.g. earlier probing questions) never leak into future replies.
    """
    try:
        agent = Agent.get_by_id(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # ✅ Check ownership
        if agent.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        Conversation.clear_for_agent(agent_id)
        print(f"🧹 Cleared conversation history for agent: {agent.name}")

        return {"message": "Conversation reset. Starting fresh."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/chat")
@limiter.limit("10/minute")
def chat_with_agent(request: Request, agent_id: str, query: str, user: User = Depends(get_current_user)):  # ✅ Require auth
    """Simplified chat endpoint."""
    try:
        return process_data(request, ProcessRequest(
            agent_id=agent_id,
            query=query
        ), user=user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))