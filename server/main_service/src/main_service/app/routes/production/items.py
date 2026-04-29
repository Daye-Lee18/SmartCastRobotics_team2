"""Item / Equipment 조회 endpoints.

Endpoints:
    GET /api/production/items                 item 목록 (필터: ord_id)
    GET /api/production/items/{item}/pp       item 별 필요 후처리 (Pink GUI #4)
    GET /api/production/equip-tasks           equip_task_txn 목록
    GET /api/production/equip-stats           res 별 최신 equip_stat
    GET /api/production/equipment             res + 최신 equip_stat 통합 (legacy)
    GET /api/production/stages                zone 별 진행중 item 수 (legacy)
    GET /api/production/metrics               최근 7일 일별 item 생성 수 (legacy)
    GET /api/production/order-item-progress   발주별 item stat 분포 (Next.js/PyQt 차트)

전부 read-only. write 는 lifecycle.py / patterns.py 가 담당.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Equip,
    EquipStat,
    EquipTaskTxn,
    Item,
    Ord,
    OrdPpMap,
    PpOption,
    PpTaskTxn,
    Res,
    Zone,
)
from app.schemas.schemas import (
    EquipStatOut,
    EquipTaskTxnOut,
    ItemOut,
    ItemPpRequirements,
    PpOptionOut,
    PpTaskTxnOut,
)

router = APIRouter(prefix="/api/production", tags=["production"])


# -----------------------------------------------------------------------------
# Item / Equipment views
# -----------------------------------------------------------------------------


@router.get("/items", response_model=list[ItemOut])
def list_items(
    ord_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ItemOut]:
    q = db.query(Item)
    if ord_id is not None:
        q = q.filter(Item.ord_id == ord_id)
    return [ItemOut.model_validate(i) for i in q.order_by(desc(Item.updated_at)).all()]


@router.get("/equip-tasks", response_model=list[EquipTaskTxnOut])
def list_equip_tasks(
    res_id: str | None = None, db: Session = Depends(get_db)
) -> list[EquipTaskTxnOut]:
    q = db.query(EquipTaskTxn)
    if res_id:
        q = q.filter(EquipTaskTxn.res_id == res_id)
    return [
        EquipTaskTxnOut.model_validate(t)
        for t in q.order_by(desc(EquipTaskTxn.req_at)).limit(100).all()
    ]


@router.get("/equip-stats", response_model=list[EquipStatOut])
def list_equip_stats(db: Session = Depends(get_db)) -> list[EquipStatOut]:
    """res별 가장 최근 equip_stat. 운영자 모니터링용."""
    res_ids = [r.res_id for r in db.query(Res).all()]
    out: list[EquipStatOut] = []
    for rid in res_ids:
        latest = (
            db.query(EquipStat)
            .filter(EquipStat.res_id == rid)
            .order_by(desc(EquipStat.updated_at))
            .first()
        )
        if latest:
            out.append(EquipStatOut.model_validate(latest))
    return out


# -----------------------------------------------------------------------------
# Legacy compat — PyQt/Next.js 가 호출하는 추가 endpoint
# -----------------------------------------------------------------------------


@router.get("/equipment")
def list_equipment(db: Session = Depends(get_db)) -> list[dict]:
    """legacy /api/production/equipment 호환. res + equip_stat 최신 합치기."""
    out: list[dict] = []
    res_rows = db.query(Res).all()
    for r in res_rows:
        latest = (
            db.query(EquipStat)
            .filter(EquipStat.res_id == r.res_id)
            .order_by(desc(EquipStat.updated_at))
            .first()
        )
        zone_id = None
        e = db.get(Equip, r.res_id)
        if e:
            zone_id = e.zone_id
        out.append(
            {
                "res_id": r.res_id,
                "res_type": r.res_type,
                "model_nm": r.model_nm,
                "zone_id": zone_id,
                "cur_stat": latest.cur_stat if latest else None,
                "err_msg": latest.err_msg if latest else None,
                "updated_at": latest.updated_at.isoformat()
                if (latest and latest.updated_at)
                else None,
            }
        )
    return out


@router.get("/stages")
def list_stages(db: Session = Depends(get_db)) -> list[dict]:
    """legacy /api/production/stages 호환. zone 별 진행중 item 수."""
    out: list[dict] = []
    for z in db.query(Zone).order_by(Zone.zone_id).all():
        # 단순화: 해당 zone 의 res 에 점유된 item 수
        in_progress = (
            db.query(func.count(Item.item_id))
            .filter(
                Item.cur_stat.in_(
                    ["MM", "POUR", "DM", "PP", "INSP", "PA", "PICK", "SHIP", "ToINSP"]
                )
            )
            .scalar()
            or 0
        )
        out.append(
            {
                "zone_id": z.zone_id,
                "zone_nm": z.zone_nm,
                "in_progress_count": in_progress,
            }
        )
    return out


@router.get("/metrics")
def production_metrics(db: Session = Depends(get_db)) -> list[dict]:
    """legacy /api/production/metrics 호환. 최근 7 일간 일별 item 생성 수."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    out: list[dict] = []
    for d_offset in range(6, -1, -1):
        day = today - timedelta(days=d_offset)
        nxt = day + timedelta(days=1)
        produced = (
            db.query(func.count(Item.item_id))
            .filter(Item.updated_at >= day, Item.updated_at < nxt)
            .scalar()
            or 0
        )
        out.append(
            {
                "date": day.date().isoformat(),
                "produced": produced,
            }
        )
    return out


@router.get("/order-item-progress")
def order_item_progress(db: Session = Depends(get_db)) -> list[dict]:
    """발주별 item 진행 상태 분포 (Next.js / PyQt 차트용)."""
    out: list[dict] = []
    for o in db.query(Ord).all():
        items = db.query(Item).filter(Item.ord_id == o.ord_id).all()
        stat_counts: dict[str, int] = {}
        for it in items:
            key = it.cur_stat or "UNKNOWN"
            stat_counts[key] = stat_counts.get(key, 0) + 1
        out.append(
            {
                "ord_id": o.ord_id,
                "total_items": len(items),
                "by_stat": stat_counts,
            }
        )
    return out


# -----------------------------------------------------------------------------
# Pink GUI #4 — item별 필요 후처리 표시
# -----------------------------------------------------------------------------


@router.get("/items/{item_id}/pp", response_model=ItemPpRequirements)
def item_pp_requirements(item_id: int, db: Session = Depends(get_db)) -> ItemPpRequirements:
    """item 별 필요한 후처리 옵션 + pp_task_txn 진행상태."""
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, f"item_id={item_id} not found")
    pp_opts = (
        db.query(PpOption)
        .join(OrdPpMap, OrdPpMap.pp_id == PpOption.pp_id)
        .filter(OrdPpMap.ord_id == item.ord_id)
        .all()
    )
    txns = (
        db.query(PpTaskTxn)
        .filter(PpTaskTxn.item_id == item_id)
        .order_by(desc(PpTaskTxn.req_at))
        .all()
    )
    return ItemPpRequirements(
        item_id=item_id,
        ord_id=item.ord_id,
        pp_options=[PpOptionOut.model_validate(p) for p in pp_opts],
        pp_task_status=[PpTaskTxnOut.model_validate(t) for t in txns],
    )
