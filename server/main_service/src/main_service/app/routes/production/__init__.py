"""production routes package — sub-router aggregator.

이 패키지는 backend/app/routes/production.py (821 LOC, 2026-04-27 분할 전) 의
책임별 분할 산출이다. main.py 의 `from app.routes import production;
app.include_router(production.router)` 패턴을 유지하기 위해 본 __init__.py 가
모든 sub-router 를 단일 `router` 로 통합한다.

Sub-modules:
    _helpers.py     공통 헬퍼 + Pydantic models + auto-progression mapping
    patterns.py     POST/GET/GET /patterns (Pink GUI #3)
    lifecycle.py    POST /start + POST /equip-tasks/{txn}/advance
    items.py        items / equip-tasks / equip-stats / equipment / stages /
                    metrics / order-item-progress / items/{item}/pp
    timeseries.py   hourly / weekly / temperature / live / parameter-history
    schedule.py     schedule/jobs / schedule/calculate / schedule/start /
                    schedule/priority-log

Endpoint URL prefix 는 모두 `/api/production` (sub-router 가 동일 prefix 사용).
"""

from __future__ import annotations

from fastapi import APIRouter

from . import items, lifecycle, patterns, schedule, timeseries

# 통합 router — main.py 가 단일 `production.router` 로 include
router = APIRouter()
router.include_router(patterns.router)
router.include_router(lifecycle.router)
router.include_router(items.router)
router.include_router(timeseries.router)
router.include_router(schedule.router)

__all__ = ["router"]
