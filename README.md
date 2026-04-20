# AI Server - Requirements Elicitation Practice System

Backend REST API for an AI-powered Requirements Elicitation Practice System. Students interact with a simulated AI stakeholder to practice requirements elicitation skills (asking questions, clarifying ambiguity, iterating toward higher-quality requirements).

## Project Purpose

This backend serves as the core infrastructure for an elicitation practice system where:

- Students submit messages to an AI stakeholder
- The system maintains conversation history and context
- An AI provider generates stakeholder responses
- All interactions are logged and persisted

## Core Architecture

### Layered Design

```
API Layer (routers)
    ↓
Service Layer (business logic)
    ↓
AI Integration Layer (provider adapter)
    ↓
Data Access Layer (repositories, ORM)
    ↓
Cross-cutting (auth, rate limiting, logging)
```

### Key Patterns

- **AI Provider Abstraction** - Swappable AI provider implementations
- **Repository Pattern** - Isolated data access layer for testability
- **Dependency Injection** - FastAPI's `Depends` for loose coupling

## Project Structure

```
ai-server/
├── alembic/                     # Database migrations
├── data/                        # Persona, project, and scale JSON context files
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── database.py              # SQLAlchemy engine & session factory
│   ├── controllers/             # API endpoints (routers)
│   ├── service/                 # Business logic & orchestration
│   ├── schemas/                 # Pydantic request/response & domain models
│   ├── repository/              # Data access layer
│   ├── models/                  # Database models (SQLAlchemy)
│   ├── agents/                  # Pydantic AI agent definitions
│   ├── middlewares/             # Correlation IDs, error handling, wide events, logging
│   ├── dependencies/            # FastAPI dependency injection (DB, services, auth, rate limit)
│   ├── exceptions/              # Custom exception classes
│   ├── security/                # Neon JWT auth & prompt sanitization
│   └── tasks/                   # Background tasks (history compaction)
├── tests/                       # Unit & integration tests
├── Dockerfile                   # Container build definition
├── docker-compose.yml           # Compose service definition
├── .env.example                 # Example environment configuration
├── .env                         # Environment configuration (gitignored)
└── pyproject.toml               # Dependencies (managed by uv)
```

## Quick Start

### Prerequisites

- [Python 3.13+](https://www.python.org/) 
- [uv](https://docs.astral.sh/uv/)
- [Neon PostgreSQL account](https://console.neon.tech/)
- AI provider API key (OpenAI, Anthropic, etc.)

### Setup

1. **Clone and setup environment:**

   ```bash
   git clone <repo-url>
   cd ai-server
   uv sync  # Install dependencies and create virtual environment
   pre-commit install  # Setup pre-commit hooks
   ```

2. **Configure environment variables:**
   Copy the example environment file and update with your values:

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` with your configuration:
   - `DATABASE_URL` - Your Neon PostgreSQL connection string
   - `AI_PROVIDER_API_KEY` - Your AI provider's API key
   - `AI_PROVIDER_BASE_URL` - (Optional) Custom base URL for your AI provider

3. **Apply database migrations:**

   ```bash
   alembic upgrade head
   ```

4. **Start the development server:**

   ```bash
   fastapi dev src/main.py
   ```

   The API will be available at `http://localhost:8000`
   Interactive docs: `http://localhost:8000/docs`

## Environment Configuration

All configuration is managed through a `.env` file in the project root. An example file is provided at `.env.example`.

| Variable               | Description                                                                                            | Required |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | -------- |
| `DATABASE_URL`         | Neon PostgreSQL connection string (format: `postgresql://user:password@host/database?sslmode=require`) | Yes      |
| `AI_PROVIDER_API_KEY`  | API key for your AI provider (OpenAI, Anthropic, etc.)                                                 | Yes      |
| `AI_PROVIDER_BASE_URL` | Custom base URL for AI provider (uses provider default if not set)                                     | Yes      |
| `AI_PROVIDER_MODEL`    | Model name or identifier to use with the AI provider (e.g. `gpt-4o-mini`, `claude-2`)                  | Yes      |
| `AUTH_URL`             | Neon Auth base URL (used by Neon Auth SDK / Data API)                                                  | No       |
| `PERSONA_FILE`         | Optional path to persona JSON context file (defaults to `data/persona.json`)                           | No       |
| `PROJECT_FILE`         | Optional path to project JSON context file (defaults to `data/project.json`)                           | No       |
| `AXIOM_INGEST_TOKEN`   | Axiom API token for ingesting wide event logs                                                          | No       |
| `AXIOM_INGEST_DATASET` | Axiom dataset name for wide events (e.g. `ai-server-events-staging`)                                   | No       |
| `ENVIRONMENT`          | Deployment environment name (e.g. `development`, `staging`, `production`). Included in every wide event | No       |
| `SERVICE_VERSION`      | Service version string included in every wide event                                                     | No       |
| `COMMIT_HASH`          | Git commit hash included in wide events (auto-detected from git if not set)                             | No       |

### Getting Your Configuration

**Neon Database URL:**

1. Create account at https://console.neon.tech/
2. Create a new project
3. Copy the connection string from the dashboard
4. Set as `DATABASE_URL` in `.env`

**AI Provider Configuration:**

- Obtain an API key from your AI provider (OpenAI, Anthropic, Google, etc.) and set `AI_PROVIDER_API_KEY` in `.env`.
- Set `AI_PROVIDER_BASE_URL` in `.env` to the provider endpoint.
- Specify the model identifier with `AI_PROVIDER_MODEL` (e.g. `gpt-4o-mini`, `gemini-2.5-flash`).
- Set `AUTH_URL` to your Neon Auth base URL so incoming JWTs can be verified against Neon's JWKS.

**Observability (optional):**

- Set `AXIOM_INGEST_TOKEN` and `AXIOM_INGEST_DATASET` to ship wide events to Axiom.
- `ENVIRONMENT`, `SERVICE_VERSION`, and `COMMIT_HASH` are attached to every emitted wide event.

## API Endpoints

### POST /api/v2/generate/stream

Accepts a user message in a conversation and streams the AI stakeholder response via Server-Sent Events (SSE).
Requires `Authorization: Bearer <token>` (Neon Auth JWT). The authenticated `user_id` is derived from the token; the `rate_limit` dependency enforces a per-user sliding window. A background task runs token counting and history compaction after the response is sent.

**Request:**

```json
{
  "conversation_id": "string",
  "content": "string"
}
```

**Response:** `text/event-stream` — the body is a stream of SSE events containing the stakeholder response as it is generated.

### GET /health and GET /ready

Liveness and readiness probes. Return `{"status": "ok"}`.

## Logging with Wide Events

This project uses **wide events** (canonical log lines) - a logging pattern that emits a single, context-rich event per request. Instead of scattering multiple log statements throughout your code, you accumulate context and emit once at request completion.

### How It Works

The `EventMiddleware` automatically creates a wide event for each request and makes it available via `request.state.wide_event`. You add business context as your handler executes, and the middleware emits the complete event at request completion.

### Basic Usage

```python
from fastapi import Request

@app.post("/api/v1/generate")
async def generate_response(request: Request, payload: GenerateRequest):
    # Access the wide event
    wide_event = request.state.wide_event

    # Add business context as you execute
    wide_event.add_context(
        user_id=payload.user_id,
        conversation_id=payload.conversation_id,
        message_length=len(payload.content)
    )

    # Fetch and add more context
    conversation = await conversation_service.get(payload.conversation_id)
    wide_event.add_context(
        message_count=len(conversation.messages),
        conversation_age_hours=(datetime.now() - conversation.created_at).total_seconds() / 3600
    )

    # Generate AI response
    response = await ai_service.generate(payload.content)
    wide_event.add_context(
        ai_model=response.model,
        tokens_used=response.usage.total_tokens,
        response_length=len(response.content)
    )

    # No need to log - middleware handles it automatically!
    return response
```

**The goal:** Anyone reading the log should understand the full business context, not just technical details.

### The `add_event_context()` Helper

Use `add_event_context()` to add context to the current request's wide event from anywhere in the call stack — no need to pass the `Request` object through every layer.

```python
from src.middlewares.events import add_event_context

class MessageService:
    async def save_user_message(self, user_id: str, conversation_id: str, content: str):
        message = await self.repo.create(user_id, conversation_id, content)
        add_event_context(user_id=user_id, conversation_id=conversation_id)
        return message
```

It works via a `ContextVar` that the `EventMiddleware` sets at the start of each request. If called outside a request (e.g. in tests or background tasks), it's a safe no-op.

### The `@wide_event` Decorator

The `@wide_event` decorator automatically captures timing and status for service methods. It records `{name}_duration_ms` and `{name}_status` ("success" or "error") on the current request's wide event via a contextvar.

```python
from src.middlewares.events import wide_event

class MessageService:
    @wide_event("save_user_message")
    async def save_user_message(self, user_id: str, conversation_id: str, content: str):
        ...

    @wide_event("get_conversation_history")
    async def get_conversation_history(self, user_id: str, conversation_id: str):
        ...
```

This produces flat keys in the wide event:

```json
{
  "save_user_message_duration_ms": 482,
  "save_user_message_status": "success",
  "get_conversation_history_duration_ms": 43,
  "get_conversation_history_status": "success"
}
```

#### Where to use `@wide_event`

Decorate at the **service layer** — that's the unit of work. Repository methods (one level deeper) would be noise since the service already wraps them. Controller-level timing is the middleware's job.

Good candidates: DB reads/writes, external API calls, LLM calls.

#### `@staticmethod` ordering

> **Warning:** When combining `@wide_event` with `@staticmethod`, `@staticmethod` must be the **outermost** (top) decorator. Otherwise, `@wide_event` wraps the staticmethod descriptor instead of the function, causing a `TypeError` at runtime.

```python
# Correct
@staticmethod
@wide_event("summarize_old_messages")
async def summarize_old_messages(messages: list[Message]) -> list[ModelMessage]:
    ...

# Wrong - causes TypeError
@wide_event("summarize_old_messages")
@staticmethod
async def summarize_old_messages(messages: list[Message]) -> list[ModelMessage]:
    ...
```

### Automatic Context

The middleware automatically includes:

```json
{
  "method": "POST",
  "path": "/api/v1/generate",
  "timestamp": "2026-02-10T10:30:45.123Z",
  "status_code": 200,
  "outcome": "success",
  "duration_ms": 342
}
```

Errors are automatically captured (flat, not nested):

```json
{
  "status_code": 500,
  "outcome": "error",
  "error_code": "INTERNAL_ERROR",
  "error_category": "server_error",
  "error_message": "An unexpected error occurred",
  "exception_type": "TypeError"
}
```

### Example Output

A complete wide event looks like:

```json
{
  "method": "POST",
  "path": "/api/v1/generate",
  "timestamp": "2026-02-10T10:30:45.123Z",
  "validate_neon_token_duration_ms": 184,
  "validate_neon_token_status": "success",
  "user_id": "user_12345",
  "conversation_id": "conv_67890",
  "user_message_length": 70,
  "save_user_message_duration_ms": 482,
  "save_user_message_status": "success",
  "load_history_duration_ms": 47,
  "load_history_status": "success",
  "summarize_old_messages_duration_ms": 0,
  "summarize_old_messages_status": "success",
  "stakeholder_query_duration_ms": 2846,
  "stakeholder_query_status": "success",
  "save_ai_message_duration_ms": 118,
  "save_ai_message_status": "success",
  "process_agent_query_duration_ms": 5583,
  "process_agent_query_status": "success",
  "ai_response_length": 103,
  "status_code": 200,
  "outcome": "success",
  "duration_ms": 5749
}
```

### Best Practices

**DO:**

- Add context incrementally as you execute
- Use `@wide_event` on service methods that do I/O (DB, HTTP, LLM)
- Keep all fields flat — no nested dicts
- Include identifiers (user_id, conversation_id) and metrics (lengths, counts)
- Let the middleware handle emission automatically

**DON'T:**

- Scatter multiple log statements throughout handlers
- Log response content or PII — use lengths instead
- Decorate both service and repository layers (pick service)
- Call `print()` or `logger.info()` directly in handlers

### References

- [Logging Sucks - Wide Events](https://loggingsucks.com)
- [Stripe's Canonical Log Lines](https://stripe.com/blog/canonical-log-lines)
- [Observability Wide Events 101](https://boristane.com/blog/observability-wide-events-101/)

## Exception Handling

This project uses a structured exception system built on `AppException` for consistent error handling across the API. Custom exceptions automatically integrate with the global exception handler and wide event logging.

### Creating Custom Exceptions

To create a new exception type, extend `AppException` and provide default values:

#### Example: Simple Not Found Exception

```python
# src/exceptions/conversation_exceptions.py
from src.exceptions.base_exceptions import AppException

class ConversationNotFoundError(AppException):
    """Raised when a conversation does not exist."""

    def __init__(self, conversation_id: str):
        super().__init__(
            status_code=404,
            error="CONVERSATION_NOT_FOUND",
            message=f"Conversation with ID '{conversation_id}' does not exist",
            details={"conversation_id": conversation_id}
        )
```

### Using Custom Exceptions

Once defined, raise your custom exceptions anywhere in your code:

```python
from src.exceptions.conversation_exceptions import ConversationNotFoundError

def some_function():
    await conversation = conversationrepo.find(conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
```

### Automatic Error Response

The global exception handler (`src/middlewares/error_handler.py`) automatically converts your custom exceptions into proper HTTP responses:

**When you raise:**

```python
raise ConversationNotFoundError("conv_12345")
```

**The client receives:**

```json
{
  "error": "CONVERSATION_NOT_FOUND",
  "message": "Conversation with ID 'conv_12345' does not exist",
  "details": {
    "conversation_id": "conv_12345"
  }
}
```

**HTTP Status:** `404 Not Found`

**Headers:**

```
X-Correlation-ID: 7f3d2a8b-4c1e-9f6d-3a2b-1c4e5f6d7a8b
Content-Type: application/json
```

## Development

### Running Tests

```bash
pytest tests/ -v                    # Run tests
pytest tests/ -v --cov=src         # Run tests with coverage report (requires pytest-cov)
```

### Adding Dependencies

```bash
uv add package-name              # Add to dependencies
uv add package-name --dev        # Add to dev dependencies
```

### Database Migrations

When schema changes are needed:

```bash
alembic upgrade head
```

## Tech Stack

- **Python 3.13+** - Runtime
- **FastAPI 0.135+** - REST API framework (with Server-Sent Events streaming)
- **Pydantic AI Slim** (with Google backend) - Agent framework for stakeholder simulation
- **Neon PostgreSQL** - Serverless Postgres database
- **SQLAlchemy 2.0** - Async ORM with typed mapped columns
- **Alembic** - Database migrations
- **PyJWT + cryptography** - Neon Auth JWT verification
- **Axiom** - Wide event ingestion for observability
- **uv** - Dependency and environment management

## Documentation

- [Full Project Documentation](https://project-steak-holder.github.io/project-docs/)
- [Neon Database Documentation](https://neon.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic AI](https://ai.pydantic.dev/)

## License

See LICENSE file for details.
