"""Time-series production endpoints.

Endpoints:
    GET /api/production/hourly             시간대별 item 생산 (24h, TimescaleDB or fallback)
    GET /api/production/weekly             주간 item 생산
    GET /api/production/temperature        legacy 온도 이력 (센서 미연동, 빈 배열)
    GET /api/production/live               legacy 실시간 공정 변수 (빈 배열)
    GET /api/production/parameter-history  legacy 공정 변수 이력 (빈 배열)

temperature/live/parameter-history 는 HW 연동 후 Phase H 별도 작업.
hourly/weekly 는 backend/app/services/timescale.py 가 schema-aware 처리.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/production", tags=["production"])


@router.get("/hourly")
def production_hourly(hours: int = 24, db: Session = Depends(get_db)) -> list[dict]:
    """시간대별 생산 — TimescaleDB 있으면 hypertable, 없으면 date_trunc 폴백."""
    from app.services.timescale import hourly_item_production

    return hourly_item_production(db, hours=hours)


@router.get("/weekly")
def production_weekly(weeks: int = 8, db: Session = Depends(get_db)) -> list[dict]:
    """주간 생산 카운트."""
    from app.services.timescale import weekly_item_production

    return weekly_item_production(db, weeks=weeks)


@router.get("/temperature")
def production_temperature() -> list[dict]:
    """legacy 온도 이력 — 센서 미연동, 빈 배열 (Phase H 별도 작업)."""
    return []


@router.get("/live")
def production_live_parameters() -> list[dict]:
    """legacy 실시간 공정 변수 — 센서 미연동, 빈 배열."""
    return []


@router.get("/parameter-history")
def production_parameter_history() -> list[dict]:
    """legacy 공정 변수 이력 — 빈 배열."""
    return []
