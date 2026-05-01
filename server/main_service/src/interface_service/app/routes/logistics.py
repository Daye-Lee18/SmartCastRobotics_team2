"""Logistics router — smartcast schema.

엔드포인트:
  GET  /api/logistics/trans-tasks       trans_task_txn 목록
  GET  /api/logistics/trans-stats       AMR 별 최신 상태 (배터리 포함)
  GET  /api/logistics/locations         3개 location stat (chg/strg/ship)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import (
    ChgLocationStat,
    ShipLocationStat,
    StrgLocationStat,
    Trans,
    TransCoord,
    TransStat,
    TransTaskTxn,
    Zone,
)
from app.schemas.schemas import TransStatOut, TransTaskTxnOut

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


def _trans_task_out(txn: TransTaskTxn) -> TransTaskTxnOut:
    return TransTaskTxnOut.model_validate(
        {
            "txn_id": txn.txn_id,
            "res_id": txn.res_id,
            "trans_task_txn_id": txn.txn_id,
            "trans_id": txn.res_id,
            "task_type": txn.task_type,
            "txn_stat": txn.txn_stat,
            "chg_loc_id": txn.chg_loc_id,
            "item_id": txn.item_stat_id,
            "ord_id": txn.ord_id,
            "req_at": txn.req_at,
            "start_at": txn.start_at,
            "end_at": txn.end_at,
        }
    )


def _trans_stat_out(stat: TransStat, *, zone_name: str | None) -> TransStatOut:
    return TransStatOut.model_validate(
        {
            "res_id": stat.res_id,
            "item_id": stat.item_stat_id,
            "cur_stat": stat.cur_stat,
            "battery_pct": stat.battery_pct,
            "cur_trans_coord_id": stat.cur_trans_coord_id,
            "cur_zone_type": zone_name,
            "updated_at": stat.updated_at,
        }
    )


@router.get("/trans-tasks", response_model=list[TransTaskTxnOut])
def list_trans_tasks(
    trans_id: str | None = None, db: Session = Depends(get_db)
) -> list[TransTaskTxnOut]:
    q = db.query(TransTaskTxn)
    if trans_id:
        q = q.filter(TransTaskTxn.res_id == trans_id)
    return [_trans_task_out(t) for t in q.order_by(desc(TransTaskTxn.req_at)).limit(100).all()]


@router.get("/trans-stats", response_model=list[TransStatOut])
def list_trans_stats(db: Session = Depends(get_db)) -> list[TransStatOut]:
    """모든 AMR 의 최신 상태."""
    out: list[TransStatOut] = []
    zone_by_coord_id = {
        c.trans_coord_id: z.zone_nm
        for c, z in db.query(TransCoord, Zone).join(Zone, Zone.zone_id == TransCoord.zone_id).all()
    }
    for t in db.query(Trans).all():
        s = db.get(TransStat, t.res_id)
        if s:
            out.append(_trans_stat_out(s, zone_name=zone_by_coord_id.get(s.cur_trans_coord_id)))
    return out


# Legacy alias — PyQt/Next.js 가 /api/logistics/tasks 로 호출
@router.get("/tasks", response_model=list[TransTaskTxnOut])
def list_tasks_alias(db: Session = Depends(get_db)) -> list[TransTaskTxnOut]:
    return list_trans_tasks(None, db)


# Legacy compat — strg_location_stat 만 반환 (warehouse 의미)
@router.get("/warehouse")
def list_warehouse(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "loc_id": r.loc_id,
            "row": r.loc_row,
            "col": r.loc_col,
            "status": r.status,
            "item_id": r.item_stat_id,
            "stored_at": r.stored_at.isoformat() if r.stored_at else None,
        }
        for r in db.query(StrgLocationStat)
        .order_by(StrgLocationStat.loc_row, StrgLocationStat.loc_col)
        .all()
    ]


# Legacy compat — outbound_orders 는 ord_stat 'SHIP' 또는 'COMP' 발주 목록
@router.get("/outbound-orders")
def list_outbound_orders(db: Session = Depends(get_db)) -> list[dict]:
    from smart_cast_db.models import Ord, OrdStat  # local import to avoid cycle

    out: list[dict] = []
    for o in db.query(Ord).all():
        latest = (
            db.query(OrdStat)
            .filter(OrdStat.ord_id == o.ord_id)
            .order_by(desc(OrdStat.updated_at))
            .first()
        )
        if latest and latest.ord_stat in {"SHIP", "COMP", "DONE"}:
            out.append(
                {
                    "ord_id": o.ord_id,
                    "user_id": o.user_id,
                    "stat": latest.ord_stat,
                    "updated_at": latest.updated_at.isoformat() if latest.updated_at else None,
                }
            )
    return out


@router.get("/locations")
def list_locations(db: Session = Depends(get_db)) -> dict:
    """3개 location stat 통합 응답 (chg / strg / ship)."""
    return {
        "chg": [
            {
                "loc_id": r.loc_id,
                "row": r.loc_row,
                "col": r.loc_col,
                "status": r.status,
                "res_id": r.res_id,
            }
            for r in db.query(ChgLocationStat)
            .order_by(ChgLocationStat.loc_row, ChgLocationStat.loc_col)
            .all()
        ],
        "strg": [
            {
                "loc_id": r.loc_id,
                "row": r.loc_row,
                "col": r.loc_col,
                "status": r.status,
                "item_id": r.item_stat_id,
            }
            for r in db.query(StrgLocationStat)
            .order_by(StrgLocationStat.loc_row, StrgLocationStat.loc_col)
            .all()
        ],
        "ship": [
            {
                "loc_id": r.loc_id,
                "row": r.loc_row,
                "col": r.loc_col,
                "status": r.status,
                "ord_id": r.ord_id,
                "item_id": r.item_stat_id,
            }
            for r in db.query(ShipLocationStat)
            .order_by(ShipLocationStat.loc_row, ShipLocationStat.loc_col)
            .all()
        ],
    }
