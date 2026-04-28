"""FastAPI 백엔드 REST 클라이언트 — thin re-export.

본 모듈은 backwards-compat 용 얇은 래퍼다. 실제 ApiClient 구현은
`monitoring/app/clients/` 패키지의 8 mixin 통합.

외부 import 패턴 동일 유지:
    from app.api_client import ApiClient
    from app.api_client import DATA_MODE   # 설정 모드 ('normal' / 'fallback' / 'mock_only')

2026-04-27: monitoring/app/api_client.py (830 LOC) 분할.

도메인 mixin (clients/ 패키지):
    _base.py        BaseClient + _get/_post/_patch
    orders.py       OrdersMixin (orders/patterns/recent/approved-running)
    production.py   ProductionMixin (start_one/items/equip/stages/schedule batch)
    quality.py      QualityMixin (inspection/sorter/vision/defect/standards)
    auth.py         AuthMixin (operator 로그인 + handoff ACK)
    logistics.py    LogisticsMixin (transport/warehouse/outbound/AMR)
    monitoring.py   MonitoringMixin (dashboard/alerts/timeseries/charts)
    debug.py        DebugMixin (RFID + TOF1/TOF2 가상 시뮬)
"""

from __future__ import annotations

from app.clients import ApiClient, BaseClient
from app.clients._base import (
    _ORD_STAT_TO_LEGACY_STATUS,
    DATA_MODE,
    _normalize_rack_id,
    _normalize_rack_status,
)

__all__ = [
    "ApiClient",
    "BaseClient",
    "DATA_MODE",
    "_ORD_STAT_TO_LEGACY_STATUS",
    "_normalize_rack_id",
    "_normalize_rack_status",
]
