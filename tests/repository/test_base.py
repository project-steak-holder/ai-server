"""Unit tests for BaseCRUDRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.repository.base import BaseCRUDRepository


class RepoResultScalarOne:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class RepoResultScalarsAll:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class MessageCRUDRepo(BaseCRUDRepository):
    model = __import__("src.models.message", fromlist=["Message"]).Message


class SoftDeleteEntity:
    def __init__(self):
        self.soft_deleted = False
        self.restored = False

    def soft_delete(self):
        self.soft_deleted = True

    def restore(self):
        self.restored = True


@pytest.mark.anyio
async def test_base_repository_query_methods():
    session = AsyncMock()
    repo = MessageCRUDRepo(session)

    session.execute.return_value = RepoResultScalarOne("found")
    assert await repo.get_by_id("abc") == "found"

    session.execute.return_value = RepoResultScalarOne("found2")
    assert await repo.get_by_field("content", "hello") == "found2"

    session.execute.return_value = RepoResultScalarsAll(["a", "b"])
    assert await repo.get_all(limit=2, offset=1) == ["a", "b"]


@pytest.mark.anyio
async def test_base_repository_create_success_commit_and_flush():
    entity = MagicMock()

    session_commit = AsyncMock()
    session_commit.add = MagicMock()
    repo_commit = MessageCRUDRepo(session_commit)
    assert await repo_commit.create(entity, flush_only=False) is entity
    session_commit.add.assert_called_once_with(entity)
    session_commit.commit.assert_awaited_once()
    session_commit.refresh.assert_awaited_once_with(entity)

    session_flush = AsyncMock()
    session_flush.add = MagicMock()
    repo_flush = MessageCRUDRepo(session_flush)
    assert await repo_flush.create(entity, flush_only=True) is entity
    session_flush.flush.assert_awaited_once()
    session_flush.commit.assert_not_awaited()
    session_flush.refresh.assert_awaited_once_with(entity)


@pytest.mark.anyio
async def test_base_repository_create_rolls_back_on_error():
    entity = MagicMock()
    session = AsyncMock()
    session.add = MagicMock()
    session.commit.side_effect = RuntimeError("commit failed")
    repo = MessageCRUDRepo(session)

    with pytest.raises(RuntimeError, match="commit failed"):
        await repo.create(entity)

    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_base_repository_update_success_commit_and_flush():
    entity = MagicMock()
    merged_entity = MagicMock()

    session_commit = AsyncMock()
    session_commit.merge.return_value = merged_entity
    repo_commit = MessageCRUDRepo(session_commit)
    assert await repo_commit.update(entity, flush_only=False) is merged_entity
    session_commit.commit.assert_awaited_once()
    session_commit.refresh.assert_awaited_once_with(merged_entity)

    session_flush = AsyncMock()
    session_flush.merge.return_value = merged_entity
    repo_flush = MessageCRUDRepo(session_flush)
    assert await repo_flush.update(entity, flush_only=True) is merged_entity
    session_flush.flush.assert_awaited_once()
    session_flush.commit.assert_not_awaited()
    session_flush.refresh.assert_awaited_once_with(merged_entity)


@pytest.mark.anyio
async def test_base_repository_update_rolls_back_on_error():
    entity = MagicMock()
    session = AsyncMock()
    session.merge.side_effect = RuntimeError("merge failed")
    repo = MessageCRUDRepo(session)

    with pytest.raises(RuntimeError, match="merge failed"):
        await repo.update(entity)

    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_base_repository_delete_success_commit_and_flush():
    entity = MagicMock()

    session_commit = AsyncMock()
    repo_commit = MessageCRUDRepo(session_commit)
    await repo_commit.delete(entity, flush_only=False)
    session_commit.delete.assert_awaited_once_with(entity)
    session_commit.commit.assert_awaited_once()

    session_flush = AsyncMock()
    repo_flush = MessageCRUDRepo(session_flush)
    await repo_flush.delete(entity, flush_only=True)
    session_flush.delete.assert_awaited_once_with(entity)
    session_flush.flush.assert_awaited_once()
    session_flush.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_base_repository_delete_rolls_back_on_error():
    entity = MagicMock()
    session = AsyncMock()
    session.delete.side_effect = RuntimeError("delete failed")
    repo = MessageCRUDRepo(session)

    with pytest.raises(RuntimeError, match="delete failed"):
        await repo.delete(entity)

    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_base_repository_soft_delete_and_restore_success_and_error():
    entity = SoftDeleteEntity()
    session = AsyncMock()
    repo = MessageCRUDRepo(session)

    result = await repo.soft_delete(entity)
    assert result is entity
    assert entity.soft_deleted is True
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(entity)

    restored = await repo.restore(entity)
    assert restored is entity
    assert entity.restored is True
    assert session.commit.await_count == 2

    failing_session = AsyncMock()
    failing_session.commit.side_effect = RuntimeError("db error")
    failing_repo = MessageCRUDRepo(failing_session)
    with pytest.raises(RuntimeError, match="db error"):
        await failing_repo.soft_delete(SoftDeleteEntity())
    failing_session.rollback.assert_awaited_once()

    failing_session2 = AsyncMock()
    failing_session2.commit.side_effect = RuntimeError("db error")
    failing_repo2 = MessageCRUDRepo(failing_session2)
    with pytest.raises(RuntimeError, match="db error"):
        await failing_repo2.restore(SoftDeleteEntity())
    failing_session2.rollback.assert_awaited_once()
