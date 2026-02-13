"""MSSE692 AI Server - FastAPI Backend for Conversation AI"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from models.base import Base
from models.conversation import Conversation
from models.message import Message
from database import engine, get_db  # You'll create these

load_dotenv()

# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown

app = FastAPI(
    title="MSSE692 AI Server",
    description="AI Backend for Requirements Engineering Practicum",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "MSSE692 AI Server Ready", "status": "healthy"}

@app.post("/conversations/")
async def create_conversation(title: str, db: Session = Depends(get_db)):
    """Create new conversation"""
    conv = Conversation(title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"conversation_id": conv.id}

@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    """Get conversation with messages"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conv.id,
        "title": conv.title,
        "messages": [{"role": m.role, "content": m.content} for m in conv.messages]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
