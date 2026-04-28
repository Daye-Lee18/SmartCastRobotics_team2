"""Mock 데이터 — FastAPI 백엔드 장애 / 오프라인 시 fallback.

네트워크 연결이 끊겨 있거나 백엔드가 응답하지 않을 때 화면이 비지 않도록
대체 데이터를 제공한다. ApiClient 가 None 을 반환할 때 사용.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _ago(minutes: int = 0, hours: int = 0) -> str:
    dt = datetime.now() - timedelta(minutes=minutes, hours=hours)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


DASHBOARD_STATS: dict[str, Any] = {
    "production_goal_rate": 82.5,
    "today_production": 187,
    "completed_today": 165,
    "active_robots": 5,
    "pending_orders": 12,
    "today_alarms": 3,
    "defect_rate": 2.8,
    "equipment_utilization": 78.4,
    "oee": 72.6,
    "active_orders": 8,
}


ALERTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "level": "warning",
        "message": "용해로 #1 온도 임계값 초과 (1450°C)",
        "source": "FRN-001",
        "created_at": _ago(minutes=2),
    },
    {
        "id": 2,
        "level": "error",
        "message": "AMR #3 배터리 부족 (12%) - 충전 필요",
        "source": "AMR-003",
        "created_at": _ago(minutes=8),
    },
    {
        "id": 3,
        "level": "info",
        "message": "조형기 #1 정기 점검 일정 도래 (D-2)",
        "source": "MLD-001",
        "created_at": _ago(minutes=22),
    },
    {
        "id": 4,
        "level": "warning",
        "message": "검사 카메라 #1 초점 재조정 권장",
        "source": "CAM-001",
        "created_at": _ago(hours=1),
    },
    {
        "id": 5,
        "level": "critical",
        "message": "분류기 #1 벨트 마모 감지 - 교체 필요",
        "source": "SRT-001",
        "created_at": _ago(hours=2),
    },
    {
        "id": 6,
        "level": "info",
        "message": "주문 ORD-2026-045 생산 완료",
        "source": "SYSTEM",
        "created_at": _ago(hours=3),
    },
]


PROCESS_STAGES: list[dict[str, Any]] = [
    {
        "id": 1,
        "label": "용해",
        "status": "running",
        "progress": 100,
        "start_time": _ago(hours=2),
        "equipment_id": "FRN-001",
    },
    {
        "id": 2,
        "label": "주형 제작",
        "status": "completed",
        "progress": 100,
        "start_time": _ago(hours=3),
        "equipment_id": "MLD-001",
    },
    {
        "id": 3,
        "label": "주탕",
        "status": "waiting",
        "progress": 0,
        "start_time": "",
        "equipment_id": "ARM-001",
    },
    {
        "id": 4,
        "label": "냉각",
        "status": "running",
        "progress": 81,
        "start_time": _ago(hours=4),
        "equipment_id": "CLZ-001",
    },
    {
        "id": 5,
        "label": "탈형",
        "status": "idle",
        "progress": 0,
        "start_time": "",
        "equipment_id": "ARM-002",
    },
    {
        "id": 6,
        "label": "후처리",
        "status": "running",
        "progress": 67,
        "start_time": _ago(hours=1),
        "equipment_id": "ARM-003",
    },
    {
        "id": 7,
        "label": "검사",
        "status": "running",
        "progress": 95,
        "start_time": _ago(minutes=30),
        "equipment_id": "CAM-001",
    },
    {
        "id": 8,
        "label": "분류",
        "status": "idle",
        "progress": 0,
        "start_time": "",
        "equipment_id": "SRT-001",
    },
]


EQUIPMENT: list[dict[str, Any]] = [
    {
        "id": "FRN-001",
        "name": "용해로 #1",
        "type": "furnace",
        "status": "running",
        "utilization": 92,
        "last_checked": "2026-03-20",
    },
    {
        "id": "FRN-002",
        "name": "용해로 #2",
        "type": "furnace",
        "status": "idle",
        "utilization": 0,
        "last_checked": "2026-03-18",
    },
    {
        "id": "MLD-001",
        "name": "조형기 #1",
        "type": "mold_press",
        "status": "running",
        "utilization": 85,
        "last_checked": "2026-03-22",
    },
    {
        "id": "ARM-001",
        "name": "로봇암 #1 (주탕)",
        "type": "robot_arm",
        "status": "idle",
        "utilization": 45,
        "last_checked": "2026-03-25",
    },
    {
        "id": "ARM-002",
        "name": "로봇암 #2 (탈형)",
        "type": "robot_arm",
        "status": "idle",
        "utilization": 32,
        "last_checked": "2026-03-24",
    },
    {
        "id": "ARM-003",
        "name": "로봇암 #3 (후처리)",
        "type": "robot_arm",
        "status": "running",
        "utilization": 78,
        "last_checked": "2026-03-26",
    },
    {
        "id": "CAM-001",
        "name": "검사 카메라 #1",
        "type": "camera",
        "status": "running",
        "utilization": 95,
        "last_checked": "2026-03-23",
    },
    {
        "id": "CVR-001",
        "name": "컨베이어 #1",
        "type": "conveyor",
        "status": "running",
        "utilization": 88,
        "last_checked": "2026-03-21",
    },
    {
        "id": "SRT-001",
        "name": "분류기 #1",
        "type": "sorter",
        "status": "running",
        "utilization": 72,
        "last_checked": "2026-03-19",
    },
    {
        "id": "AMR-001",
        "name": "AMR #1",
        "type": "amr",
        "status": "running",
        "utilization": 65,
        "last_checked": "2026-03-28",
    },
    {
        "id": "AMR-002",
        "name": "AMR #2",
        "type": "amr",
        "status": "idle",
        "utilization": 20,
        "last_checked": "2026-03-27",
    },
    {
        "id": "AMR-003",
        "name": "AMR #3",
        "type": "amr",
        "status": "charging",
        "utilization": 0,
        "last_checked": "2026-03-29",
    },
]


QUALITY_STATS: dict[str, Any] = {
    "total": 342,
    "ok": 332,
    "ng": 10,
    "defect_rate": 2.9,
}


INSPECTIONS: list[dict[str, Any]] = [
    {
        "id": i,
        "inspected_at": _ago(minutes=i * 5),
        "product": f"맨홀뚜껑 M{500 + i}",
        "result": "OK" if i % 8 != 0 else "NG",
        "defect_type": "" if i % 8 != 0 else ("균열" if i % 16 == 0 else "기공"),
        "inspector": "AI (CAM-001)",
        "note": "자동 검사" if i % 8 != 0 else "재검사 필요",
    }
    for i in range(1, 21)
]


TRANSPORT_TASKS: list[dict[str, Any]] = [
    {
        "id": "T-0042",
        "type": "운반",
        "priority": "urgent",
        "from": "주조 구역 C",
        "to": "냉각 구역 D",
        "amr": "AMR-001",
        "status": "running",
        "cargo": "주물 12개",
    },
    {
        "id": "T-0043",
        "type": "운반",
        "priority": "high",
        "from": "검사 F",
        "to": "분류 F",
        "amr": "AMR-002",
        "status": "pending",
        "cargo": "검사품 8개",
    },
    {
        "id": "T-0040",
        "type": "충전",
        "priority": "low",
        "from": "대기 장소",
        "to": "충전소",
        "amr": "AMR-003",
        "status": "running",
        "cargo": "-",
    },
    {
        "id": "T-0041",
        "type": "운반",
        "priority": "normal",
        "from": "후처리 E",
        "to": "검사 구역 F",
        "amr": "AMR-001",
        "status": "completed",
        "cargo": "주물 10개",
    },
    {
        "id": "T-0039",
        "type": "운반",
        "priority": "urgent",
        "from": "분류 F",
        "to": "출고장 G",
        "amr": "AMR-002",
        "status": "pending",
        "cargo": "출고분 30개",
    },
    {
        "id": "T-0038",
        "type": "운반",
        "priority": "normal",
        "from": "주형 B",
        "to": "주조 C",
        "amr": "AMR-001",
        "status": "pending",
        "cargo": "주형 6개",
    },
    {
        "id": "T-0037",
        "type": "운반",
        "priority": "low",
        "from": "용해 A",
        "to": "주형 B",
        "amr": "AMR-001",
        "status": "completed",
        "cargo": "원재료 50kg",
    },
]


AMR_STATUS: list[dict[str, Any]] = [
    {
        "id": "AMR-001",
        "status": "running",
        "battery": 78,
        "location": "이송 구역",
        "current_task": "T-0042",
    },
    {
        "id": "AMR-002",
        "status": "idle",
        "battery": 95,
        "location": "대기 장소",
        "current_task": "-",
    },
    {
        "id": "AMR-003",
        "status": "charging",
        "battery": 12,
        "location": "충전소",
        "current_task": "T-0040",
    },
]


# ===== 차트 데이터 (v0.2 신규) =====

WEEKLY_PRODUCTION: list[dict[str, Any]] = [
    {"day": "월", "production": 168, "defect_rate": 2.4},
    {"day": "화", "production": 182, "defect_rate": 2.1},
    {"day": "수", "production": 165, "defect_rate": 3.3},
    {"day": "목", "production": 194, "defect_rate": 1.8},
    {"day": "금", "production": 201, "defect_rate": 2.0},
    {"day": "토", "production": 156, "defect_rate": 2.9},
    {"day": "일", "production": 143, "defect_rate": 3.6},
]


TEMPERATURE_HISTORY: list[dict[str, Any]] = [
    {"minute": i, "temperature": temp, "target": 1450}
    for i, temp in enumerate(
        [
            25,
            180,
            340,
            490,
            640,
            780,
            910,
            1020,
            1120,
            1200,
            1270,
            1330,
            1380,
            1410,
            1430,
            1442,
            1448,
            1451,
            1449,
            1450,
            1451,
            1450,
            1452,
            1449,
            1450,
            1451,
            1450,
            1450,
            1449,
            1451,
        ]
    )
]


HOURLY_PRODUCTION: list[dict[str, Any]] = [
    {"hour": f"{h:02d}:00", "good": g, "bad": b}
    for h, (g, b) in zip(
        range(8, 20),
        [
            (32, 1),
            (41, 2),
            (38, 1),
            (45, 3),
            (52, 2),
            (48, 1),
            (39, 2),
            (44, 1),
            (50, 3),
            (46, 2),
            (42, 1),
            (35, 1),
        ],
        strict=False,
    )
]


DEFECT_RATE_TREND: list[dict[str, Any]] = [
    {"label": "월", "rate": 2.4},
    {"label": "화", "rate": 2.1},
    {"label": "수", "rate": 3.3},
    {"label": "목", "rate": 1.8},
    {"label": "금", "rate": 2.0},
    {"label": "토", "rate": 2.9},
    {"label": "일", "rate": 3.6},
]


DEFECT_TYPE_DIST: list[dict[str, Any]] = [
    {"type": "기공", "count": 12},
    {"type": "균열", "count": 8},
    {"type": "미성형", "count": 5},
    {"type": "치수 이탈", "count": 3},
    {"type": "표면 결함", "count": 2},
]


VISION_FEED: dict[str, Any] = {
    "result": "pass",
    "product_id": "M500-0042",
    "confidence": 98.7,
    "inspected_at": "2026-04-07 17:58:12",
    "defect_type": "",
}


SORTER_STATE: dict[str, Any] = {
    "angle": 90.0,
    "direction": "good",
    "success": True,
    "count_good": 152,
    "count_bad": 8,
}


INSPECTION_STANDARDS: list[dict[str, Any]] = [
    {
        "product": "맨홀뚜껑 M500",
        "target": "Φ500 × H40 mm",
        "tolerance": "±0.8 mm",
        "threshold": "95%",
    },
    {
        "product": "그레이팅 GR-A",
        "target": "500 × 300 × 25 mm",
        "tolerance": "±1.0 mm",
        "threshold": "92%",
    },
    {
        "product": "맨홀뚜껑 M800",
        "target": "Φ800 × H55 mm",
        "tolerance": "±1.2 mm",
        "threshold": "94%",
    },
]


PRODUCTION_VS_DEFECTS: list[dict[str, Any]] = [
    {"label": f"{h:02d}시", "production": g + b, "defect_rate": round(b * 100 / max(g + b, 1), 1)}
    for h, (g, b) in zip(
        range(8, 20),
        [
            (32, 1),
            (41, 2),
            (38, 1),
            (45, 3),
            (52, 2),
            (48, 1),
            (39, 2),
            (44, 1),
            (50, 3),
            (46, 2),
            (42, 1),
            (35, 1),
        ],
        strict=False,
    )
]


WAREHOUSE_RACKS: list[dict[str, Any]] = [
    # 3행 × 6열, ID 1~18 (하단 좌측=1 → 우측 최상단=18).
    # 행 0 (하단): 1~6
    {"id": "1", "status": "full", "content": "맨홀뚜껑 M500", "qty": 24},
    {"id": "2", "status": "full", "content": "맨홀뚜껑 M600", "qty": 18},
    {"id": "3", "status": "partial", "content": "맨홀뚜껑 M600", "qty": 9},
    {"id": "4", "status": "full", "content": "그레이팅 GR-A", "qty": 32},
    {"id": "5", "status": "empty", "content": "", "qty": 0},
    {"id": "6", "status": "reserved", "content": "그레이팅 GR-B", "qty": 16},
    # 행 1 (중간): 7~12
    {"id": "7", "status": "partial", "content": "커버 CV-1", "qty": 4},
    {"id": "8", "status": "empty", "content": "", "qty": 0},
    {"id": "9", "status": "full", "content": "맨홀뚜껑 M400", "qty": 28},
    {"id": "10", "status": "locked", "content": "검사 대기", "qty": 6},
    {"id": "11", "status": "full", "content": "그레이팅 GR-C", "qty": 22},
    {"id": "12", "status": "partial", "content": "커버 CV-2", "qty": 7},
    # 행 2 (상단): 13~18
    {"id": "13", "status": "full", "content": "맨홀뚜껑 M800", "qty": 20},
    {"id": "14", "status": "reserved", "content": "출고 대기", "qty": 12},
    {"id": "15", "status": "full", "content": "그레이팅 GR-D", "qty": 26},
    {"id": "16", "status": "full", "content": "맨홀뚜껑 M500", "qty": 30},
    {"id": "17", "status": "partial", "content": "커버 CV-3", "qty": 5},
    {"id": "18", "status": "locked", "content": "품질 홀드", "qty": 8},
]


OUTBOUND_ORDERS: list[dict[str, Any]] = [
    {
        "id": "OUT-20260407-01",
        "product": "맨홀뚜껑 M500",
        "qty": 24,
        "customer": "대성산업",
        "policy": "FIFO",
        "status": "pending",
    },
    {
        "id": "OUT-20260407-02",
        "product": "그레이팅 GR-A",
        "qty": 30,
        "customer": "한진중공업",
        "policy": "FIFO",
        "status": "running",
    },
    {
        "id": "OUT-20260407-03",
        "product": "맨홀뚜껑 M800",
        "qty": 15,
        "customer": "포스코",
        "policy": "LIFO",
        "status": "pending",
    },
    {
        "id": "OUT-20260406-11",
        "product": "맨홀뚜껑 M600",
        "qty": 18,
        "customer": "현대건설",
        "policy": "FIFO",
        "status": "completed",
    },
    {
        "id": "OUT-20260406-09",
        "product": "커버 CV-2",
        "qty": 5,
        "customer": "삼성중공업",
        "policy": "FIFO",
        "status": "completed",
    },
]


PROCESS_PARAM_HISTORY: list[dict[str, Any]] = [
    {
        "time": "09:00:00",
        "stage": "용해",
        "temperature": 1452.3,
        "pressure": "-",
        "angle": "-",
        "power": "92%",
        "cooling": "-",
        "progress": "100%",
    },
    {
        "time": "09:00:00",
        "stage": "주형",
        "temperature": "-",
        "pressure": "85 bar",
        "angle": "-",
        "power": "-",
        "cooling": "-",
        "progress": "100%",
    },
    {
        "time": "09:15:00",
        "stage": "주탕",
        "temperature": 1400.0,
        "pressure": "-",
        "angle": "45°",
        "power": "-",
        "cooling": "-",
        "progress": "0%",
    },
    {
        "time": "09:30:00",
        "stage": "냉각",
        "temperature": 178.1,
        "pressure": "-",
        "angle": "-",
        "power": "-",
        "cooling": "60%",
        "progress": "81%",
    },
    {
        "time": "09:45:00",
        "stage": "탈형",
        "temperature": "-",
        "pressure": "-",
        "angle": "-",
        "power": "-",
        "cooling": "-",
        "progress": "0%",
    },
    {
        "time": "10:00:00",
        "stage": "후처리",
        "temperature": "-",
        "pressure": "-",
        "angle": "-",
        "power": "-",
        "cooling": "-",
        "progress": "67%",
    },
    {
        "time": "10:15:00",
        "stage": "검사",
        "temperature": "-",
        "pressure": "-",
        "angle": "-",
        "power": "-",
        "cooling": "-",
        "progress": "95%",
    },
    {
        "time": "10:30:00",
        "stage": "분류",
        "temperature": "-",
        "pressure": "-",
        "angle": "-",
        "power": "-",
        "cooling": "-",
        "progress": "0%",
    },
]


LIVE_PARAMETERS: dict[str, Any] = {
    "furnace_temperature": 1447.8,
    "furnace_target": 1450.0,
    "furnace_heating_power": 88.5,
    "mold_pressure": 82.3,
    "pour_angle": 42.5,
    "cooling_progress": 78.0,
    "cooling_current_temp": 178.1,
    "cooling_target_temp": 25.0,
    "cooling_remaining_min": 12,
    "mode_auto": True,
    "e_stop_active": False,
}


ORDER_ITEM_PROGRESS: list[dict[str, Any]] = [
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-1", "stage": "적재"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-2", "stage": "검사"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-3", "stage": "후처리"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-4", "stage": "후처리"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-5", "stage": "탈형"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-6", "stage": "주탕"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-7", "stage": "대기"},
    {"order_id": "ORD-2026-045", "product": "맨홀뚜껑 A형", "item": "A-8", "stage": "대기"},
    {"order_id": "ORD-2026-043", "product": "원형 그레이팅", "item": "B-1", "stage": "검사"},
    {"order_id": "ORD-2026-043", "product": "원형 그레이팅", "item": "B-2", "stage": "탈형"},
    {"order_id": "ORD-2026-043", "product": "원형 그레이팅", "item": "B-3", "stage": "주탕"},
    {"order_id": "ORD-2026-043", "product": "원형 그레이팅", "item": "B-4", "stage": "대기"},
]


RECENT_ORDERS: list[dict[str, Any]] = [
    {
        "id": "ORD-2026-045",
        "customer": "대성산업",
        "amount": 24_500_000,
        "due_date": "2026-04-15",
        "status": "production",
    },
    {
        "id": "ORD-2026-044",
        "customer": "한진중공업",
        "amount": 18_200_000,
        "due_date": "2026-04-12",
        "status": "approved",
    },
    {
        "id": "ORD-2026-043",
        "customer": "포스코",
        "amount": 42_800_000,
        "due_date": "2026-04-20",
        "status": "production",
    },
    {
        "id": "ORD-2026-042",
        "customer": "현대건설",
        "amount": 9_600_000,
        "due_date": "2026-04-10",
        "status": "completed",
    },
    {
        "id": "ORD-2026-041",
        "customer": "삼성중공업",
        "amount": 31_500_000,
        "due_date": "2026-04-18",
        "status": "reviewing",
    },
]
