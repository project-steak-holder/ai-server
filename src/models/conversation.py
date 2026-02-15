"""Conversation model STUB to allow for foreign key relationships in Message model."""

from sqlalchemy import UUID, Column
from .base import Base


class Conversation(Base):
    __tablename__ = "conversation"
    id = Column(UUID, primary_key=True)
