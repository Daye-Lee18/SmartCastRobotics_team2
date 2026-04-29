"""QSS 섹션 함수 패키지 — 책임별 sub-module 로 분리된 섹션을 모아 단일 _SECTIONS tuple 로 노출.

`build_qss(tokens)` 는 `app.styles.builder` 가 이 _SECTIONS 를 순회하며 합성한다.
새 섹션 추가는: 적절한 sub-module 에 함수 추가 → 본 __init__ 의 _SECTIONS 에 등록.
"""

from __future__ import annotations

from app.styles.qss.badges_alerts import _alerts_list, _badges_alerts, _toast
from app.styles.qss.base import _global, _main, _scrollbar
from app.styles.qss.canvas_map import _canvas, _factory_map
from app.styles.qss.content import _buttons, _cards, _inputs, _tables
from app.styles.qss.domain import _amr_card, _battery_bar, _conveyor_card, _defect_panels
from app.styles.qss.sidebar import _sidebar
from app.styles.qss.statusbar import _statusbar

# 섹션 적용 순서 — 일반 → 페이지 골격 → 콘텐츠 → 도메인 → 캔버스/맵.
# 원본 builder.py 의 순서를 보존하여 cascade 결과 동일.
_SECTIONS = (
    _global,
    _main,
    _sidebar,
    _cards,
    _inputs,
    _buttons,
    _tables,
    _badges_alerts,
    _canvas,
    _scrollbar,
    _statusbar,
    _alerts_list,
    _toast,
    _amr_card,
    _battery_bar,
    _conveyor_card,
    _defect_panels,
    _factory_map,
)

__all__ = ["_SECTIONS"]
