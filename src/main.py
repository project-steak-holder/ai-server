import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.database import engine
from src.controllers.ai_controller_v2 import router as ai_router_v2
from src.controllers.health_controller import router as health_router
from src.middlewares.correlation_id import CorrelationIDMiddleware
from src.middlewares.error_handler import global_exception_handler
from src.middlewares.events import EventMiddleware
from src.middlewares.logging import setup_logger

# Reduce uvicorn and starlette errors logging levels to avoid cluttering logs
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("starlette.middleware.errors").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()


# Setup FastAPI app and include middleware and exception handler
app = FastAPI(lifespan=lifespan)
setup_logger()
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(EventMiddleware)
app.include_router(router=ai_router_v2)
app.include_router(router=health_router)


@app.get("/")
async def main():
    return "Hello from ai-server!"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ok"}
