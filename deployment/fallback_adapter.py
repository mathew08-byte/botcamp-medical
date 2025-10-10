import os
import redis
from typing import Any, Dict


def _redis() -> redis.Redis:
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def set_active_ai_provider(provider: str, ttl: int = 3600) -> None:
    r = _redis()
    r.set("ai:active_provider", provider, ex=ttl)


def get_active_ai_provider() -> str:
    r = _redis()
    val = r.get("ai:active_provider")
    if val:
        try:
            return val.decode()
        except Exception:
            return str(val)
    return os.getenv("AI_PROVIDER", "gemini")


def call_ai(prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """Call AI with fallback. This is a thin wrapper; wire into services/ai_service.py if desired."""
    provider = get_active_ai_provider()
    tried = []
    for name in [provider, os.getenv("AI_FALLBACK_PROVIDER", "openai")]:
        if name in tried:
            continue
        tried.append(name)
        try:
            # Placeholder call; integrate with your existing AI service clients
            if name == "gemini":
                # simulate successful call
                return {"provider": name, "content": f"[gemini] {prompt}", "confidence": 0.9}
            if name == "openai":
                return {"provider": name, "content": f"[openai] {prompt}", "confidence": 0.85}
        except Exception:
            continue
    return {"provider": "none", "error": "all providers failed"}

