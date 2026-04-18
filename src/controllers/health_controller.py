import os
from typing import Any, Dict

import axiom_py  # type: ignore[import-untyped]
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.database import engine
from src.security.neon import get_jwks

router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def check_observability() -> Dict[str, Any]:
    """Check observability backend connectivity"""
    token = os.environ.get("AXIOM_INGEST_TOKEN")
    dataset = os.environ.get("AXIOM_INGEST_DATASET")

    if not token or not dataset:
        return {"status": "unhealthy"}

    try:
        async with axiom_py.AsyncClient(token) as client:
            query = f"['{dataset}'] | limit 1"
            await client.query(query)
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def check_auth() -> Dict[str, Any]:
    """Check auth service connectivity"""
    if not os.environ.get("AUTH_URL"):
        return {"status": "unhealthy"}

    try:
        jwks = await get_jwks()
        if not isinstance(jwks, dict) or "keys" not in jwks:
            return {"status": "unhealthy"}
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


"""Note:

LLM health is derived from recent log events in the Axiom dashboard.
A dedicated endpoint-level LLM dependency check is intentionally omitted.
"""


@router.get("/dependencies")
async def dependencies():
    """Connectivity checks for external dependencies."""
    db_status = await check_database()
    observability_status = await check_observability()
    auth_status = await check_auth()

    checks = {
        "database": db_status,
        "observability": observability_status,
        "auth": auth_status,
    }

    overall_status = (
        "healthy"
        if all(s["status"] == "healthy" for s in checks.values())
        else "unhealthy"
    )

    payload = {"status": overall_status, "checks": checks}
    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(status_code=status_code, content=payload)
