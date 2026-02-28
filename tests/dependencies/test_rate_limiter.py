"""Unit tests for the rate limiter dependency."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from src.dependencies.rate_limiter import _buckets, rate_limit
from src.dependencies.user import AuthenticatedUser


@pytest.fixture(autouse=True)
def clear_buckets():
    """Reset in-memory state between tests."""
    _buckets.clear()
    yield
    _buckets.clear()


def make_user(user_id: str = "user-1"):
    return AuthenticatedUser(user_id=user_id)


def test_rate_limit_allows_requests_within_limit():
    """5 requests from the same user should all pass."""
    user = make_user()
    for _ in range(5):
        rate_limit(user)  # must not raise


def test_rate_limit_blocks_on_sixth_request():
    """The 6th request from the same user within the window raises 429."""
    user = make_user()
    for _ in range(5):
        rate_limit(user)
    with pytest.raises(HTTPException) as exc_info:
        rate_limit(user)
    assert exc_info.value.status_code == 429


def test_rate_limit_isolates_users():
    """A user at the limit does not affect a different user."""
    user_a = make_user("user-a")
    user_b = make_user("user-b")
    for _ in range(5):
        rate_limit(user_a)
    # user_b should still pass
    rate_limit(user_b)  # must not raise


def test_rate_limit_evicts_old_entries():
    """Entries older than 60 seconds are evicted; request should pass."""
    user = make_user()
    old_time = datetime.now(UTC) - timedelta(seconds=61)
    # Inject 5 old timestamps directly into the bucket
    for _ in range(5):
        _buckets[user.user_id].append(old_time)
    # All 5 are expired, so this request should pass
    rate_limit(user)  # must not raise


def test_rate_limit_counts_recent_entries():
    """Entries within the window (59s old) still count toward the limit."""
    user = make_user()
    recent_time = datetime.now(UTC) - timedelta(seconds=59)
    for _ in range(5):
        _buckets[user.user_id].append(recent_time)
    with pytest.raises(HTTPException) as exc_info:
        rate_limit(user)
    assert exc_info.value.status_code == 429
