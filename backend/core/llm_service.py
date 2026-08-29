# backend/core/llm_service.py

from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ========================================
# GROQ CONFIGURATION
# ========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "openai/gpt-oss-120b"  
MODERATION_MODEL = "openai/gpt-oss-safeguard-20b"

if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY not found in environment variables!")
    print("   Please add it to your .env file")
else:
    print(f"✅ Groq API key loaded")
    print(f"🤖 Using model: {MODEL_NAME}")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)


# ========================================
# CONTENT MODERATION FUNCTION
# ========================================

# gpt-oss-safeguard is a "bring your own policy" model — it reasons against
# whatever policy you give it and returns structured JSON, rather than a
# fixed built-in taxonomy like Llama Guard had.
_MODERATION_POLICY = """# Abusive Language Policy

## INSTRUCTIONS
Classify whether the user message below is abusive, hateful, or harassing
toward the assistant or in general. This assistant is a customer-facing
car sales chatbot; it should not engage with users who are being hostile.

## DEFINITIONS
- Violation: slurs, hate speech, threats, harassment, or targeted insults.
- Not a violation: ordinary customer questions, complaints about a product
  or service, mild frustration, sarcasm, or profanity used casually and
  not directed at a person as an attack.

## CRITERIA
Return violation=1 only for slurs, hate speech, threats, or harassment.
Return violation=0 for everything else, including neutral or mildly
negative messages that are not attacks on a person or group.

## OUTPUT FORMAT
Respond with ONLY a JSON object, no other text:
{"violation": 0 or 1, "category": "<short label or 'none'>"}
"""


def moderate_message(text: str) -> bool:
    """
    Runs a single message through Groq-hosted gpt-oss-safeguard-20b using
    the abuse policy above. Catches abuse/hate speech/threats that a plain
    wordlist filter misses (misspellings, veiled harassment, context-
    dependent hostility).

    Returns True if the message is flagged a violation, False if not.
    Fails open (returns False) on any API error or unparseable response —
    a moderation-service hiccup should never block a legitimate user from
    chatting.
    """
    try:
        response = client.chat.completions.create(
            model=MODERATION_MODEL,
            messages=[
                {"role": "system", "content": _MODERATION_POLICY},
                {"role": "user", "content": text},
            ],
            reasoning_effort="low",  # simple classification — don't burn tokens reasoning
        )
        raw = response.choices[0].message.content.strip()

        # Strip a ```json ... ``` fence if the model wraps its answer in one
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        result = json.loads(raw)
        return bool(result.get("violation")) 
    except Exception as e:
        print(f"⚠️ Moderation check failed, failing open: {e}")
        return False


# ========================================
# LLM INFERENCE FUNCTION
# ========================================

def run_chat(messages: list, max_new_tokens: int = 800) -> str:
    """
    Run Groq LLM with a full multi-turn message list (system + history + latest user turn).
    Use this instead of run_llm() when you want the model to have conversation memory.

    Args:
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        max_new_tokens: Maximum tokens to generate

    Returns:
        Generated text response
    """
    try:
        print(f"🤖 Running Groq LLM ({MODEL_NAME}) with {len(messages)} messages...")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=0.3,
            top_p=0.9,
            reasoning_effort="low",  # gpt-oss-120b: keep hidden reasoning short so
                                     # it doesn't eat the whole token budget and
                                     # leave no room for the actual answer
        )

        result = response.choices[0].message.content.strip()

        # Safety net: if the model burned its whole budget on reasoning and
        # returned nothing, retry once with a larger budget before giving up.
        if not result:
            print("⚠️ Empty content on first attempt — retrying with larger token budget")
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=max_new_tokens + 400,
                temperature=0.3,
                top_p=0.9,
                reasoning_effort="low",
            )
            result = response.choices[0].message.content.strip()

        usage = response.usage
        print(f"✅ Response generated")
        print(f"   Tokens used: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")

        return result

    except Exception as e:
        error_msg = f"❌ Error during Groq API call: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


def run_llm(prompt: str, max_new_tokens: int = 500) -> str:
    """
    Run Groq LLM for text generation.
    
    Args:
        prompt: The input prompt/question with context
        max_new_tokens: Maximum tokens to generate (default: 500)
        
    Returns:
        Generated text response
    """
    
    try:
        print(f"🤖 Running Groq LLM ({MODEL_NAME})...")
        print(f"   Max tokens: {max_new_tokens}")
        print(f"   Prompt length: {len(prompt)} characters")
        
        # Call Groq API
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based ONLY on the provided context. Never make up information. If the context doesn't contain the answer, say so clearly."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_new_tokens,
            temperature=0.3,  # ✅ Groq supports temperature
            top_p=0.9,        # ✅ Groq supports top_p
        )
        
        # Extract response
        result = response.choices[0].message.content.strip()
        
        # Get usage info
        usage = response.usage
        print(f"✅ Response generated")
        print(f"   Tokens used: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")
        print(f"   Response length: {len(result)} characters")
        print(f"📄 Preview: {result[:150]}...")
        
        return result
        
    except Exception as e:
        error_msg = f"❌ Error during Groq API call: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


# ========================================
# CHAT WITH CONTEXT FUNCTION
# ========================================

def run_llm_with_context(context: str, question: str, max_tokens: int = 500) -> str:
    """
    Wrapper function that formats context and question into a proper prompt.
    
    Args:
        context: The scraped content/knowledge base
        question: User's question
        max_tokens: Maximum tokens to generate
        
    Returns:
        AI-generated answer
    """
    
    prompt = f"""Answer the following question based ONLY on the context provided below. 

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Use ONLY information from the context above
2. Answer in 2-3 clear, concise sentences
3. If the context doesn't contain the answer, respond with: "I don't have that information in the provided context."
4. Do NOT make up or infer information not in the context
5. Be direct and helpful

ANSWER:"""
    
    return run_llm(prompt, max_tokens)


# ========================================
# MODEL INFO
# ========================================

def get_model_info():
    """Get information about the Groq model"""
    
    return {
        "provider": "Groq",
        "model_name": MODEL_NAME,
        "model_type": "Llama 3.3 70B",
        "api_key_set": bool(GROQ_API_KEY),
        "max_tokens": 32768,  # Context window
        "pricing": "Free tier available",
        "features": {
            "temperature": "Supported (0-2)",
            "top_p": "Supported",
            "streaming": "Supported",
            "speed": "Very fast inference"
        }
    }


# ========================================
# TEST FUNCTION
# ========================================

def test_groq_connection():
    """Test if Groq API is working"""
    
    try:
        print("🧪 Testing Groq connection...")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": "Say 'Hello, I am working!' if you can read this."}
            ],
            max_tokens=20
        )
        
        result = response.choices[0].message.content
        print(f"✅ Groq API is working!")
        print(f"   Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Groq API test failed: {e}")
        return False


# Run test on import (optional)
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Groq LLM Service - Connection Test")
    print("="*60 + "\n")
    
    info = get_model_info()
    print(f"Model: {info['model_name']}")
    print(f"API Key Set: {info['api_key_set']}")
    print(f"Max Context: {info['max_tokens']} tokens\n")
    
    if info['api_key_set']:
        test_groq_connection()
    else:
        print("⚠️ Please set GROQ_API_KEY in your .env file")