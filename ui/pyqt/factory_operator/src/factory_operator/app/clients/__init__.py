"""ApiClient 패키지 — 도메인별 mixin 통합.

외부 import: `from app.api_client import ApiClient` 그대로 동작.
api_client.py 가 본 패키지의 ApiClient 를 re-export.

2026-04-27: monitoring/app/api_client.py (830 LOC) 분할 산출.

도메인 mixin (8개):
    _base.py        BaseClient + _get/_post/_patch + dead_paths/transient_failures
    orders.py       OrdersMixin (orders, patterns, recent_orders, approved/running)
    production.py   ProductionMixin (start_one, items, equip_tasks, advance,
                                     equipment, stages, schedule, batch start)
    quality.py      QualityMixin (inspection, sorter, vision, defect, standards)
    auth.py         AuthMixin (auth_lookup, operator_id/label, handoff_ack)
    logistics.py    LogisticsMixin (transport, warehouse, outbound, amr_status)
    monitoring.py   MonitoringMixin (dashboard, alerts, timeseries, charts)
    debug.py        DebugMixin (RFID + TOF1/TOF2 가상 시뮬)
"""

from __future__ import annotations

from ._base import BaseClient
from .auth import AuthMixin
from .debug import DebugMixin
from .logistics import LogisticsMixin
from .monitoring import MonitoringMixin
from .orders import OrdersMixin
from .production import ProductionMixin
from .quality import QualityMixin


class ApiClient(
    OrdersMixin,
    ProductionMixin,
    QualityMixin,
    AuthMixin,
    LogisticsMixin,
    MonitoringMixin,
    DebugMixin,
    BaseClient,
):
    """FastAPI REST 엔드포인트 호출 래퍼 (mock fallback 지원).

    8 mixin 통합. mixin 메서드 시그니처는 BaseClient 의 self._get/_post/_patch
    + self._fallback/_mock_only 를 사용. MRO 순서는 도메인별로 의미 충돌 없으므로
    어떤 순서든 동작 (BaseClient 가 마지막).
    """

    pass


__all__ = ["ApiClient", "BaseClient"]
