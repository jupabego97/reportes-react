"""Cache TTL para predicciones y compras."""
import hashlib
import json
from typing import Any, Optional

from cachetools import TTLCache


# TTL 15 minutos
PREDICCIONES_CACHE: TTLCache = TTLCache(maxsize=50, ttl=900)
PREDICCIONES_DESGLOSE_CACHE: TTLCache = TTLCache(maxsize=100, ttl=900)
COMPRAS_CACHE: TTLCache = TTLCache(maxsize=50, ttl=900)


def _cache_key(prefix: str, filters: Any, extra: Optional[str] = None) -> str:
    """Genera clave de cache a partir de filtros."""
    try:
        data = filters.model_dump() if hasattr(filters, "model_dump") else dict(filters)
    except Exception:
        data = {}
    payload = json.dumps(data, sort_keys=True, default=str)
    if extra:
        payload += f":{extra}"
    return f"{prefix}:{hashlib.sha256(payload.encode()).hexdigest()}"


def get_cached(cache: TTLCache, key: str) -> Optional[Any]:
    """Obtiene valor del cache."""
    return cache.get(key)


def set_cached(cache: TTLCache, key: str, value: Any) -> None:
    """Guarda valor en cache."""
    cache[key] = value
