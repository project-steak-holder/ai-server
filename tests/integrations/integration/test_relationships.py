import pytest
from sqlalchemy.orm import sessionmaker
from models.conversation import Conversation
from models.message import Message

def test_conversation_messages(db_session):
    # Create conversation with messages
    conv = Conversation(title="IoT Chat")
    msg1 = Message(conversation_id=conv.id, role="user", content="Check config")
    msg2 = Message(conversation_id=conv.id, role="assistant", content="Risk found!")
    
    db_session.add_all([conv, msg1, msg2])
    db_session.commit()
    
    # Test relationship
    loaded = db_session.query(Conversation).first()
    assert len(loaded.messages) == 2
