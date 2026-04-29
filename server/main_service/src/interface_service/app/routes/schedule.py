"""Schedule router — smartcast schema.

엔드포인트:
  GET /api/schedule           모든 발주의 최신 상태 (운영 화면용)
  GET /api/schedule/{ord}     특정 발주 상태 이력
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import Ord, OrdStat
from app.schemas.schemas import OrdStatOut

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("", response_model=list[OrdStatOut])
def list_schedule(db: Session = Depends(get_db)) -> list[OrdStatOut]:
    """모든 발주의 최신 ord_stat (1건씩)."""
    out: list[OrdStatOut] = []
    for o in db.query(Ord).order_by(desc(Ord.created_at)).all():
        latest = (
            db.query(OrdStat)
            .filter(OrdStat.ord_id == o.ord_id)
            .order_by(desc(OrdStat.updated_at))
            .first()
        )
        if latest:
            out.append(OrdStatOut.model_validate(latest))
    return out


@router.get("/{ord_id}", response_model=list[OrdStatOut])
def order_status_history(ord_id: int, db: Session = Depends(get_db)) -> list[OrdStatOut]:
    if not db.get(Ord, ord_id):
        raise HTTPException(404, f"ord_id={ord_id} not found")
    rows = (
        db.query(OrdStat).filter(OrdStat.ord_id == ord_id).order_by(desc(OrdStat.updated_at)).all()
    )
    return [OrdStatOut.model_validate(r) for r in rows]
