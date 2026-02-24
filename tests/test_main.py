"""Unit tests for FastAPI app module entrypoints."""

import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_main_module_routes_and_lifespan(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://user:pass@localhost/testdb"
    )
    main_mod = importlib.import_module("src.main")

    assert await main_mod.main() == "Hello from ai-server!"
    assert await main_mod.health() == {"status": "ok"}
    assert await main_mod.ready() == {"status": "ok"}

    dispose = AsyncMock()
    monkeypatch.setattr(main_mod, "engine", SimpleNamespace(dispose=dispose))

    async with main_mod.lifespan(main_mod.app):
        pass

    dispose.assert_awaited_once()
