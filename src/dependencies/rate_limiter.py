"""Per-user in-memory sliding window rate limiter."""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.dependencies.user import CurrentUser

_buckets: dict[str, deque[datetime]] = defaultdict(deque)
_LIMIT = 5
_WINDOW = timedelta(minutes=1)


def rate_limit(current_user: CurrentUser) -> None:
    user_id = current_user.user_id
    now = datetime.now(UTC)
    cutoff = now - _WINDOW
    bucket = _buckets[user_id]
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= _LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    bucket.append(now)


RateLimit = Annotated[None, Depends(rate_limit)]
