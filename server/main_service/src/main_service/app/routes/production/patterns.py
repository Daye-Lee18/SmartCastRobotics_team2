"""Pattern endpoints — 패턴 위치 등록/조회 (Pink GUI #3).

Endpoints:
    POST /api/production/patterns          패턴 등록
    GET  /api/production/patterns          모든 패턴
    GET  /api/production/patterns/{ord_id} 특정 발주의 패턴

2026-04-27: 자동 ptn_loc 매핑 (R/S/O→1/2/3) 은 backend/app/routes/orders.py 의
create_customer_order 가 발주 생성 시점에 처리. 본 엔드포인트는 운영자가 수동
override 하거나 legacy 호출에 대한 응답용.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import Ord, Pattern
from app.schemas.schemas import PatternIn, PatternOut

router = APIRouter(prefix="/api/production", tags=["production"])


@router.post("/patterns", response_model=PatternOut, status_code=201)
def register_pattern(payload: PatternIn, db: Session = Depends(get_db)) -> PatternOut:
    """패턴 위치 등록 (1-6). 발주 1:1 — 동일 ord_id 재등록 시 UPDATE."""
    if not db.get(Ord, payload.ptn_id):
        raise HTTPException(404, f"ord_id={payload.ptn_id} not found")
    existing = db.get(Pattern, payload.ptn_id)
    if existing:
        existing.ptn_loc = payload.ptn_loc
    else:
        existing = Pattern(ptn_id=payload.ptn_id, ptn_loc=payload.ptn_loc)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return PatternOut.model_validate(existing)


@router.get("/patterns", response_model=list[PatternOut])
def list_patterns(db: Session = Depends(get_db)) -> list[PatternOut]:
    return [PatternOut.model_validate(p) for p in db.query(Pattern).all()]


@router.get("/patterns/{ord_id}", response_model=PatternOut)
def get_pattern(ord_id: int, db: Session = Depends(get_db)) -> PatternOut:
    p = db.get(Pattern, ord_id)
    if not p:
        raise HTTPException(404, f"pattern for ord_id={ord_id} not registered")
    return PatternOut.model_validate(p)
