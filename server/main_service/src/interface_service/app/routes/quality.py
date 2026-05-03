"""Quality router — smartcast schema.

엔드포인트:
  GET  /api/quality/inspections           insp_task_txn 목록 (필터: ord_id, item_id)
  GET  /api/quality/summary               핑크 GUI #6: 발주별 GP/DP/미검사 요약
  GET  /api/quality/summary/{ord_id}      특정 발주 요약
  POST /api/quality/inspections/{txn}/result  검사 결과 업데이트 (AI service 콜백)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import InspStat, InspTaskTxn, ItemStat, Ord
from app.schemas.schemas import InspectionSummary, InspTaskTxnOut

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.get("/inspections", response_model=list[InspTaskTxnOut])
def list_inspections(
    ord_id: int | None = None,
    item_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[InspTaskTxnOut]:
    q = db.query(InspTaskTxn, InspStat).outerjoin(InspStat, InspStat.insp_txn_id == InspTaskTxn.txn_id)
    if item_id is not None:
        q = q.filter(InspTaskTxn.item_stat_id == item_id)
    if ord_id is not None:
        q = q.join(ItemStat, ItemStat.item_stat_id == InspTaskTxn.item_stat_id).filter(ItemStat.ord_id == ord_id)
    out: list[InspTaskTxnOut] = []
    for txn, stat in q.order_by(desc(InspTaskTxn.req_at)).limit(200).all():
        result = None
        if stat and stat.final_result == "GP":
            result = True
        elif stat and stat.final_result == "DP":
            result = False
        out.append(
            InspTaskTxnOut.model_validate(
                {
                    "txn_id": txn.txn_id,
                    "item_id": txn.item_stat_id,
                    "res_id": txn.res_id,
                    "txn_stat": txn.txn_stat,
                    "result": result,
                    "req_at": txn.req_at,
                    "start_at": txn.start_at,
                    "end_at": txn.end_at,
                }
            )
        )
    return out


@router.get("/summary", response_model=list[InspectionSummary])
def inspection_summary_all(db: Session = Depends(get_db)) -> list[InspectionSummary]:
    """Pink GUI #6: 발주별 검사 요약.

    각 ord_id 의 item 총수 / 검사 완료 / 양품(GP) / 불량(DP) / 미검사 카운트.
    """
    return _build_summaries(db, ord_id=None)


@router.get("/summary/{ord_id}", response_model=InspectionSummary)
def inspection_summary_one(ord_id: int, db: Session = Depends(get_db)) -> InspectionSummary:
    rows = _build_summaries(db, ord_id=ord_id)
    if not rows:
        if not db.get(Ord, ord_id):
            raise HTTPException(404, f"ord_id={ord_id} not found")
        return InspectionSummary(
            ord_id=ord_id,
            total_items=0,
            inspected=0,
            good_count=0,
            defective_count=0,
            pending_count=0,
        )
    return rows[0]


def _build_summaries(db: Session, ord_id: int | None) -> list[InspectionSummary]:
    """v21 item_stat.result 기준 발주별 검사 요약."""
    base = (
        db.query(
            ItemStat.ord_id.label("ord_id"),
            func.count(ItemStat.item_stat_id).label("total_items"),
            func.count(ItemStat.item_stat_id).filter(ItemStat.result.isnot(None)).label("inspected"),
            func.count(ItemStat.item_stat_id).filter(ItemStat.result.is_(True)).label("good_count"),
            func.count(ItemStat.item_stat_id).filter(ItemStat.result.is_(False)).label("defective_count"),
        )
        .group_by(ItemStat.ord_id)
    )
    if ord_id is not None:
        base = base.filter(ItemStat.ord_id == ord_id)
    out: list[InspectionSummary] = []
    for r in base.all():
        pending = max(0, (r.total_items or 0) - (r.inspected or 0))
        out.append(
            InspectionSummary(
                ord_id=r.ord_id,
                total_items=r.total_items or 0,
                inspected=r.inspected or 0,
                good_count=r.good_count or 0,
                defective_count=r.defective_count or 0,
                pending_count=pending,
            )
        )
    return out


# -------------------------------------------------------------------------
# Legacy compat endpoints
# -------------------------------------------------------------------------


@router.get("/stats")
def quality_stats_summary(db: Session = Depends(get_db)) -> dict:
    """legacy /api/quality/stats — 전체 검사 누적 합계."""
    inspected = db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.isnot(None)).scalar() or 0
    good = db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.is_(True)).scalar() or 0
    defective = db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.is_(False)).scalar() or 0
    pending = db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.is_(None)).scalar() or 0
    rate = (good / inspected * 100.0) if inspected else 0.0
    return {
        "inspected": inspected,
        "good": good,
        "defective": defective,
        "pending": pending,
        "good_rate_pct": round(rate, 2),
    }


@router.get("/standards")
def list_standards() -> list[dict]:
    """legacy 검사 기준 — 별도 테이블 없음, 빈 배열."""
    return []


@router.get("/sorter-logs")
def list_sorter_logs() -> list[dict]:
    """legacy sorter — equip_task_txn(task_type='ToINSP') 로 통합됨, 빈 배열."""
    return []


@router.get("/sorter")
def get_sorter_state() -> dict:
    """legacy sorter 상태 — 미연동, 정적 응답."""
    return {"status": "idle", "items_processed": 0, "last_action_at": None}


@router.get("/trend")
def quality_trend(hours: int = 24, db: Session = Depends(get_db)) -> list[dict]:
    """err_log 시간대별 트렌드 (equip + trans 합계)."""
    from app.services.timescale import err_log_trend

    return err_log_trend(db, hours=hours)


@router.get("/defect-types")
def quality_defect_types() -> list[dict]:
    """legacy 불량 유형 분포 — 미분류 카테고리, 빈 배열."""
    return []


@router.get("/vs-defects")
def quality_vs_defects() -> list[dict]:
    """legacy 생산 vs 불량 — 빈 배열."""
    return []


@router.get("/vision-feed")
def quality_vision_feed() -> dict:
    """legacy 비전 카메라 피드 — Jetson 미연동, 빈 응답."""
    return {"frames": [], "status": "disconnected"}


@router.post("/inspections/{txn_id}/result", response_model=InspTaskTxnOut)
def update_inspection_result(
    txn_id: int,
    result: bool = Query(..., description="True=GP, False=DP"),
    db: Session = Depends(get_db),
) -> InspTaskTxnOut:
    """AI 검사 결과 업데이트. v21 insp_stat.final_result + item_stat.result 를 갱신한다."""
    txn = db.get(InspTaskTxn, txn_id)
    if not txn:
        raise HTTPException(404, f"insp_task_txn={txn_id} not found")
    txn.txn_stat = "SUCC"
    txn.end_at = datetime.utcnow()
    stat = db.get(InspStat, txn_id)
    if stat is None:
        stat = InspStat(insp_txn_id=txn_id, item_stat_id=txn.item_stat_id)
        db.add(stat)
    stat.item_stat_id = txn.item_stat_id
    stat.final_result = "GP" if result else "DP"
    if txn.item_stat_id:
        item = db.get(ItemStat, txn.item_stat_id)
        if item:
            item.result = result
    db.commit()
    db.refresh(txn)
    return InspTaskTxnOut.model_validate(
        {
            "txn_id": txn.txn_id,
            "item_id": txn.item_stat_id,
            "res_id": txn.res_id,
            "txn_stat": txn.txn_stat,
            "result": result,
            "req_at": txn.req_at,
            "start_at": txn.start_at,
            "end_at": txn.end_at,
        }
    )
