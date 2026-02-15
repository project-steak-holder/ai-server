from src.models.conversation import Conversation
from src.models.message import Message, MessageType
from src.models.user import User


def test_conversation_messages(db_session):
    user = User(name="Test User")
    conv = Conversation(name="IoT Chat", user=user)
    msg1 = Message(
        conversation=conv, user=user, type=MessageType.USER, content="Check config"
    )
    msg2 = Message(
        conversation=conv, user=user, type=MessageType.AI, content="Risk found!"
    )

    db_session.add_all([user, conv, msg1, msg2])
    db_session.commit()

    loaded = db_session.query(Conversation).first()
    assert len(loaded.messages) == 2
