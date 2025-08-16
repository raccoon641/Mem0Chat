# Mem0Chat

Personal multimodal memory agent on WhatsApp

## Overview

Mem0Chat is a FastAPI-based backend that turns WhatsApp into your personal memory assistant. It ingests WhatsApp messages and media via Twilio, persists interactions and media locally, transcribes audio with Whisper, and creates/searches memories using the Mem0 SDK. It also exposes simple analytics and enrichment endpoints.

- WhatsApp → Twilio → FastAPI webhook → Persist interaction/media → Optional transcription → Create memory in Mem0 → Send confirmation back

For a deeper breakdown of every file and function, see `DOCS.md`.

## Features

- Ingest WhatsApp messages (text and media) via Twilio
- Deduplicate media by SHA-256 and persist locally
- Transcribe audio using Whisper (local model) or swap to an API-based transcriber
- Create and search memories using Mem0 (with graceful fallbacks if not configured)
- Simple analytics endpoints and recent interaction listing
- SQLite by default; easy to swap to any SQLAlchemy-compatible DB

## Architecture

- Framework: FastAPI
- Data: SQLAlchemy ORM + SQLite (default)
- Integrations: Twilio (WhatsApp), Mem0 SDK, Whisper (local)
- Configuration: Pydantic Settings via `.env`

Key modules:
- `app/routers/webhook.py`: Twilio inbound webhook → ingestion + processing
- `app/routers/memories.py`: Create/search/list memories
- `app/routers/interactions.py`: Recent interactions
- `app/routers/analytics.py`: Basic counts and last ingest time
- `app/services/`: Mem0 client, media download/persist, transcription, outbound Twilio messaging

See `DOCS.md` for a full directory and function reference.

## Requirements

- Python 3.10+
- SQLite (bundled with Python) or another SQL database supported by SQLAlchemy
- FFmpeg (required for local Whisper transcription)
- Twilio account with WhatsApp Sandbox or WhatsApp Business setup
- Mem0 API key (optional for running basic flows; enables memory creation/search)

## Quickstart

1) Clone and enter the project
```bash
git clone <your-fork-or-repo-url> mem0chat && cd mem0chat
```

2) Create a virtual environment and install dependencies
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3) Create `.env`
```bash
cp .env.example .env  # if you create one, otherwise make a new file with the keys below
```
Minimum variables (see all below):
```env
APP_HOST=0.0.0.0
APP_PORT=8000
ENV=dev
DEFAULT_TIMEZONE=UTC
STORAGE_DIR=./data
DATABASE_URL=sqlite:///./data/app.db

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886  # or your enabled WhatsApp number

# Optional, but recommended
PUBLIC_BASE_URL=https://<your-ngrok-or-deployed-host>

# Mem0
MEM0_API_KEY=your_mem0_api_key

# Optional if using API-based transcription instead of local Whisper
OPENAI_API_KEY=your_openai_api_key
```

4) Initialize the database (auto-creates on first run) or apply DDL manually
```bash
mkdir -p ./data
sqlite3 ./data/app.db < sql/schema.sql
```

5) Start the server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6) Expose publicly and configure Twilio webhook
- Use a tunnel like ngrok and set `PUBLIC_BASE_URL`
- Configure Twilio WhatsApp webhook to POST to: `https://<PUBLIC_BASE_URL>/webhook`

## Environment Variables

- `APP_HOST`, `APP_PORT`, `ENV`, `DEFAULT_TIMEZONE`, `STORAGE_DIR`, `DATABASE_URL`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`
- `PUBLIC_BASE_URL` (optional)
- `MEM0_API_KEY`
- `OPENAI_API_KEY` (optional)

Notes:
- `STORAGE_DIR` is used for persisted media (e.g., `./data/media`).
- `DATABASE_URL` defaults nicely to SQLite; swap to Postgres/MySQL as needed (e.g., `postgresql+psycopg://...`).

## Using the API

Once running locally, the API will be available at `http://localhost:8000`.

### Create a memory (without Twilio)
```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_external_id": "user:wa:+12345550000",
    "memory_type": "note",
    "text": "Remember to buy oat milk",
    "labels": ["groceries", "personal"]
  }'
```

### Search memories
```bash
curl "http://localhost:8000/memories?user_id=user:wa:+12345550000&query=milk"
```

### List all memories (newest first)
```bash
curl "http://localhost:8000/memories/list?user_id=user:wa:+12345550000"
```

### Recent interactions
```bash
curl "http://localhost:8000/interactions/recent?user_id=user:wa:+12345550000&limit=20"
```

### Analytics summary
```bash
curl "http://localhost:8000/analytics/summary"
```

## WhatsApp + Twilio Flow

1) User sends a message/media to your WhatsApp number
2) Twilio forwards it to your webhook (`POST /webhook`)
3) The app:
   - Upserts the `User`
   - Ensures idempotency by `twilio_message_sid`
   - Persists the `Interaction` and downloads any media securely from Twilio
   - Deduplicates media via SHA-256 and persists it under `STORAGE_DIR`
   - If audio, attempts Whisper transcription
   - Creates a `Memory` via Mem0 (if configured) and links it to the `Interaction`
   - Sends a confirmation message back via Twilio

## Data Model (high level)

- `User`: WhatsApp user; timezone-aware
- `Interaction`: Inbound/outbound messages and metadata
- `MediaAsset`: Persisted media files with dedup by hash
- `Memory`: Created in Mem0 and linked to its source interaction

See `sql/schema.sql` and `app/models.py` for exact fields and relationships.

## Transcription

- By default, `app/services/transcription.py` loads a local Whisper `base` model lazily. You need FFmpeg installed.
- You can swap to an API-based transcriber and set `OPENAI_API_KEY` if preferred.

## Mem0 Integration

- Configure `MEM0_API_KEY` to enable memory creation and semantic search.
- If Mem0 is not configured, the app will operate with graceful fallbacks (e.g., storing text locally without remote memory creation/search).

## Development

- Run with auto-reload via Uvicorn as shown above.
- Seed script: `python scripts/seed.py` (uses `app/database.py` helpers).
- For production, prefer Gunicorn/Uvicorn workers behind a reverse proxy and use proper migrations (Alembic) instead of `Base.metadata.create_all`.

## Troubleshooting

- Twilio webhook not firing: verify public URL, Twilio webhook configuration, and that your server is reachable from the public internet.
- Media download fails: ensure `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN` are correct and `PUBLIC_BASE_URL` is set when Twilio needs callback resolution.
- Whisper errors: ensure FFmpeg is installed and accessible in your PATH; large models require more memory.
- Mem0 not creating/searching memories: verify `MEM0_API_KEY`; the app will still run with reduced functionality.
- SQLite lock errors: avoid multiple writers or switch to a server DB for multi-process concurrency.

## References

- Detailed file-by-file documentation: `DOCS.md`
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Twilio WhatsApp: https://www.twilio.com/whatsapp
- Mem0: https://mem0.ai/
- Whisper: https://github.com/openai/whisper

## License

No license has been specified yet. Add a `LICENSE` file to clarify usage and distribution terms.
