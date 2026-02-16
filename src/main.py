import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.database import engine
from src.controllers.ai import router as ai_router
from src.middlewares.correlation_id import CorrelationIDMiddleware
from src.middlewares.error_handler import global_exception_handler
from src.middlewares.events import EventMiddleware

# Reduce uvicorn and starlette errors logging levels to avoid cluttering logs
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
logging.getLogger("starlette.middleware.errors").setLevel(logging.CRITICAL)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


# Setup FastAPI app and include middleware and exception handler
app = FastAPI(lifespan=lifespan)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(EventMiddleware)
app.include_router(ai_router)


@app.get("/")
async def main():
    return "Hello from ai-server!"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ok"}
