from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Interaction
from ..schemas import InteractionRead

router = APIRouter()


@router.get("/interactions/recent", response_model=list[InteractionRead])
async def recent_interactions(limit: int = Query(10, ge=1, le=100), user_id: int = Query(...), db: Session = Depends(get_db)):
    return (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
        .all()
    ) 