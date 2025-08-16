## WhatsApp Memory Assistant (Python FastAPI)

This document describes the project skeleton, with every file and function explained.

### Project Structure

- `requirements.txt`: Python dependencies.
- `app/`: Backend application package.
  - `__init__.py`: Makes `app` a package.
  - `config.py`: App settings via environment variables.
  - `database.py`: SQLAlchemy engine/session setup and helpers.
  - `models.py`: SQLAlchemy ORM models: `User`, `Interaction`, `MediaAsset`, `Memory`.
  - `schemas.py`: Pydantic models for request/response payloads.
  - `main.py`: FastAPI application factory and router registration.
  - `routers/`: API endpoints.
    - `webhook.py`: `POST /webhook` for Twilio WhatsApp inbound.
    - `memories.py`: `POST /memories`, `GET /memories`, `GET /memories/list`.
    - `interactions.py`: `GET /interactions/recent`.
    - `analytics.py`: `GET /analytics/summary`.
  - `services/`: Integrations and domain services.
    - `mem0_client.py`: Wrapper for Mem0 SDK.
    - `transcription.py`: Whisper-based transcription loader and function.
    - `media.py`: Twilio media download and persistence utilities.
    - `twilio_messaging.py`: Helper to send WhatsApp messages via Twilio.
  - `utils/`: Generic utilities.
    - `time_utils.py`: Timezone helpers and natural time range parsing.
- `sql/schema.sql`: DDL reflecting the ORM models.
- `scripts/seed.py`: Minimal seed script.

### Environment Variables

Configure `.env` (not committed) using the following keys:
- `APP_HOST`, `APP_PORT`, `ENV`, `DEFAULT_TIMEZONE`, `STORAGE_DIR`, `DATABASE_URL`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`
- `PUBLIC_BASE_URL` (optional)
- `MEM0_API_KEY`
- `OPENAI_API_KEY` (optional if using API-based transcription instead of local Whisper)

### Files and Functions

#### `app/config.py`
- `Settings`: Pydantic settings sourcing environment variables.
- `get_settings()`: Returns a cached `Settings` instance and ensures storage/DB paths exist.

#### `app/database.py`
- `Base`: Declarative base for ORM models.
- `_create_engine_url()`: Returns DB URL from settings.
- `_create_engine()`: Creates a SQLAlchemy engine with SQLite-specific args.
- `engine`: Shared engine instance.
- `SessionLocal`: Session factory.
- `get_db()`: FastAPI dependency yielding a session per request.
- `db_session()`: Context manager for manual scripts (commit/rollback semantics).

#### `app/models.py`
- `User`: Represents a WhatsApp user. Fields: `whatsapp_user_id`, `phone_number`, `timezone`, timestamps. Relationships: `interactions`, `memories`.
- `Interaction`: Stores inbound/outbound messages. Fields: `twilio_message_sid` (unique for idempotency), `message_direction` (inbound/outbound), `message_type`, `body_text`, `occurred_at`, `created_at`. Relationships: `user`, `media_assets`, `memory`.
- `MediaAsset`: Persisted media files with `sha256_hash` unique for deduplication; fields: `media_url`, `local_path`, `content_type`, `width_px`, `height_px`, `duration_seconds`, timestamps. Relationship: `interaction`.
- `Memory`: A memory persisted to Mem0 and linked to source `interaction`. Fields: `mem0_id`, `memory_type`, `title`, `text`, `labels_json`, `created_at`. Relationships: `user`, `interaction`.

#### `app/schemas.py`
- `UserCreate`, `UserRead`: I/O schemas for users.
- `InteractionRead`: Read model for interactions.
- `MemoryCreate`: Inbound payload for new memory via API. Fields: `memory_type` (one of `text`/`image`/`audio`), `text` (optional), `media_url` (optional), `labels` (optional).
- `MemoryRead`: Outbound memory representation.
- `SearchResponseItem`: Combines memory with an optional search score and source interaction.
- `AnalyticsSummary`: Aggregated counts and last ingest time.

#### `app/services/mem0_client.py`
- `Mem0Client`: Wraps the Mem0 SDK.
  - `is_configured()`: Indicates if SDK is available.
  - `create_memory(user_external_id, memory_type, text, media_path, labels)`: Creates a memory; returns `mem0_id` or `None` on fallback.
  - `search(user_external_id, query)`: Searches memories; returns a list of results or an empty list on fallback.
- `mem0_client_singleton`: Reusable instance for app code.

#### `app/services/transcription.py`
- `_load_model()`: Lazily loads Whisper `base` model.
- `transcribe_audio_file(file_path)`: Returns transcription text or `None` if Whisper is unavailable.

#### `app/services/media.py`
- `compute_sha256(content_bytes)`: Returns content hash for deduplication.
- `download_twilio_media(media_url)`: Downloads media using Twilio Basic auth; returns `(bytes, content_type)` or `(None, None)`.
- `persist_media(content_bytes, sha256_hex, content_type)`: Stores media to disk under `STORAGE_DIR/media` and returns file path.
- Perceptual image dedup utilities (aHash):
  - `compute_image_ahash_from_bytes(content_bytes)`: Returns 64-bit aHash integer or `None`.
  - `compute_image_ahash_from_path(path)`: Returns 64-bit aHash integer or `None`.
  - `hamming_distance(a, b)`: Hamming distance between two 64-bit hashes.

#### `app/services/twilio_messaging.py`
- `send_whatsapp_message(to_phone_e164, body)`: Sends WhatsApp messages via the Twilio REST API; returns message SID or `None`.

#### `app/utils/time_utils.py`
- `now_tz(tz_name)`: Current time in a timezone.
- `parse_natural_time_range(text, tz_name)`: Parses phrases like “last week” into a `(start, end)` pair.

#### `app/routers/webhook.py`
- `POST /webhook`: Handles Twilio inbound webhook. Also responds to `GET`/`HEAD` with a simple TwiML `OK` for validation.
  - Creates or finds a `User` using `WaId`/`From`.
  - Idempotency check using `MessageSid`.
  - Persists `Interaction` and downloads media if present.
  - Media deduplication:
    - Exact content dedup via SHA-256.
    - Perceptual dedup for images using aHash + Hamming distance (near-duplicates avoided).
  - If audio, attempts Whisper transcription.
  - Creates `Memory` via Mem0 and stores linkage.
  - Commands supported:
    - `/list [natural time range]` — optionally filter by phrases like “last week”.
    - `/search <query>` — uses Mem0 search if available, otherwise DB fallback search.
  - Heuristic search: question-like text (containing `?` and no media) is treated as a search.
  - Returns TwiML responses (e.g., “Memory saved ✅”, “Duplicate ignored.”).

#### `app/routers/memories.py`
- `POST /memories`: Adds a memory for a user, optionally with labels; links to Mem0. Requires `user_id` query parameter and a `MemoryCreate` payload.
- `GET /memories?query=...&user_id=...`: Searches Mem0 and enriches with DB interaction context.
- `GET /memories/list?user_id=...`: Lists all memories for a user, newest first.

#### `app/routers/interactions.py`
- `GET /interactions/recent?limit=...&user_id=...`: Returns recent interactions for a user.

#### `app/routers/analytics.py`
- `GET /analytics/summary`: Returns simple stats: totals by entity, by memory type, last ingest time.

### Running Locally

1. Create a virtual environment and install deps:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
2. Create a `.env` based on the keys in this doc.
3. Initialize the database tables on first run (done automatically on app start), or apply SQL DDL:
```bash
sqlite3 ./data/app.db < sql/schema.sql
```
4. Start the server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
5. Expose publicly (e.g., with `ngrok`) and configure your Twilio WhatsApp sandbox webhook to `POST https://<public>/webhook`.

### Notes on Idempotency, Deduplication, and Timezones
- Idempotency: `interactions.twilio_message_sid` is unique to prevent duplicate processing.
- Media deduplication: `media_assets.sha256_hash` unique constraint; identical media is re-referenced. For images, perceptual near-duplicates are also filtered using aHash/Hamming distance.
- Timezone-aware queries: Utilities provided to interpret phrases like “last week” in a user’s timezone.

### Caveats
- Mem0 SDK integration is wrapped with fallbacks if the library/key is not available.
- Whisper model loads lazily and requires local model weights; you can replace with an API-based transcriber if preferred.
- For production, use Alembic migrations instead of `Base.metadata.create_all`. 