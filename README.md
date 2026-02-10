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
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`
   Interactive docs: `http://localhost:8000/docs`

## Environment Configuration

All configuration is managed through a `.env` file in the project root. An example file is provided at `.env.example`.

| Variable | Description | Required |
|----------|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string (format: `postgresql://user:password@host/database?sslmode=require`) | Yes |
| `AI_PROVIDER_API_KEY` | API key for your AI provider | Yes |
| `AI_PROVIDER_BASE_URL` | Custom base URL for AI provider (uses provider default if not set) | No |

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
├── main.py                      # FastAPI app entry point
├── config.py                    # Environment variables & settings
├── pyproject.toml               # Dependencies
├── .env.example                 # Example environment configuration
│
├── app/
│   ├── routers/                 # API endpoints
│   ├── services/                # Business logic & orchestration
│   ├── ai/                      # AI provider abstraction
│   ├── data/                    # Database models & repositories
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── auth/                    # Authentication & authorization
│   ├── middleware/              # Error handling, logging, rate limits
│   └── utils/                   # Validation utilities
│
├── tests/                       # Unit & integration tests
│
└── docs/                        # Documentation
```

## Development

### Running Tests

```bash
pytest tests/ -v                    # Run tests
pytest tests/ -v --cov=app         # Run tests with coverage report (requires pytest-cov)
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
