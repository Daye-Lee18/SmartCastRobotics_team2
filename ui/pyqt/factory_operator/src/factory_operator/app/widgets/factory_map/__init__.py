"""factory_map 위젯 패키지 — 2D 공장 맵 (이미지 기반 5구역 + AMR 시뮬).

이 패키지는 monitoring/app/widgets/factory_map.py (1069 LOC, 2026-04-27 분할 전)
의 책임별 분할 산출이다. 외부 import 패턴 동일 유지:

    from app.widgets.factory_map import FactoryMapView, MiniFactoryMapView,
                                          FactoryMapScene, STATUS_COLORS

Sub-modules:
    _constants.py    SCENE_W/H, 색상, _POS, STATUS_COLORS, SIM_*
    _drawing.py      _add_zone, _add_label, _add_box, _add_cobot, _add_worker
    sim.py           _CastingItem, _SimAMR, _SimController (18-step FSM)
    scene.py         FactoryMapScene (5구역 그리기 + AMR 마커 보간)
    views.py         FactoryMapView, MiniFactoryMapView

성능 (2026-04-27 패치):
    - ANIMATION_INTERVAL_MS 100ms (이전 30ms)
    - SIM_TICK_MS 200ms (이전 50ms) + SIM_SPEED 10px 보정
    - MiniFactoryMapView 는 enable_sim=False (sim 두 개 동시 가동 차단)
"""

from __future__ import annotations

from ._constants import STATUS_COLORS
from .scene import FactoryMapScene
from .views import FactoryMapView, MiniFactoryMapView

__all__ = [
    "FactoryMapView",
    "MiniFactoryMapView",
    "FactoryMapScene",
    "STATUS_COLORS",
]
