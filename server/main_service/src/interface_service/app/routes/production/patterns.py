"""Pattern endpoints — 발주↔패턴 등록/조회 (Pink GUI #3).

Endpoints:
    POST /api/production/patterns          패턴 등록
    GET  /api/production/patterns          모든 패턴
    GET  /api/production/patterns/{ord_id} 특정 발주의 패턴

2026-04-27: 자동 ptn_id 매핑 (R/S/O→1/2/3) 은 backend/app/routes/orders.py 의
create_customer_order 가 발주 생성 시점에 처리. 본 엔드포인트는 운영자가 수동
override 하거나 legacy 호출에 대한 응답용.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import Ord, OrdPattern
from app.schemas.schemas import OrdPatternIn, OrdPatternOut

router = APIRouter(prefix="/api/production", tags=["production"])


@router.post("/patterns", response_model=OrdPatternOut, status_code=201)
def register_pattern(payload: OrdPatternIn, db: Session = Depends(get_db)) -> OrdPatternOut:
    """발주↔패턴 등록 (ptn_id 1-3). 발주 1:1 — 동일 ord_id 재등록 시 UPDATE."""
    if not db.get(Ord, payload.ord_id):
        raise HTTPException(404, f"ord_id={payload.ord_id} not found")
    existing = db.get(OrdPattern, payload.ord_id)
    if existing:
        existing.ptn_id = payload.ptn_id
    else:
        existing = OrdPattern(ord_id=payload.ord_id, ptn_id=payload.ptn_id)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return OrdPatternOut.model_validate(existing)


@router.get("/patterns", response_model=list[OrdPatternOut])
def list_patterns(db: Session = Depends(get_db)) -> list[OrdPatternOut]:
    return [OrdPatternOut.model_validate(p) for p in db.query(OrdPattern).all()]


@router.get("/patterns/{ord_id}", response_model=OrdPatternOut)
def get_pattern(ord_id: int, db: Session = Depends(get_db)) -> OrdPatternOut:
    p = db.get(OrdPattern, ord_id)
    if not p:
        raise HTTPException(404, f"pattern for ord_id={ord_id} not registered")
    return OrdPatternOut.model_validate(p)
