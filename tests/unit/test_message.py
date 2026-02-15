from time import sleep
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.models.message import Message, MessageType
from src.models.user import User
from src.models.conversation import Conversation


def _seed_user_and_conversation(session):
    user = User(name="Message Test User")
    session.add(user)
    session.commit()

    conversation = Conversation(name="Message Test Conversation", user_id=user.id)
    session.add(conversation)
    session.commit()
    return user, conversation


def test_message_creation(db_session):
    user, conversation = _seed_user_and_conversation(db_session)
    message = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        content="Hello",
        type=MessageType.USER,
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)

    assert message.id is not None
    assert message.createdAt is not None
    assert message.updatedAt is not None


def test_message_requires_valid_foreign_keys(db_session):
    message = Message(
        conversation_id=uuid4(),
        user_id=uuid4(),
        content="Hello",
        type=MessageType.USER,
    )
    db_session.add(message)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_message_requires_non_nullable_fields(db_session):
    user, conversation = _seed_user_and_conversation(db_session)
    message = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        content=None,  # type: ignore[arg-type]
        type=MessageType.USER,
    )
    db_session.add(message)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_message_updated_at_changes_on_update(db_session):
    user, conversation = _seed_user_and_conversation(db_session)
    message = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        content="v1",
        type=MessageType.USER,
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    before = message.updatedAt

    sleep(0.01)
    message.content = "v2"
    db_session.commit()
    db_session.refresh(message)

    assert message.updatedAt > before


def test_message_indexes_exist(engine):
    indexes = inspect(engine).get_indexes("message")
    names = {idx["name"] for idx in indexes}
    assert "ix_message_user_id" in names
    assert "ix_message_conversation_createdAt" in names
