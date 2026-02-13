import pytest
from sqlalchemy.orm import sessionmaker
from models import Conversation, Message

def test_conversation_message_relationship(tables):
    """Integration: Full conversation workflow"""
    # Create conversation
    conv = Conversation(title="IoT Security Chat", user_id=1)
    tables.add(conv)
    tables.commit()
    
    # Add messages
    user_msg = Message(conversation_id=conv.id, role="user", content="Check port 80")
    ai_msg = Message(conversation_id=conv.id, role="assistant", content="Risk: Insecure port!")
    
    tables.add_all([user_msg, ai_msg])
    tables.commit()
    
    # Verify relationship
    loaded_conv = tables.query(Conversation).first()
    assert len(loaded_conv.messages) == 2
    
    # Complex query
    recent_msgs = tables.query(Message).filter(
        Message.conversation_id == conv.id,
        Message.created_at > datetime(2026, 1, 1)
    ).all()
    assert len(recent_msgs) == 2
