from fastapi import FastAPI
from src.middlewares.correlation_id import CorrelationIDMiddleware
from src.middlewares.error_handler import global_exception_handler
from src.middlewares.events import EventMiddleware

# Setup FastAPI app and include middleware and exception handler
app = FastAPI()
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(EventMiddleware)


@app.get("/")
async def main():
    raise Exception("Test exception for global handler")
    return "Hello from ai-server!"
