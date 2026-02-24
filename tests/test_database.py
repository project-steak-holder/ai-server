"""Unit tests for database session dependency module."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from tests.helpers import FakeSessionCM


@pytest.mark.anyio
async def test_database_get_session_success(monkeypatch):
    import src.database as db

    session = AsyncMock()
    monkeypatch.setattr(db, "SessionLocal", lambda: FakeSessionCM(session))

    gen = db.get_session()
    yielded = await anext(gen)
    assert yielded is session

    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    session.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_database_get_session_rolls_back_on_error(monkeypatch):
    import src.database as db

    session = AsyncMock()
    monkeypatch.setattr(db, "SessionLocal", lambda: FakeSessionCM(session))

    gen = db.get_session()
    await anext(gen)

    with pytest.raises(RuntimeError, match="boom"):
        await gen.athrow(RuntimeError("boom"))

    session.rollback.assert_awaited_once()


def test_database_module_raises_when_database_url_missing(monkeypatch):
    import dotenv

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)

    path = Path(__file__).resolve().parents[1] / "src" / "database.py"
    spec = importlib.util.spec_from_file_location("temp_database_no_env", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        spec.loader.exec_module(module)
