import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.conversation import Conversation
from src.models.summary import Summary
from src.repository.summary_repository import SummaryRepository


@pytest.mark.anyio
async def test_update_summary_creates_then_updates() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Summary.metadata.create_all(
                sync_conn,
                tables=[Conversation.__table__, Summary.__table__],
            )
        )

    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    conversation_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        session.add(Conversation(id=conversation_id))
        await session.commit()

        repo = SummaryRepository(session)

        created = await repo.update_summary(
            conversation_id=conversation_id,
            content="first",
            token_count=1,
            window_start=now,
            window_end=now,
        )
        assert created.id is not None
        assert created.conversation_id == conversation_id
        assert created.content == "first"

        fetched1 = (
            await session.execute(
                select(Summary).where(Summary.conversation_id == conversation_id)
            )
        ).scalar_one()
        assert fetched1.id == created.id

        updated = await repo.update_summary(
            conversation_id=conversation_id,
            content="second",
            token_count=2,
            window_start=now,
            window_end=now,
        )
        assert updated.id == created.id

        fetched2 = (
            await session.execute(
                select(Summary).where(Summary.conversation_id == conversation_id)
            )
        ).scalar_one()
        assert fetched2.id == created.id
        assert fetched2.content == "second"
        assert fetched2.token_count == 2

    await engine.dispose()
