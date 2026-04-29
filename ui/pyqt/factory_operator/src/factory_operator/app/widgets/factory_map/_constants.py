"""factory_map 위젯 — 색상/크기/좌표 상수.

Scene 크기, 색상 팔레트, AMR 상태→색상 매핑, 시뮬레이션 좌표 (_POS).
다른 모듈이 `from ._constants import ...` 로 import.

2026-04-27: backend/app/widgets/factory_map.py (1069 LOC) 분할 산출.
"""

from __future__ import annotations

from PyQt5.QtGui import QColor

# ---------------------------------------------------------------------------
# 씬 크기 (이미지 비율 ~1300x650)
# ---------------------------------------------------------------------------
SCENE_W = 1300
SCENE_H = 700

# ---------------------------------------------------------------------------
# 색상
# ---------------------------------------------------------------------------
BG_COLOR = "#e8e8e8"  # 전체 배경
ZONE_BG = QColor(160, 180, 210, 140)  # 구역 배경 (반투명 파란)
ZONE_BORDER = QColor(60, 70, 110)  # 구역 파선 테두리
LABEL_BG = "#ffd700"  # 노란 라벨
LABEL_TEXT = "#000000"
EQUIP_BG = "#ffffff"  # 장비 흰색 배경
CONVEYOR_COLOR = "#228b22"  # 컨베이어 초록
RED_BLOCK = "#ff3300"  # 빨간 사각형
MOLD_COLOR = "#b0d4f1"  # 하늘색 몰드
AMR_COLOR = "#e6c619"  # AMR 노란색
CHARGING_BG = QColor(200, 200, 200)
OUTBOUND_GRAD_TOP = "#d0d0d0"
OUTBOUND_GRAD_BOT = "#a0a0a0"
WORKER_COLOR = "#333333"

# AMR 상태 색상
STATUS_COLORS: dict[str, dict[str, str]] = {
    "active": {"dot": "#4ade80", "border": "#22c55e"},
    "idle": {"dot": "#9ca3af", "border": "#6b7280"},
    "warning": {"dot": "#fbbf24", "border": "#f59e0b"},
    "error": {"dot": "#f87171", "border": "#ef4444"},
    "charging": {"dot": "#60a5fa", "border": "#60a5fa"},
}


# ---------------------------------------------------------------------------
# 시뮬레이션 좌표
# ---------------------------------------------------------------------------
# 주요 좌표 상수 (zone 내부 + 통로 웨이포인트)
_POS = {
    "mold": (927, 480),
    "cast_wait": (970, 320),
    "amr1_home": (562, 527),
    "amr2_home": (672, 527),
    "amr3_home": (782, 527),
    "cast_pickup": (870, 320),
    "unload_worker": (90, 170),
    "pp_worker": (160, 155),
    "conv_left": (230, 117),
    "conv_right": (490, 117),
    "conv_wait": (560, 117),
    "conv_pickup": (600, 245),
    "putaway": (310, 430),
    "rack": (95, 530),
    "rack_pickup": (200, 530),
    "outbound": (1165, 125),
    # 통로 웨이포인트 (zone 밖)
    "corridor_top": (450, 250),
    "corridor_right": (850, 250),
    "corridor_left": (90, 250),
    "corridor_mid": (600, 250),
    "corridor_bottom_left": (450, 430),
    "corridor_outbound_r": (1050, 250),
    "corridor_outbound_up": (1165, 250),
    "corridor_storage_bot": (450, 530),
    "corridor_charge_exit_1": (562, 440),
    "corridor_charge_exit_2": (672, 440),
    "corridor_charge_exit_3": (782, 440),
}

# 시뮬레이션 파라미터
CASTING_COLOR = "#9333ea"  # 보라색
CASTING_RADIUS = 8
SIM_SPEED = 10  # px per tick (200ms 주기 보정 — 같은 시각 속도 유지)
SIM_TICK_MS = 200  # 200ms = 5Hz (이전 50ms = 20Hz 에서 4배 완화)


def _status_key(raw: str) -> str:
    """외부 status 라벨 → STATUS_COLORS key 정규화."""
    s = (raw or "").lower()
    mapping = {
        "running": "active",
        "active": "active",
        "completed": "active",
        "idle": "idle",
        "waiting": "idle",
        "warning": "warning",
        "maintenance": "warning",
        "error": "error",
        "alarm": "error",
        "charging": "charging",
    }
    return mapping.get(s, "idle")


def _move_toward(
    cx: float, cy: float, tx: float, ty: float, speed: float
) -> tuple[float, float, bool]:
    """(cx,cy)에서 (tx,ty)를 향해 speed만큼 이동. 도착하면 arrived=True."""
    dx, dy = tx - cx, ty - cy
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= speed:
        return tx, ty, True
    ratio = speed / dist
    return cx + dx * ratio, cy + dy * ratio, False
