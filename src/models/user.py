"""User model STUB to allow for foreign key relationships in Message model."""

from .base import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "neon_auth"}
