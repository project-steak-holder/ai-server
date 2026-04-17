"""Conversation model STUB to allow for foreign key relationships in Message model."""

from .base import Base


class Conversation(Base):
    __tablename__ = "conversation"
