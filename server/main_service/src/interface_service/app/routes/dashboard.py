"""Dashboard router — smartcast schema 기반 통계 집계.

Legacy /api/dashboard/stats 호환 응답을 신규 schema 에서 derive 한다.
PyQt / Next.js 대시보드 페이지가 호출.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import (
    EquipErrLog,
    ItemStat,
    Ord,
    OrdStat,
    Res,
    TransErrLog,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict:
    """대시보드 카드용 집계 한 묶음."""
    # latest stat per ord 를 derive
    latest_stats: dict[int, str] = {}
    for s in db.query(OrdStat).order_by(desc(OrdStat.updated_at)).all():
        latest_stats.setdefault(s.ord_id, s.ord_stat or "RCVD")

    total_orders = db.query(func.count(Ord.ord_id)).scalar() or 0
    in_production = sum(1 for v in latest_stats.values() if v in {"APPR", "MFG"})
    completed = sum(1 for v in latest_stats.values() if v in {"COMP", "SHIP", "DONE"})
    pending = sum(1 for v in latest_stats.values() if v == "RCVD")

    total_items = db.query(func.count(ItemStat.item_stat_id)).scalar() or 0
    defective_items = (
        db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.is_(False)).scalar() or 0
    )
    good_items = (
        db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.is_(True)).scalar() or 0
    )

    inspected = (
        db.query(func.count(ItemStat.item_stat_id)).filter(ItemStat.result.isnot(None)).scalar() or 0
    )
    defect_rate = (defective_items / inspected * 100.0) if inspected else 0.0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    err_today = (
        db.query(func.count(EquipErrLog.err_id))
        .filter(EquipErrLog.occured_at >= today_start)
        .scalar()
        or 0
    )
    trans_err_today = (
        db.query(func.count(TransErrLog.err_id))
        .filter(TransErrLog.occured_at >= today_start)
        .scalar()
        or 0
    )

    active_resources = db.query(func.count(Res.res_id)).scalar() or 0

    from app.services.timescale import has_timescaledb

    return {
        "total_orders": total_orders,
        "orders_in_production": in_production,
        "orders_completed": completed,
        "orders_pending": pending,
        "total_items": total_items,
        "good_items": good_items,
        "defective_items": defective_items,
        "defect_rate_pct": round(defect_rate, 2),
        "alerts_today": err_today + trans_err_today,
        "active_resources": active_resources,
        "snapshot_at": datetime.utcnow().isoformat() + "Z",
        "timescaledb_enabled": has_timescaledb(),  # 시계열 차트가 hypertable 사용 가능한지
    }
