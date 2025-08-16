from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Memory, Interaction
from ..schemas import MemoryCreate, MemoryRead, SearchResponseItem
from ..services.mem0_client import mem0_client_singleton

router = APIRouter()


@router.post("/memories", response_model=MemoryRead)
async def add_memory(payload: MemoryCreate, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("user not found")

    mem0_id = mem0_client_singleton.create_memory(
        user_external_id=user.whatsapp_user_id,
        memory_type=payload.memory_type,
        text=payload.text,
        media_path=None,
        labels=payload.labels,
    )

    memory = Memory(
        user_id=user.id,
        interaction_id=None,
        mem0_id=mem0_id,
        memory_type=payload.memory_type,
        title=None,
        text=payload.text,
        labels_json=None,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.get("/memories")
async def search_memories(query: str = Query(...), user_id: int = Query(...), db: Session = Depends(get_db)) -> list[SearchResponseItem]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    results = mem0_client_singleton.search(user_external_id=user.whatsapp_user_id, query=query)
    response: list[SearchResponseItem] = []

    for r in results:
        # Resolve memory from DB using mem0_id if available
        mem0_id = r.get("id") if isinstance(r, dict) else None
        memory: Optional[Memory] = None
        if mem0_id:
            memory = db.query(Memory).filter(Memory.mem0_id == mem0_id, Memory.user_id == user.id).first()
        if not memory:
            continue
        interaction = None
        if memory.interaction_id:
            interaction = db.query(Interaction).filter(Interaction.id == memory.interaction_id).first()
        response.append(
            SearchResponseItem(memory=memory, score=r.get("score"), source_interaction=interaction)
        )

    return response


@router.get("/memories/list", response_model=list[MemoryRead])
async def list_memories(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .all()
    ) 