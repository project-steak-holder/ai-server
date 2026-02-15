"""MSSE692 AI Server - FastAPI Backend for Conversation AI."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import engine, get_db
from src.controllers.ai import router as ai_router
from src.models import Base, Conversation, Message, User
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
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(EventMiddleware)
app.include_router(ai_router)


@app.get("/")
async def root():
    return {"message": "MSSE692 AI Server Ready", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ok"}


# Temporary visibility endpoints to validate DB/model wiring during implementation.
# These routes are intended to be removed once feature-specific endpoints are complete.
@app.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "emailVerified": user.emailVerified,
            "image": user.image,
            "createdAt": user.createdAt,
            "updatedAt": user.updatedAt,
        }
        for user in users
    ]


@app.get("/conversations")
async def get_all_conversations(db: Session = Depends(get_db)):
    conversations = db.query(Conversation).all()
    return [
        {
            "id": conv.id,
            "user_id": conv.user_id,
            "name": conv.name,
            "createdAt": conv.createdAt,
            "updatedAt": conv.updatedAt,
        }
        for conv in conversations
    ]


@app.get("/messages")
async def get_all_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).all()
    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "user_id": msg.user_id,
            "content": msg.content,
            "type": msg.type.value,
            "createdAt": msg.createdAt,
            "updatedAt": msg.updatedAt,
        }
        for msg in messages
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
