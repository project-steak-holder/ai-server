import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.conversation import Conversation
from models.message import Message
from models.base import Base

TEST_DB = "sqlite:///:memory:"

@pytest.fixture(scope="module")
def engine():
    e = create_engine(TEST_DB)
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)

@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_conversation_creation(db_session):
    conv = Conversation(title="Test Chat")
    db_session.add(conv)
    db_session.commit()
    assert conv.id is not None

def test_message_creation(db_session):
    conv = Conversation(id=1)
    msg = Message(conversation_id=1, role="user", content="Hello")
    db_session.add_all([conv, msg])
    db_session.commit()
    assert msg.content == "Hello"
