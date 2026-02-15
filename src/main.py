"""MSSE692 AI Server - FastAPI Backend for Conversation AI."""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import engine, get_db
from src.models import Base, Conversation
from src.middlewares.correlation_id import CorrelationIDMiddleware
from src.middlewares.error_handler import global_exception_handler
from src.middlewares.events import EventMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MSSE692 AI Server",
    description="AI Backend for Requirements Engineering Practicum",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(EventMiddleware)
app.add_middleware(CorrelationIDMiddleware)


@app.get("/")
async def root():
    return {"message": "MSSE692 AI Server Ready", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ok"}


@app.post("/conversations/")
async def create_conversation(name: str, user_id: str, db: Session = Depends(get_db)):
    """Create a new conversation."""
    conv = Conversation(name=name, user_id=user_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"conversation_id": conv.id}


@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, db: Session = Depends(get_db)):
    """Get a conversation with all messages."""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conv.id,
        "name": conv.name,
        "messages": [
            {"type": m.type.value, "content": m.content} for m in conv.messages
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
