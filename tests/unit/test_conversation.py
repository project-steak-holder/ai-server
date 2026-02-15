import pytest
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from src.models.conversation import Conversation
from src.models.message import Message, MessageType
from src.models.user import User


def test_conversation_creation(db_session):
    user = User(name="Test User")
    conv = Conversation(name="Test Chat", user=user)
    db_session.add_all([user, conv])
    db_session.commit()
    db_session.refresh(conv)

    assert conv.id is not None
    assert conv.name == "Test Chat"


def test_conversation_requires_valid_user_fk(db_session):
    conv = Conversation(name="Orphan Conversation", user_id=uuid4())
    db_session.add(conv)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_conversation_relationship_to_messages(db_session):
    user = User(name="IoT User")
    conv = Conversation(name="IoT Security Chat", user=user)
    msg1 = Message(
        conversation=conv,
        user=user,
        type=MessageType.USER,
        content="Check port 80",
    )
    msg2 = Message(
        conversation=conv,
        user=user,
        type=MessageType.AI,
        content="Risk: Insecure port!",
    )
    db_session.add_all([user, conv, msg1, msg2])
    db_session.commit()

    loaded_conv = db_session.query(Conversation).first()
    assert len(loaded_conv.messages) == 2
