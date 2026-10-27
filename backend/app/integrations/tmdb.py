"""Optional TMDB integration. Never required for recommendations.

Design: pure HTTP client with request timeout + tiny in-memory cache. If no
API key is configured, all methods return None (callers must fall back to
locally available fields)."""
from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings


class TMDBClient:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = 60 * 60 * 6  # 6 hours

    @property
    def enabled(self) -> bool:
        return settings.tmdb_enabled

    def _cached(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, val = entry
        if time.time() - ts > self._ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _put(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def search(self, title: str) -> list[dict] | None:
        if not self.enabled:
            return None
        key = f"search:{title.lower().strip()}"
        hit = self._cached(key)
        if hit is not None:
            return hit
        try:
            with httpx.Client(timeout=settings.tmdb_timeout_seconds) as c:
                r = c.get(
                    f"{settings.tmdb_base_url}/search/movie",
                    params={"api_key": settings.tmdb_api_key, "query": title, "include_adult": "false"},
                )
                r.raise_for_status()
                data = r.json().get("results", [])
                self._put(key, data)
                return data
        except Exception:
            return None

    def poster_url(self, tmdb_id: int) -> str | None:
        if not self.enabled:
            return None
        key = f"poster:{tmdb_id}"
        hit = self._cached(key)
        if hit is not None:
            return hit
        try:
            with httpx.Client(timeout=settings.tmdb_timeout_seconds) as c:
                r = c.get(
                    f"{settings.tmdb_base_url}/movie/{tmdb_id}",
                    params={"api_key": settings.tmdb_api_key},
                )
                r.raise_for_status()
                data = r.json()
                p = data.get("poster_path")
                url = f"{settings.tmdb_image_base_url}{p}" if p else None
                self._put(key, url)
                return url
        except Exception:
            return None

    def overview(self, tmdb_id: int) -> str | None:
        if not self.enabled:
            return None
        try:
            with httpx.Client(timeout=settings.tmdb_timeout_seconds) as c:
                r = c.get(
                    f"{settings.tmdb_base_url}/movie/{tmdb_id}",
                    params={"api_key": settings.tmdb_api_key},
                )
                r.raise_for_status()
                return r.json().get("overview")
        except Exception:
            return None


tmdb = TMDBClient()
