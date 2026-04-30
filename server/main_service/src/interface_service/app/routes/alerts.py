"""Alerts router — equip_err_log + trans_err_log 통합.

레거시 'alerts' 테이블은 신규 schema 에서 두 err_log 로 분리됐다.
프런트와 PyQt 의 호환성을 위해 동일 엔드포인트 유지하되 두 소스 합쳐 반환.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import EquipErrLog, TransErrLog

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    """equip + trans err_log 합쳐서 최신순 반환."""
    out: list[dict] = []
    for e in db.query(EquipErrLog).order_by(desc(EquipErrLog.occured_at)).limit(limit).all():
        out.append(
            {
                "source": "equip",
                "err_id": e.err_id,
                "res_id": e.res_id,
                "task_txn_id": e.task_txn_id,
                "failed_stat": e.failed_stat,
                "err_msg": e.err_msg,
                "occured_at": e.occured_at,
            }
        )
    for t in db.query(TransErrLog).order_by(desc(TransErrLog.occured_at)).limit(limit).all():
        out.append(
            {
                "source": "trans",
                "err_id": t.err_id,
                "res_id": t.res_id,
                "task_txn_id": t.task_txn_id,
                "failed_stat": t.failed_stat,
                "err_msg": t.err_msg,
                "battery_pct": t.battery_pct,
                "occured_at": t.occured_at,
            }
        )

    def _ts(d: dict) -> datetime:
        v = d.get("occured_at")
        return v if isinstance(v, datetime) else datetime.min

    out.sort(key=_ts, reverse=True)
    return out[:limit]
