# Guitar Tutor — Backend

A FastAPI **RAG** service that answers guitar-instruction questions from YouTube transcript data. A user question is embedded, matched against a Pinecone vector store of chunked guitar-lesson transcripts, and the retrieved context is handed to an LLM that answers grounded in what real instructors actually said.

**Stack:** FastAPI · LangChain agent (`create_agent` + LangGraph `MemorySaver`) · Groq / Ollama / Anthropic (configurable LLM) · OpenAI embeddings (`text-embedding-3-small`, 1536-dim) · Pinecone · Postgres (SQLAlchemy 2.0 + Alembic) · Clerk auth · structlog.

## How it works

There are two independent flows: an **offline ingestion pipeline** that builds the corpus, and the **online query path** that serves answers.

### 1. Ingestion pipeline (offline)

Transcripts move through a status lifecycle, tracked in the `status` column of the Postgres `transcript` table. Each stage is a separate, idempotent, re-runnable job that only picks up rows in the right state:

```
scrape ──▶ SCRAPED ──▶ classify ──▶ CLASSIFIED_KEEP ──▶ ingest ──▶ INGESTED
                                 └─▶ CLASSIFIED_REJECT  (never ingested)
```

- **Scrape** — the YouTube scraper lives in `data_gathering/` (a *separate* import root; the contract between it and `backend/` is the Postgres table + the JSON transcript shape, not shared code). It writes each transcript to disk and inserts a `SCRAPED` row.
- **Classify** — a quality gate (see below) that marks each transcript `CLASSIFIED_KEEP` or `CLASSIFIED_REJECT`.
- **Ingest** — for kept transcripts only: clean → chunk (~400-token chunks, ~50-token overlap, via `tiktoken`) → embed (OpenAI) → upsert to Pinecone, then mark `INGESTED`.

#### Classification (the quality gate)

Not every guitar video belongs in the knowledge base. The classifier filters the corpus down to videos that **teach generalizable technique, theory, or concepts**, keeping the retrieval index high-signal. It makes one structured-output LLM call per transcript (a single classification call — *not* an agent) and assigns one category:

| Category | Kept? | Meaning |
|----------|-------|---------|
| `INSTRUCTION` | ✅ | Teaches technique/theory/concepts that transfer across songs |
| `SONG_TUTORIAL` | ❌ | Teaches one specific named song |
| `PERFORMANCE` | ❌ | Playing with little/no teaching |
| `PRODUCT_DEMO` | ❌ | Gear review/demo |
| `OTHER` | ❌ | Vlog, intro, anything else |

**Keep policy** (`classification/policy.py`): a transcript is kept only if `category == INSTRUCTION` **and** `confidence >= 0.7`. The model only categorizes and scores confidence — the keep/reject decision lives in code (`should_keep`), so the threshold can be tuned without touching the prompt. Rejections store the model's one-line justification in the `reject_reason` column for auditing:

```sql
SELECT video_id, title, reject_reason FROM transcript WHERE status = 'CLASSIFIED_REJECT';
```

### 2. Query path (online)

`POST /chat` → authenticate (Clerk) → rate-limit (slowapi) → `Retriever` embeds the question and queries Pinecone for the top-k chunks → the chunk text is folded into an augmented prompt → the LangChain agent answers, grounded in the context → response returns the reply plus the `Source` list (title, instructor, url, timestamp) backing it.

Per-conversation history is kept in a LangGraph `MemorySaver`, keyed by `conversation_id` (the agent's `thread_id`).

## Project structure

```
backend/
  api.py                  # FastAPI app, routes, Clerk auth dependency, rate limiting
  main.py                 # Entry point — configures logging, starts uvicorn
  pipeline.py             # Ingestion orchestrator — classify then ingest (run after scraping)
  agent.py                # LangChain agent (LLM + system prompt + MemorySaver), MAX_QUESTIONS
  llm.py                  # LLM factory (groq | ollama | anthropic), env-driven
  middleware.py           # Request ID + security headers middleware
  logging_config.py       # Structured JSON logging (structlog)
  exceptions.py           # Domain exceptions (transport-independent)
  vector_store.py         # VectorStore protocol + Pinecone implementation, factory
  conftest.py             # Stubs heavy deps so tests need no network/keys
  classification/
    classify.py           # Classifier: build_input, LLM call, main() batch job
    policy.py             # should_keep — the keep/reject decision (MIN_CONFIDENCE)
    test_policy.py        # Pure tests for the keep policy
    test_classify.py      # Pure tests for build_input
  ingestion/
    chunker.py            # filter + ~400-token chunking with overlap (tiktoken)
    ingest.py             # main() — load → skip non-KEEP → chunk → embed → upsert
    test_chunker.py
  embeddings/
    embeddings.py         # EmbeddingProvider protocol + OpenAI implementation, factory
  rag/
    retriever.py          # Retriever — embed query, query Pinecone, format context + sources
  db/
    database.py           # SQLAlchemy Base, Transcript model, Status enum, engine
    db_service.py         # DB operations: add/query transcripts, status transitions
    backfill.py           # One-shot ETL: load disk JSON → DB as SCRAPED
  models/
    chat.py               # /chat request/response models
    classification.py     # Classification result model + Category enum
    transcript.py         # Transcript/Segment validation models (trust boundary)
    query.py              # Pinecone query-response models
    source.py             # Source (citation) model
  alembic/                # Migrations (schema is Alembic-owned)
```

## Prerequisites

- **Python 3.14+**
- **Postgres** — a `docker-compose.yaml` for local Postgres lives in `backend/db/`.
- A `.env` file at the project root (see configuration below). `.env` is gitignored — never commit secrets.

## Install dependencies

From the project root:

```bash
uv sync
```

Installs everything in `pyproject.toml` (fastapi, langchain + provider packages, openai, pinecone, sqlalchemy, alembic, clerk, structlog, …).

## Configuration

All options are environment variables (loaded from `.env`). See `.env.example` for the full list with placeholders.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | **Required.** Postgres connection string (used by the app, Alembic, and the scraper). |
| `LLM_PROVIDER` | `ollama` | `groq`, `ollama`, or `anthropic`. Production uses `groq`. |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Model when `LLM_PROVIDER=groq`. Requires `GROQ_API_KEY`. |
| `OLLAMA_BASE_MODEL` | `llama3.1:8b` | Model when `LLM_PROVIDER=ollama`. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL. |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic`. |
| `EMBEDDING_PROVIDER` | `openai` | Embedding backend. |
| `OPENAI_API_KEY` | — | **Required** for embeddings (`text-embedding-3-small`). |
| `VECTOR_STORE_PROVIDER` | `pinecone` | Vector store backend. |
| `PINECONE_API_KEY` | — | **Required.** Pinecone API key. |
| `PINECONE_INDEX_NAME` | `guitar-rag` | Pinecone index name. |
| `CLERK_SECRET_KEY` | — | **Required** to authenticate `/chat`. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins (also Clerk authorized parties). |
| `RATE_LIMIT` | `20/minute` | Per-IP rate limit on `/chat`. |
| `PORT` | `8000` | Server port. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `JSON_LOGS` | `true` | Set `false` for human-readable console logs in local dev. |

## Database & migrations

The schema is **owned by Alembic** (not `create_all`). From `backend/`:

```bash
alembic upgrade head                                 # apply migrations to the DB
alembic revision --autogenerate -m "describe change" # generate a migration after editing models
```

Always read an autogenerated migration before applying it. The `transcript` table is the single source of truth for the ingestion lifecycle.

## Running the pipeline

All commands run from `backend/`. Intra-package jobs use the `-m` form so `backend/` is on `sys.path`.

```bash
python pipeline.py                 # classify + ingest in one step (the normal entry point)
```

`pipeline.py` orchestrates the two consumer-side stages in order — `run_classify()` then `run_ingest()` — so the classify step can't be forgotten. Each stage is status-gated and idempotent, so re-running is safe. The stages can also be run individually for debugging:

```bash
python -m db.backfill              # one-shot: load existing disk transcripts into the DB as SCRAPED
python -m classification.classify  # classify all SCRAPED rows → CLASSIFIED_KEEP / CLASSIFIED_REJECT
python -m ingestion.ingest         # embed + upsert all CLASSIFIED_KEEP rows → INGESTED
```

The classify job logs each decision (`category`, `confidence`, `reason`) and is safe to re-run — it only touches `SCRAPED` rows. To re-classify everything (e.g. after tuning the prompt or threshold), reset first:

```sql
UPDATE transcript SET status = 'SCRAPED', reject_reason = NULL;
```

> **Note:** the `status` column tracks what is in Pinecone. If you wipe the Pinecone index, roll the affected rows back a state (e.g. `UPDATE transcript SET status = 'CLASSIFIED_KEEP' WHERE status = 'INGESTED'`) before re-running, or the DB and index will be out of sync.

## Running the server

From `backend/`:

```bash
python main.py
```

API at `http://localhost:8000`; Swagger UI at `http://localhost:8000/docs`. For readable local logs:

```bash
JSON_LOGS=false LOG_LEVEL=DEBUG python main.py
```

## API

### `POST /chat`

Requires a Clerk bearer token (`Authorization: Bearer <token>`).

**Request:**

```json
{
  "conversation_id": "my-session-123",
  "message": "How do I combine major and minor pentatonic scales?"
}
```

**Response:**

```json
{
  "reply": "...",
  "sources": [
    {"title": "...", "url": "...", "instructor": "...", "start_time": 42.0, "snippet": "..."}
  ],
  "questions_remaining": 9
}
```

- `conversation_id` is the conversation thread; reuse it across requests to keep history.
- Each conversation is limited to 10 questions (`MAX_QUESTIONS`).
- `sources` are the retrieved chunks backing the answer.

**Error responses:**

| Status | Reason |
|--------|--------|
| 401 | Missing/invalid Clerk authentication |
| 429 | Rate limit exceeded, or max questions reached for this `conversation_id` |
| 500 | Unexpected error in the retriever, agent, or model |

## Logging

Structured JSON by default (structlog), suitable for any aggregator. Every log line in a request carries a `request_id` so a request can be traced across all layers. Third-party logs (uvicorn, langchain) route through the same pipeline.

## Tests

From `backend/`:

```bash
python -m pytest -v                         # whole suite
python -m pytest classification/ -v         # a single package
```

No API keys or network needed: `conftest.py` stubs heavy/external dependencies, and the `/chat` tests use fixtures that bypass auth, disable rate limiting, and mock the retriever. The pure logic (`should_keep`, `build_input`, chunking) is tested directly with no mocks — which is why that logic is deliberately kept separate from its IO.

## Production notes

`MemorySaver` (conversation history) and the `question_counts` dict are **in-process memory** — they reset on restart and aren't shared across workers. For multi-worker/multi-instance deployment, replace with persistent stores:

- **Conversation history** → `langgraph-checkpoint-postgres` or a Redis-backed checkpointer.
- **Question counts** → Redis or a DB keyed by `conversation_id`.

The classify and ingest jobs are designed to be re-runnable and idempotent (status-gated, upserts with `ON CONFLICT DO NOTHING`), so re-processing a partially-ingested corpus is safe.
