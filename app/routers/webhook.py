from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Interaction, MediaAsset, Memory
from ..services.media import download_twilio_media, compute_sha256, persist_media
from ..services.media import compute_image_ahash_from_bytes, compute_image_ahash_from_path, hamming_distance
from ..services.transcription import transcribe_audio_file
from ..services.mem0_client import mem0_client_singleton
from ..utils.time_utils import parse_natural_time_range

router = APIRouter()


def _twiml(msg: str) -> str:
    safe = (msg or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<Response><Message>{safe}</Message></Response>"


def _format_memories_reply(memories: list[Memory]) -> str:
    if not memories:
        return "No memories found."
    lines: list[str] = []
    for m in memories[:10]:
        when = m.created_at.isoformat(timespec="seconds") if m.created_at else ""
        snippet = (m.text or "").strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        lines.append(f"- [{when}] ({m.memory_type}) {snippet}")
    return "Here are your memories:\n" + "\n".join(lines)


def _format_search_reply(memories: list[Memory]) -> str:
    if not memories:
        return "No matching memories found."
    lines: list[str] = []
    for m in memories[:5]:
        when = m.created_at.isoformat(timespec="seconds") if m.created_at else ""
        snippet = (m.text or "").strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        lines.append(f"- [{when}] ({m.memory_type}) {snippet}")
    return "Top matches:\n" + "\n".join(lines)


@router.api_route("/webhook", methods=["POST", "GET", "HEAD"])
async def twilio_webhook(
    request: Request,
    From: str = Form(None),
    WaId: str = Form(None),
    Body: str = Form(None),
    NumMedia: str = Form("0"),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
    MessageSid: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    # Respond to Twilio console validation GET/HEAD with simple TwiML
    if request.method in ("GET", "HEAD"):
        return Response(content=_twiml("OK"), media_type="application/xml; charset=utf-8")

    whatsapp_user_id = WaId or (From or "").replace("whatsapp:", "")
    phone_number = From or ""

    # Find or create user
    user = db.query(User).filter(User.whatsapp_user_id == whatsapp_user_id).first()
    if not user:
        user = User(whatsapp_user_id=whatsapp_user_id, phone_number=phone_number)
        db.add(user)
        db.flush()

    # Idempotency: avoid processing same MessageSid twice
    if MessageSid:
        existing = db.query(Interaction).filter(Interaction.twilio_message_sid == MessageSid).first()
        if existing:
            return Response(content=_twiml("Duplicate ignored."), media_type="application/xml; charset=utf-8")

    body_text = (Body or "").strip()
    is_command = body_text.startswith("/")

    # Record interaction regardless of command/media
    interaction = Interaction(
        user_id=user.id,
        twilio_message_sid=MessageSid,
        message_direction="inbound",
        message_type="text" if (not NumMedia or int(NumMedia) == 0) else "media",
        body_text=Body,
    )
    db.add(interaction)
    db.flush()

    # Commands: /list [range], /search <query>
    try:
        if is_command and body_text:
            cmd, *rest = body_text.split(" ", 1)
            arg = rest[0].strip() if rest else ""

            if cmd.lower() == "/list":
                q = db.query(Memory).filter(Memory.user_id == user.id)
                # Time range filter if provided
                if arg:
                    rng = parse_natural_time_range(arg, user.timezone or "UTC")
                    if rng:
                        start, end = rng
                        q = q.filter(and_(Memory.created_at >= start, Memory.created_at <= end))
                memories = q.order_by(Memory.created_at.desc()).limit(10).all()
                reply = _format_memories_reply(memories)
                db.commit()
                return Response(content=_twiml(reply), media_type="application/xml; charset=utf-8")

            if cmd.lower() == "/search":
                query_text = arg
                results: list[Memory] = []
                # Prefer Mem0 if available
                mem0_results = mem0_client_singleton.search(user_external_id=user.whatsapp_user_id, query=query_text)
                if mem0_results:
                    mem0_ids = [r.get("id") for r in mem0_results if isinstance(r, dict) and r.get("id")]
                    if mem0_ids:
                        results = (
                            db.query(Memory)
                            .filter(Memory.user_id == user.id, Memory.mem0_id.in_(mem0_ids))
                            .order_by(Memory.created_at.desc())
                            .limit(5)
                            .all()
                        )
                # Fallback: simple DB LIKE search
                if not results:
                    like = f"%{query_text}%"
                    results = (
                        db.query(Memory)
                        .filter(
                            Memory.user_id == user.id,
                            or_(Memory.text.ilike(like), Memory.title.ilike(like))
                        )
                        .order_by(Memory.created_at.desc())
                        .limit(5)
                        .all()
                    )
                reply = _format_search_reply(results)
                db.commit()
                return Response(content=_twiml(reply), media_type="application/xml; charset=utf-8")

        # If message looks like a query (no media) handle as search
        if body_text and ("?" in body_text) and (not NumMedia or int(NumMedia) == 0):
            query_text = body_text
            results: list[Memory] = []
            mem0_results = mem0_client_singleton.search(user_external_id=user.whatsapp_user_id, query=query_text)
            if mem0_results:
                mem0_ids = [r.get("id") for r in mem0_results if isinstance(r, dict) and r.get("id")]
                if mem0_ids:
                    results = (
                        db.query(Memory)
                        .filter(Memory.user_id == user.id, Memory.mem0_id.in_(mem0_ids))
                        .order_by(Memory.created_at.desc())
                        .limit(5)
                        .all()
                    )
            if not results:
                like = f"%{query_text}%"
                results = (
                    db.query(Memory)
                    .filter(
                        Memory.user_id == user.id,
                        or_(Memory.text.ilike(like), Memory.title.ilike(like))
                    )
                    .order_by(Memory.created_at.desc())
                    .limit(5)
                    .all()
                )
            reply = _format_search_reply(results)
            db.commit()
            return Response(content=_twiml(reply), media_type="application/xml; charset=utf-8")

        # Default: ingest as memory (text or media)
        memory_type = "text"
        memory_text: Optional[str] = body_text or None
        media_path: Optional[str] = None

        if NumMedia and int(NumMedia) > 0 and MediaUrl0:
            # Download media
            content_bytes, content_type = download_twilio_media(MediaUrl0)
            if content_bytes:
                sha256_hex = compute_sha256(content_bytes)
                # Dedup: exact content
                existing_media = db.query(MediaAsset).filter(MediaAsset.sha256_hash == sha256_hex).first()
                if existing_media:
                    media = existing_media
                    media_path = existing_media.local_path
                    return Response(content=_twiml("This media is already saved ✅"), media_type="application/xml; charset=utf-8")
                else:
                    # Perceptual dedup for images (handles recompression/resizing)
                    if content_type and "image" in content_type:
                        new_hash = compute_image_ahash_from_bytes(content_bytes)
                        if new_hash is not None:
                            # Compare with user's prior image assets
                            candidates = (
                                db.query(MediaAsset)
                                .join(Interaction, MediaAsset.interaction_id == Interaction.id)
                                .filter(
                                    Interaction.user_id == user.id,
                                    MediaAsset.content_type.ilike("%image%"),
                                    MediaAsset.local_path.isnot(None),
                                )
                                .order_by(MediaAsset.id.desc())
                                .limit(100)
                                .all()
                            )
                            for cand in candidates:
                                cand_hash = compute_image_ahash_from_path(cand.local_path) if cand.local_path else None
                                if cand_hash is None:
                                    continue
                                if hamming_distance(new_hash, cand_hash) <= 10:
                                    return Response(content=_twiml("This media is already saved ✅"), media_type="application/xml; charset=utf-8")
                    # Persist as new media if not deduped
                    media_path = persist_media(content_bytes, sha256_hex, content_type)
                    media = MediaAsset(
                        interaction_id=interaction.id,
                        media_url=MediaUrl0,
                        local_path=media_path,
                        content_type=content_type,
                        sha256_hash=sha256_hex,
                    )
                    db.add(media)

                if content_type and "image" in content_type:
                    memory_type = "image"
                elif content_type and ("audio" in content_type or "ogg" in content_type):
                    memory_type = "audio"
                    # Attempt transcription
                    transcript = transcribe_audio_file(media_path) if media_path else None
                    if transcript:
                        memory_text = transcript
                else:
                    memory_type = "text"

        # Create memory in Mem0
        mem0_id = mem0_client_singleton.create_memory(
            user_external_id=user.whatsapp_user_id,
            memory_type=memory_type,
            text=memory_text,
            media_path=media_path,
            labels=None,
        )

        memory = Memory(
            user_id=user.id,
            interaction_id=interaction.id,
            mem0_id=mem0_id,
            memory_type=memory_type,
            title=None,
            text=memory_text,
            labels_json=None,
        )
        db.add(memory)
        db.commit()

        # TwiML confirmation message
        return Response(content=_twiml("Memory saved ✅"), media_type="application/xml; charset=utf-8")
    except Exception as exc:
        db.rollback()
        return Response(content=_twiml("There was an error processing your message ❌"), media_type="application/xml; charset=utf-8") 