"""Base CRUD repository with generic database operations."""

from typing import Generic, Optional, Sequence, TypeVar

from src.models.base import Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Type variable for the model class
ModelT = TypeVar("ModelT", bound=Base)


class BaseCRUDRepository(Generic[ModelT]):
    """Generic CRUD repository for SQLAlchemy models."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: str) -> Optional[ModelT]:
        """Fetch record by primary key."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_field(self, field: str, value: object) -> Optional[ModelT]:
        """Fetch record by field value."""
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Sequence[ModelT]:
        """Fetch all records with optional pagination."""
        stmt = select(self.model).order_by(self.model.id)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, entity: ModelT, *, flush_only: bool = False) -> ModelT:
        """Insert new record."""
        try:
            self.session.add(entity)
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception:
            # Only rollback if we're managing the transaction (not flush_only)
            if not flush_only:
                await self.session.rollback()
            raise

    async def update(self, entity: ModelT, *, flush_only: bool = False) -> ModelT:
        """Update existing record."""
        try:
            entity = await self.session.merge(entity)
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception:
            # Only rollback if we're managing the transaction (not flush_only)
            if not flush_only:
                await self.session.rollback()
            raise

    async def delete(self, entity: ModelT, *, flush_only: bool = False) -> None:
        """Delete record."""
        try:
            await self.session.delete(entity)
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
        except Exception:
            # Only rollback if we're managing the transaction (not flush_only)
            if not flush_only:
                await self.session.rollback()
            raise

    async def soft_delete(self, entity: ModelT) -> ModelT:
        """Soft delete record (requires SoftDeleteMixin)."""
        try:
            entity.soft_delete()  # type: ignore[attr-defined]
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, entity: ModelT) -> ModelT:
        """Restore soft-deleted record (requires SoftDeleteMixin)."""
        try:
            entity.restore()  # type: ignore[attr-defined]
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception:
            await self.session.rollback()
            raise
