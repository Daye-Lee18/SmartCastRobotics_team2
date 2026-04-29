"""Production scheduling endpoints — 우선순위 계산 + 큐 등록.

Endpoints:
    GET  /api/production/schedule/jobs           생산 대기열 (APPR/MFG)
    POST /api/production/schedule/calculate      우선순위 계산 (dry-run)
    POST /api/production/schedule/start          큐 등록 (ord_stat MFG transition)
    GET  /api/production/schedule/priority-log   우선순위 변경 이력 (현재 빈 배열)

⚠️ /schedule/start 는 ord_stat MFG 만 transition. **Item / EquipTaskTxn 생성 없음**.
실제 라인 투입은 /api/production/start (lifecycle.py) 가 처리.
2026-04-27 ApiClient 동명 메서드 critical 픽스 후 라벨 명확화: 큐 등록 vs 라인 투입.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import Ord, OrdStat

from ._helpers import (
    ScheduleOrderIdsIn,
    _latest_ord_stat,
    _parse_ord_id,
    _priority_result,
    _virtual_production_job,
)

router = APIRouter(prefix="/api/production", tags=["production"])


@router.get("/schedule/jobs")
def production_schedule_jobs(db: Session = Depends(get_db)) -> list[dict]:
    """smartcast 생산 대기열.

    legacy ProductionJob 테이블은 smartcast 스키마에 없으므로 latest ord_stat 이
    APPR/MFG 인 주문을 PyQt/웹 호환 ProductionJob shape 로 투영한다.
    """
    rows: list[dict] = []
    candidates = db.query(Ord).order_by(desc(Ord.created_at)).all()
    rank = 1
    for ord_obj in candidates:
        if _latest_ord_stat(db, ord_obj.ord_id) not in {"APPR", "MFG"}:
            continue
        rows.append(_virtual_production_job(db, ord_obj, rank=rank))
        rank += 1
    return rows


@router.post("/schedule/calculate")
def production_schedule_calculate(
    payload: ScheduleOrderIdsIn,
    db: Session = Depends(get_db),
) -> dict:
    if not payload.order_ids:
        raise HTTPException(400, "order_ids is required")
    ord_ids = [_parse_ord_id(raw) for raw in payload.order_ids]
    orders = db.query(Ord).filter(Ord.ord_id.in_(ord_ids)).all()
    if not orders:
        raise HTTPException(404, "selected orders not found")
    allowed = {"APPR", "MFG"}
    results = [
        _priority_result(db, ord_obj)
        for ord_obj in orders
        if _latest_ord_stat(db, ord_obj.ord_id) in allowed
    ]
    results.sort(key=lambda r: float(r.get("total_score", 0)), reverse=True)
    for idx, result in enumerate(results, start=1):
        result["rank"] = idx
    return {"results": results}


@router.post("/schedule/start")
def production_schedule_start(
    payload: ScheduleOrderIdsIn,
    db: Session = Depends(get_db),
) -> list[dict]:
    """웹 생산 승인: APPR 주문을 PyQt 생산계획 풀(MFG)로 등록.

    ⚠️ 본 엔드포인트는 **큐 등록만 함**. Item/EquipTaskTxn 생성 없음.
    실제 라인 투입은 PyQt 의 [실시간 운영 모니터링] 페이지에서 /api/production/start
    호출이 담당 (Item + EquipTaskTxn(RA1, MM, QUE) 생성).
    """
    if not payload.order_ids:
        raise HTTPException(400, "order_ids is required")
    ord_ids = [_parse_ord_id(raw) for raw in payload.order_ids]
    jobs: list[dict] = []
    for rank, ord_id in enumerate(ord_ids, start=1):
        ord_obj = db.get(Ord, ord_id)
        if ord_obj is None:
            raise HTTPException(404, f"ord_id={ord_id} not found")
        latest = _latest_ord_stat(db, ord_id)
        if latest not in {"APPR", "MFG"}:
            raise HTTPException(
                400,
                f"ord_id={ord_id} must be APPR/MFG before production approval; current={latest}",
            )
        if latest != "MFG":
            db.add(OrdStat(ord_id=ord_id, ord_stat="MFG"))
        jobs.append(_virtual_production_job(db, ord_obj, rank=rank))
    db.commit()
    return jobs


@router.get("/schedule/priority-log")
def production_schedule_priority_log() -> list[dict]:
    """우선순위 변경 이력 — 현재 미구현, 빈 배열 반환."""
    return []
