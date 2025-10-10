from time import time

_cache = {}


def set_cache(key: str, value, ttl: int = 300) -> None:
    _cache[key] = (value, time() + ttl)


def get_cache(key: str):
    item = _cache.get(key)
    if not item:
        return None
    value, expires = item
    if time() > expires:
        try:
            del _cache[key]
        except Exception:
            pass
        return None
    return value


