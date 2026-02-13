import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Conversation, Message, Base

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def tables(engine):
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

def test_conversation_model(tables):
    """Unit: Conversation CRUD"""
    conv = Conversation(title="Test Chat", user_id=1)
    tables.add(conv)
    tables.commit()
    
    saved = tables.query(Conversation).first()
    assert saved.title == "Test Chat"
    assert saved.id is not None

def test_message_model(tables):
    """Unit: Message model"""
    conv = Conversation(id=1, title="test")
    msg = Message(
        conversation_id=1,
        role="user",
        content="Hello AI",
        model="llama3.1-8b"
    )
    tables.add_all([conv, msg])
    tables.commit()
    
    assert tables.query(Message).filter_by(content="Hello AI").first() is not None
