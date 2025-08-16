from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Interaction, Memory
from ..schemas import AnalyticsSummary

router = APIRouter()


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_interactions = db.query(func.count(Interaction.id)).scalar() or 0
    total_memories = db.query(func.count(Memory.id)).scalar() or 0

    rows = db.query(Memory.memory_type, func.count(Memory.id)).group_by(Memory.memory_type).all()
    memories_by_type = {mt: cnt for mt, cnt in rows}

    last_ingest = db.query(func.max(Memory.created_at)).scalar()

    return AnalyticsSummary(
        total_users=total_users,
        total_interactions=total_interactions,
        total_memories=total_memories,
        memories_by_type=memories_by_type,
        last_ingest_time=last_ingest,
    ) 