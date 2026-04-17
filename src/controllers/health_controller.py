import os
from typing import Any, Dict

import axiom_py  # type: ignore[import-untyped]
from fastapi import APIRouter
from sqlalchemy import text

from src.database import engine

router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }


async def check_axiom() -> Dict[str, Any]:
    """Check Axiom connectivity"""
    token = os.environ.get("AXIOM_INGEST_TOKEN")
    dataset = os.environ.get("AXIOM_INGEST_DATASET")

    if not token or not dataset:
        return {"status": "unhealthy", "message": "Axiom credentials not configured"}

    try:
        client = axiom_py.Client(token)
        # Try to query the dataset to verify connectivity
        query = f'["{dataset}", ""] | limit 1'
        await client.apl.query(query)
        return {"status": "healthy", "message": "Axiom connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Axiom connection failed: {str(e)}"}


@router.get("/checks")
async def checks():
    """Connectivity checks for database and Axiom"""
    db_status = await check_database()
    axiom_status = await check_axiom()

    overall_status = (
        "healthy"
        if all(s["status"] == "healthy" for s in [db_status, axiom_status])
        else "unhealthy"
    )

    return {
        "status": overall_status,
        "checks": {
            "database": db_status,
            "axiom": axiom_status,
        },
    }
