from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import Depends, HTTPException, status
import structlog

from app.config.settings import Settings, get_settings
from app.middleware.auth_middleware import get_current_user
from app.models.auth_models import CurrentUser


logger = structlog.get_logger(__name__)


@dataclass
class UsageWindow:
    hourly_count: int
    daily_count: int


class InMemoryRateLimitStore:
    def __init__(self) -> None:
        self._hourly: dict[str, deque[datetime]] = defaultdict(deque)
        self._daily: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def increment_and_get(self, user_id: str, now: datetime) -> UsageWindow:
        async with self._lock:
            hourly_window = self._hourly[user_id]
            daily_window = self._daily[user_id]

            hour_start = now - timedelta(hours=1)
            day_start = now - timedelta(days=1)

            while hourly_window and hourly_window[0] < hour_start:
                hourly_window.popleft()
            while daily_window and daily_window[0] < day_start:
                daily_window.popleft()

            hourly_window.append(now)
            daily_window.append(now)

            return UsageWindow(hourly_count=len(hourly_window), daily_count=len(daily_window))

    async def clear(self) -> None:
        async with self._lock:
            self._hourly.clear()
            self._daily.clear()


class RateLimiter:
    def __init__(self, store: InMemoryRateLimitStore, hourly_limit: int, daily_limit: int) -> None:
        self._store = store
        self._hourly_limit = hourly_limit
        self._daily_limit = daily_limit

    async def enforce(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        usage = await self._store.increment_and_get(user_id=user_id, now=now)

        logger.info(
            "rate_limit_usage",
            user_id=user_id,
            hourly_count=usage.hourly_count,
            daily_count=usage.daily_count,
            hourly_limit=self._hourly_limit,
            daily_limit=self._daily_limit,
        )

        if usage.hourly_count > self._hourly_limit or usage.daily_count > self._daily_limit:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                hourly_count=usage.hourly_count,
                daily_count=usage.daily_count,
                hourly_limit=self._hourly_limit,
                daily_limit=self._daily_limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

    def set_limits(self, hourly_limit: int, daily_limit: int) -> None:
        self._hourly_limit = hourly_limit
        self._daily_limit = daily_limit

    async def reset(self) -> None:
        await self._store.clear()


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    settings: Settings = get_settings()
    store = InMemoryRateLimitStore()
    return RateLimiter(store, settings.rate_limit_hourly, settings.rate_limit_daily)


async def enforce_rate_limit(
    current_user: CurrentUser = Depends(get_current_user),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    await limiter.enforce(current_user.user_id)
