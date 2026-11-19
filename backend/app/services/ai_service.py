"""
AI assistant: grounds answers in VOCHE trials and resources, applies clinical guardrails,
and calls Gemini over its REST API (httpx is already a dependency, so no SDK is added).
"""
import logging
import re
from typing import Any, Dict, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Voche AI Assistant, a multilingual guide for the Voche (Voices of Communities for Health Equity) platform, a global ecosystem focused on infectious diseases that serves patients, caregivers, Healthcare Professionals (HCPs) and Civil Society Organizations, especially in Low- and Middle-Income Countries.

Your goals:
1. Help users find clinical trials, educational resources and community forums on the platform.
2. Explain informed consent, patient rights and clinical trial processes in simple language.
3. Promote trial literacy and ethical participation in health research.

Strict rules:
- Stay neutral. Never endorse a specific trial, sponsor or unverified treatment.
- Never give medical advice, a diagnosis or a treatment recommendation. Tell users to consult their healthcare provider.
- Never ask for personal or health identifiers.
- Be concise, compassionate and clear. Use short bullet points where they help.
- When platform items are listed below, base your answer on them and refer to them by title. Do not invent trials or resources."""

DISCLAIMER = "This is general information, not medical advice. Please talk to a healthcare provider about your own health."

EMERGENCY_REPLY = (
    "It sounds like this could be an emergency. Please call your local emergency number or go to the nearest "
    "hospital now. If you are thinking about harming yourself, please contact a crisis line or someone you trust "
    "right away. I can't help with emergencies, but I'm here for questions about trials and resources afterwards."
)

EMERGENCY_PATTERN = re.compile(
    r"\b(suicid\w*|kill (my|him|her)self|end my life|self[- ]harm|overdos\w*|can'?t breathe|"
    r"cannot breathe|chest pain|heart attack|stroke|seizure|unconscious|severe bleeding|bleeding heavily)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "what", "which", "when", "where", "about", "there", "their", "would", "could", "should", "with", "from",
    "that", "this", "have", "does", "your", "trial", "trials", "study", "studies", "tell", "know", "want",
    "need", "help", "please", "find", "show", "some", "more", "into", "they", "them", "been",
    "are", "any", "the", "and", "for", "how", "can", "you", "who", "why", "its", "not", "but", "has",
    "was", "our", "all", "get", "use", "one", "out", "may", "now", "see", "did", "had", "his", "her",
}

MAX_CONTEXT_ITEMS = 3
HISTORY_LIMIT = 20


def is_emergency(text: str) -> bool:
    return bool(EMERGENCY_PATTERN.search(text))


def keywords(text: str) -> List[str]:
    # Words of 3+ letters, plus short all-caps acronyms such as TB.
    acronyms = [a.lower() for a in re.findall(r"\b[A-Z]{2}\b", text)]
    words = acronyms + re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    return list(dict.fromkeys(w for w in words if w not in STOPWORDS))[:8]


async def find_context(conn, text: str) -> List[Dict[str, Any]]:
    """RAG-lite: trials and resources whose text matches words from the user's message."""
    patterns = [f"%{w}%" for w in keywords(text)]
    if not patterns:
        return []
    trials = await conn.fetch(
        """
        SELECT trial_id AS id, title, LEFT(COALESCE(summary, ''), 300) AS snippet
        FROM clinical_trials
        WHERE (title || ' ' || COALESCE(summary, '') || ' ' || disease_area) ILIKE ANY($1::text[])
        ORDER BY last_updated DESC
        LIMIT $2
        """,
        patterns, MAX_CONTEXT_ITEMS,
    )
    resources = await conn.fetch(
        """
        SELECT resource_id AS id, title, LEFT(description, 300) AS snippet
        FROM resources
        WHERE (title || ' ' || description || ' ' || category) ILIKE ANY($1::text[])
        ORDER BY featured DESC, created_at DESC
        LIMIT $2
        """,
        patterns, MAX_CONTEXT_ITEMS,
    )
    return [{"type": "trial", **dict(r)} for r in trials] + [{"type": "resource", **dict(r)} for r in resources]


async def call_gemini(history: List[Dict[str, Any]], user_text: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
    system = SYSTEM_PROMPT
    if context:
        listed = "\n".join(f"- [{c['type']}] {c['title']}: {c['snippet']}" for c in context)
        system += f"\n\nPlatform items related to this question:\n{listed}"

    contents = [
        {"role": "model" if m["sender_role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in history if m["sender_role"] in ("user", "assistant")
    ]
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.7},
            },
        )
        res.raise_for_status()
        data = res.json()

    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    return {"text": text, "token_count": data.get("usageMetadata", {}).get("totalTokenCount")}


def offline_answer(context: List[Dict[str, Any]]) -> str:
    # shortcut: used when GEMINI_API_KEY is not set (local dev, tests); lists matches instead of chatting
    if not context:
        return ("The AI service is not configured on this server yet. You can browse clinical trials on the "
                "Trials page and learning materials on the Resources page.")
    titles = "\n".join(f"- {c['title']}" for c in context)
    return f"The AI service is not configured on this server yet. These platform items match your question:\n{titles}"


async def generate_reply(conn, history: List[Dict[str, Any]], user_text: str) -> Dict[str, Any]:
    """Returns {content, citations, token_count, safety_flagged} for the assistant message."""
    if is_emergency(user_text):
        return {"content": EMERGENCY_REPLY, "citations": [], "token_count": None, "safety_flagged": True}

    context = await find_context(conn, user_text)
    citations = [{"type": c["type"], "id": str(c["id"]), "title": c["title"]} for c in context]

    if settings.gemini_api_key:
        result = await call_gemini(history[-HISTORY_LIMIT:], user_text, context)
        text, token_count = result["text"], result["token_count"]
    else:
        text, token_count = offline_answer(context), None

    if not text:
        text = "Sorry, I couldn't generate an answer. Please try rephrasing your question."
    # Post-check: the model may still slip into advice, so every reply carries the disclaimer.
    if DISCLAIMER not in text:
        text = f"{text}\n\n_{DISCLAIMER}_"

    return {"content": text, "citations": citations, "token_count": token_count,
            "safety_flagged": is_emergency(text)}
