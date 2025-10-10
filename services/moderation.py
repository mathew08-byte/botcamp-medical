import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "You are an expert medical QA moderator. Given a question, options, correct answer, and explanation, "
    "assess clarity, grammar, medical accuracy, and relevance. Detect duplicates if hinted (by similarity text). "
    "Return JSON with: moderation_score (0-100), moderation_comments (short string), action one of ['accept','flag','reject']. "
    "Be strict and concise."
)


def moderate_question_with_ai(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses OpenAI or Gemini to moderate question quality.
    Falls back to a simple heuristic if no keys.
    """
    # Try to get API keys from environment or files
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API")
    
    # Try to read from gemni_api file if not in environment
    if not gemini_key:
        try:
            with open("gemni_api", "r", encoding="utf-8") as f:
                gemini_key = f.read().strip()
        except FileNotFoundError:
            pass
    
    payload = json.dumps(question_data, ensure_ascii=False)
    logger.info(f"Moderating question with AI. Gemini key available: {bool(gemini_key)}, OpenAI key available: {bool(openai_key)}")

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": payload},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            logger.info(f"OpenAI moderation result: {result}")
            return result
        except Exception as e:
            logger.error(f"OpenAI moderation failed: {e}")

    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = SYSTEM_INSTRUCTIONS + "\n\nQuestion JSON:\n" + payload + "\n\nReturn JSON only."
            result = model.generate_content(prompt)
            text = result.text or "{}"
            parsed_result = json.loads(text)
            logger.info(f"Gemini moderation result: {parsed_result}")
            return parsed_result
        except Exception as e:
            logger.error(f"Gemini moderation failed: {e}")

    # Heuristic fallback
    logger.warning("Using heuristic moderation fallback")
    qtext = (question_data.get("question") or question_data.get("question_text") or "").strip()
    opts = question_data.get("options") or []
    score = 50
    if qtext.endswith("?") and len(opts) >= 4:
        score = 75
    action = "accept" if score >= 70 else "flag"
    return {
        "moderation_score": score,
        "moderation_comments": "Heuristic moderation applied - no AI available.",
        "action": action,
    }


async def moderate_question_async(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper for moderation function
    """
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, moderate_question_with_ai, question_data)


