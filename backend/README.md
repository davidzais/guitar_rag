# Software Engineering Assistant — Backend

A FastAPI service that wraps a LangChain/Anthropic agent. The agent answers software engineering questions and maintains per-conversation history via a LangGraph `MemorySaver` checkpointer.

## Project structure

```
backend/
  agent.py            # Agent singleton (model, system prompt, checkpointer)
  api.py              # FastAPI app and routes
  exceptions.py       # Domain exceptions (transport-layer independent)
  logging_config.py   # Structured JSON logging setup (structlog)
  main.py             # Entry point — configures logging, starts uvicorn
  middleware.py       # Request ID middleware (injects request_id into every log line)
  conftest.py         # Stubs heavy imports so tests never hit the real API
  test_api.py         # pytest test suite
  models/
    chat.py           # Pydantic request/response models
  services/
    chat_service.py   # Business logic (no HTTP concerns)
```

## Prerequisites

- Python 3.14+
- An Anthropic API key in a `.env` file at the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Install dependencies

From the project root:

```bash
uv sync
```

This installs all dependencies declared in `pyproject.toml`, including `fastapi`, `uvicorn`, `langchain-anthropic`, `structlog`, and `httpx`.

## Run the server

From the `backend/` directory:

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

Interactive docs (Swagger UI) are at `http://localhost:8000/docs`.

### Configuration

All options are set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `PORT` | `8000` | Port the server listens on. |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `JSON_LOGS` | `true` | Set to `false` for human-readable console output during local development. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed CORS origins. |
| `RATE_LIMIT` | `20/minute` | Per-IP rate limit on `/chat`. Supports `second`, `minute`, `hour`, `day`. |
| `API_KEY` | *(unset)* | Bearer token required on `/chat`. If unset, auth is skipped (local dev only). |

Example for local development with readable logs:

```bash
JSON_LOGS=false LOG_LEVEL=DEBUG python main.py
```

## Logging

Logs are structured JSON by default, suitable for shipping to any log aggregator (Datadog, CloudWatch, ELK, etc.). Every log line emitted during a request includes a `request_id` field so you can trace a full request across all layers:

```json
{"request_id": "a3f1...", "method": "POST", "path": "/chat", "event": "request_started", "level": "info", "timestamp": "2026-06-06T12:00:00Z"}
{"request_id": "a3f1...", "logger": "services.chat_service", "event": "agent_invocation_failed", "level": "error", "timestamp": "2026-06-06T12:00:01Z"}
```

Third-party library logs (uvicorn, langchain) are routed through the same pipeline and also emit as JSON.

## API usage

### `POST /chat`

**Request body:**

```json
{
  "conversation_id": "my-session-123",
  "message": "What is the difference between a list and a tuple in Python?"
}
```

**Response:**

```json
{
  "reply": "Lists are mutable and tuples are immutable...",
  "questions_remaining": 9
}
```

**Notes:**
- `conversation_id` identifies the conversation thread. Use the same value across requests to maintain history.
- Each conversation is limited to 10 questions. The 11th request returns HTTP 429.
- Questions unrelated to software engineering are answered with a polite refusal by the agent.

**Error responses:**

| Status | Reason |
|--------|--------|
| 429 | Maximum questions reached for this `conversation_id` |
| 500 | The agent or model raised an unexpected error |

## Run the tests

From the `backend/` directory:

```bash
pytest test_api.py -v
```

No API key is required — `conftest.py` stubs out all external dependencies before any test imports run.

### What the tests cover

| Test | What it verifies |
|------|-----------------|
| `test_chat_returns_reply` | 200 response with correct reply and remaining count |
| `test_questions_remaining_decrements` | Counter decrements correctly each turn |
| `test_separate_conversations_tracked_independently` | Different `conversation_id`s don't affect each other |
| `test_question_limit_returns_429` | 11th request on same conversation is rejected |
| `test_question_limit_does_not_affect_other_conversations` | Exhausted conversation doesn't block a fresh one |
| `test_agent_called_with_correct_thread_id` | `thread_id` in config matches `conversation_id` from request |
| `test_agent_exception_returns_500` | Model errors surface as HTTP 500 |
| `test_failed_call_does_not_increment_count` | Failed requests don't consume a question slot |

## Production notes

`MemorySaver` and the `question_counts` dict are both **in-process memory**. They reset on restart and are not shared across multiple workers. For a multi-worker or multi-instance deployment, replace them with persistent alternatives:

- **Conversation history**: swap `MemorySaver` for `langgraph-checkpoint-postgres` or a Redis-backed checkpointer.
- **Question counts**: store in Redis or a database, keyed by `conversation_id`.
