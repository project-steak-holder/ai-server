# AI Server - Requirements Elicitation Practice System

Backend REST API for an AI-powered Requirements Elicitation Practice System. Students interact with a simulated AI stakeholder to practice requirements elicitation skills (asking questions, clarifying ambiguity, iterating toward higher-quality requirements).

## Tech Stack

- **Python 3.13** - Runtime
- **FastAPI 0.128.4+** - REST API framework
- **Pydantic AI Slim** - AI integration with OpenAI backend
- **Neon PostgreSQL** - Serverless Postgres database
- **uv** - Package manager
- **SQLAlchemy** - ORM for database queries

## Project Purpose

This backend serves as the core infrastructure for an elicitation practice system where:

- Students submit messages to an AI stakeholder
- The system maintains conversation history and context
- An AI provider generates stakeholder responses
- All interactions are logged and persisted

## Quick Start

### Prerequisites

- Python 3.13+
- Neon PostgreSQL account (https://console.neon.tech/)
- AI provider API key (OpenAI, Anthropic, etc.)

### Setup

1. **Clone and setup environment:**

   ```bash
   git clone <repo-url>
   cd ai-server
   uv sync  # Install dependencies and create virtual environment
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

3. **Start the development server:**

   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`
   Interactive docs: `http://localhost:8000/docs`

## Environment Configuration

All configuration is managed through a `.env` file in the project root. An example file is provided at `.env.example`.

| Variable               | Description                                                                                            | Required |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | -------- |
| `DATABASE_URL`         | Neon PostgreSQL connection string (format: `postgresql://user:password@host/database?sslmode=require`) | Yes      |
| `AI_PROVIDER_API_KEY`  | API key for your AI provider                                                                           | Yes      |
| `AI_PROVIDER_BASE_URL` | Custom base URL for AI provider (uses provider default if not set)                                     | No       |

### Getting Your Configuration

**Neon Database URL:**

1. Create account at https://console.neon.tech/
2. Create a new project
3. Copy the connection string from the dashboard
4. Set as `DATABASE_URL` in `.env`

**AI Provider API Key:**

- Obtain from your AI provider (OpenAI, Anthropic, etc.)
- Set as `AI_PROVIDER_API_KEY` in `.env`

## Project Structure

```
ai-server/
├── alembic/                     # Database migrations
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config/                  # Environment variables & settings
│   ├── controllers/             # API endpoints (routers)
│   ├── services/                # Business logic & orchestration
│   ├── schemas/                 # Pydantic request/response models
│   ├── repositories/            # Data access layer
│   ├── models/                  # Database models (SQLAlchemy)
│   ├── ai/                      # AI provider abstraction
│   ├── middlewares/             # Error handling, logging, rate limits
│   ├── dependencies/            # FastAPI dependency injection
│   ├── exceptions/              # Custom exception classes
│   └── utils/                   # Validation & helper functions
├── tests/                       # Unit & integration tests
├── scripts/                     # Database seeding & utility scripts
├── ruff.yaml                    # Linter configuration
├── .env.example                 # Example environment configuration
├── .env.local                   # Local development environment
├── .env                         # Environment configuration (gitignored)
└── pyproject.toml               # Dependencies
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

Errors are automatically captured:

```json
{
  "status_code": 500,
  "outcome": "error",
  "error": {
    "type": "ValidationError",
    "message": "Invalid conversation_id format"
  }
}
```

### Example Output

A complete wide event looks like:

```json
{
  "method": "POST",
  "path": "/api/v1/generate",
  "timestamp": "2026-02-10T10:30:45.123Z",
  "status_code": 200,
  "outcome": "success",
  "duration_ms": 342,
  "user_id": "user_12345",
  "conversation_id": "conv_67890",
  "message_length": 156,
  "message_count": 8,
  "conversation_age_hours": 2.5,
  "ai_model": "gpt-4",
  "tokens_used": 450,
  "response_length": 203
}
```

### Best Practices

**DO:**

- Add context incrementally as you execute
- Include business context (user tier, account age, etc.)
- Use high-cardinality fields (IDs, not just categories)
- Let the middleware handle emission automatically

**DON'T:**

- Scatter multiple log statements throughout handlers
- Log only technical details without business context
- Call `print()` or `logger.info()` directly in handlers
- Miss opportunities to add relevant context

### References

- [Logging Sucks - Wide Events](https://loggingsucks.com)
- [Stripe's Canonical Log Lines](https://stripe.com/blog/canonical-log-lines)
- [Observability Wide Events 101](https://boristane.com/blog/observability-wide-events-101/)

## API Endpoints

### POST /api/v1/generate

Accept a user message in a conversation and return AI stakeholder response.

**Request:**

```json
{
  "conversation_id": "string",
  "user_id": "string",
  "content": "string"
}
```

**Response:**

```json
{
  "conversation_id": "string",
  "user_id": "string",
  "content": "string",
  "type": "MessageType",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

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

## Documentation

- [Neon Database Documentation](https://neon.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic AI](https://ai.pydantic.dev/)

## License

See LICENSE file for details.
