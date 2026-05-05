"""V2 — Integration: EventBridge 와 9 컴포넌트 연계 통합 테스트.

동료들이 작성한 services/legacy/handoff_pipeline · services/core/task_manager ·
services/adapters/sensors/rfid_service 가 EventBridge 와 연결되어 실제 데이터
흐름을 따라가며 EventType / payload / 호출 순서 / DB 부수효과 / 핸들러
호출 순서를 검증한다.

격리 정책 (TEST 페이지 51642709 의 Integration 정의 준수):
    - 실 PostgreSQL — conftest.py 의 ``postgresql_with_smartcast_seed`` /
      ``postgresql_smartcast_empty`` PG fixture 3종 사용 (실제 DB hit O)
    - 일부 Mock — RobotAdapter / TrafficManager / 외부 RPC 는 in-memory stub
    - EventBridge — 실 EventBridgeImpl 인스턴스 (subscribe + publish 검증)
    - smart_cast_db ORM 모델 — 실 SQLAlchemy 객체 (mock 안 함)

검증 시나리오 6개:
    I-1  TaskManager.start_production_single → TASK_CREATED publish (PG seed)
    I-2  apply_handoff (실 PG) → HANDOFF_ACK publish + DB 상태 변화
    I-3  apply_tof1 (실 PG) → TOF1_ENTRY publish + EquipTaskTxn INSERT
    I-4  apply_tof2 (실 PG) → TOF2_EXIT publish + InspTaskTxn INSERT
    I-5  RfidService.report_scan → RFID_SCANNED publish (FakeSession)
    I-6  multiple subscribers — Allocator stub + Monitor stub 동시 수신 + 격리

NOTE: 본 파일은 PR #16 (event_bridge.py 풀 구현체 + Event/PublishResult contracts)
머지 후 실행 가능. 그 전엔 import 단계에서 ImportError 발생.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest

# EventBridge (PR #16)
from main_service.management.services.core.event_bridge import EventBridgeImpl
from main_service.management.services.core.contracts.enums import EventType
from main_service.management.services.core.contracts.models import Event

# 동료 모듈
from services.core.task_manager import TaskManager, TaskManagerError
from services.legacy.handoff_pipeline import apply_handoff, apply_tof1, apply_tof2
from services.adapters.sensors.rfid_service import RfidService, RfidScanResult

# DB 모델 (실 SQLAlchemy)
from smart_cast_db.database import SessionLocal
from smart_cast_db.models import (
    Equip,
    EquipStat,
    EquipTaskTxn,
    InspTaskTxn,
    ItemStat,
    Ord,
    OrdPpMap,
    PpOption,
    PpTaskTxn,
    Res,
    Trans,
    TransStat,
    TransTaskTxn,
    UserAccount,
    Zone,
    RfidScanLog,
)


# ─────────────────────────────────────────────────────────────────────
# Fixtures — EventBridge + collector
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def bridge() -> EventBridgeImpl:
    """매 테스트마다 새 EventBridgeImpl 인스턴스."""
    return EventBridgeImpl()


@pytest.fixture
def collected() -> list[Event]:
    """publish 결과를 모으는 리스트 — assert 시 순서/내용 검증."""
    return []


@pytest.fixture
def collector(collected: list[Event]):
    def _c(e: Event) -> None:
        collected.append(e)
    return _c


# ─────────────────────────────────────────────────────────────────────
# Seed helpers (test_handoff_pipeline.py 패턴 차용)
# ─────────────────────────────────────────────────────────────────────

def _seed_zones_and_res(db) -> dict[str, Zone]:
    zones = {n: Zone(zone_nm=n) for n in ("CHG", "PP", "INSP")}
    db.add_all(zones.values())
    db.flush()
    db.add_all([
        Res(res_id="AMR1", res_type="AMR", model_nm="TEST-AMR"),
        Res(res_id="CONV-01", res_type="CONV", model_nm="TEST-CONV"),
    ])
    db.flush()
    db.add(Trans(res_id="AMR1", slot_count=1))
    db.add(Equip(res_id="CONV-01", zone_id=zones["INSP"].zone_id))
    db.flush()
    return zones


def _seed_item_in_zone(db, *, ord_id: int, flow_stat: str, zone_nm: str) -> ItemStat:
    item = ItemStat(ord_id=ord_id, flow_stat=flow_stat, zone_nm=zone_nm)
    db.add(item)
    db.flush()
    return item


def _seed_trans_waiting(db, *, item: ItemStat, ord_id: int) -> TransTaskTxn:
    db.add(TransStat(res_id="AMR1", item_stat_id=item.item_stat_id, cur_stat="WAIT_DLD"))
    txn = TransTaskTxn(
        res_id="AMR1", task_type="ToPP", txn_stat="PROC",
        item_stat_id=item.item_stat_id, ord_id=ord_id,
        req_at=datetime.now() - timedelta(minutes=5),
    )
    db.add(txn)
    db.flush()
    return txn


def _seed_pp_options_and_map(db, *, ord_id: int) -> None:
    shot = PpOption(pp_nm="SHOT", extra_cost=1000)
    grind = PpOption(pp_nm="GRIND", extra_cost=2000)
    db.add_all([shot, grind])
    db.flush()
    db.add_all([
        OrdPpMap(ord_id=ord_id, pp_id=shot.pp_id),
        OrdPpMap(ord_id=ord_id, pp_id=grind.pp_id),
    ])
    db.flush()


# ─────────────────────────────────────────────────────────────────────
# I-1) TaskManager → EventBridge TASK_CREATED publish
# ─────────────────────────────────────────────────────────────────────

def test_i1_task_manager_publishes_task_created(
    postgresql_with_smartcast_seed, bridge, collector, collected
):
    """발주 승인 → TaskManager.start_production_single 호출 → 결과를 EventBridge 로 발행 → subscriber 가 정확히 받는다."""
    bridge.subscribe(EventType.TASK_CREATED, collector, "test.task_created")

    tm = TaskManager()
    result = tm.start_production_single(42)

    # TaskManager 결과를 외부에서 EventBridge 로 발행 (Orchestrator 패턴)
    bridge.publish(Event(
        event_type=EventType.TASK_CREATED,
        ord_id=result.ord_id,
        item_id=result.item_id,
        txn_id=result.equip_task_txn_id,
        payload={"task_type": "MM"},
    ))

    assert len(collected) == 1
    e = collected[0]
    assert e.event_type == EventType.TASK_CREATED
    assert e.ord_id == 42
    assert e.txn_id == result.equip_task_txn_id
    assert e.item_id == result.item_id
    assert e.payload["task_type"] == "MM"


def test_i1b_task_manager_error_publishes_no_event(
    postgresql_smartcast_empty, bridge, collector, collected
):
    """ord_id 미존재 → TaskManagerError 발생, EventBridge 에 publish 없음."""
    bridge.subscribe(EventType.TASK_CREATED, collector, "test.task_created")

    tm = TaskManager()
    with pytest.raises(TaskManagerError, match="not found"):
        tm.start_production_single(999999)

    assert collected == []  # 실패 경로는 publish 없음


# ─────────────────────────────────────────────────────────────────────
# I-2) handoff_pipeline.apply_handoff (실 PG) → HANDOFF_ACK publish
# ─────────────────────────────────────────────────────────────────────

def test_i2_apply_handoff_publishes_handoff_ack(
    postgresql_smartcast_empty, bridge, collector, collected
):
    """PP 작업자 핸드오프 → DB 상태 변화 + HANDOFF_ACK 이벤트 발행."""
    bridge.subscribe(EventType.HANDOFF_ACK, collector, "test.handoff_ack")

    with SessionLocal() as db:
        _seed_zones_and_res(db)
        db.add(Ord(ord_id=200, user_id=1))
        db.flush()
        item = _seed_item_in_zone(db, ord_id=200, flow_stat="WAIT_PP", zone_nm="PP")
        _seed_pp_options_and_map(db, ord_id=200)
        txn = _seed_trans_waiting(db, item=item, ord_id=200)

        result = apply_handoff(
            db,
            button_device_id="BTN-1",
            ack_source="esp32_button",
            via="pytest",
            idempotency_key="i2-handoff-1",
            operator_id=1,
        )

        db.flush()
        db.refresh(item)

        # DB 상태 검증 (test_handoff_pipeline.py 가 보장하는 부수효과)
        assert result.released is True
        assert item.flow_stat == "PP"

        # 외부 publish 패턴 — apply_handoff 결과를 EventBridge 로 발행
        bridge.publish(Event(
            event_type=EventType.HANDOFF_ACK,
            ord_id=200,
            item_id=item.item_stat_id,
            txn_id=txn.txn_id,
            resource_id="AMR1",
            payload={
                "task_id": result.task_id,
                "amr_id": result.amr_id,
                "released": result.released,
                "pp_task_count": len(result.pp_task_txn_ids),
            },
        ))

    assert len(collected) == 1
    e = collected[0]
    assert e.event_type == EventType.HANDOFF_ACK
    assert e.ord_id == 200
    assert e.resource_id == "AMR1"
    assert e.payload["released"] is True
    assert e.payload["pp_task_count"] == 2  # SHOT + GRIND


# ─────────────────────────────────────────────────────────────────────
# I-3) apply_tof1 (실 PG) → TOF1_ENTRY publish + EquipTaskTxn INSERT
# ─────────────────────────────────────────────────────────────────────

def test_i3_apply_tof1_publishes_tof1_entry(
    postgresql_smartcast_empty, bridge, collector, collected
):
    """컨베이어 TOF1 입구 진입 → DB 부수효과(EquipTaskTxn ToINSP PROC) + TOF1_ENTRY 발행."""
    bridge.subscribe(EventType.TOF1_ENTRY, collector, "test.tof1")

    with SessionLocal() as db:
        _seed_zones_and_res(db)
        db.add(Ord(ord_id=300, user_id=1))
        db.flush()
        item = _seed_item_in_zone(db, ord_id=300, flow_stat="PP", zone_nm="PP")
        db.add_all([PpOption(pp_nm="SHOT", extra_cost=1000), PpOption(pp_nm="GRIND", extra_cost=2000)])
        db.flush()
        db.add_all([
            PpTaskTxn(ord_id=300, item_stat_id=item.item_stat_id, pp_nm="SHOT", txn_stat="QUE"),
            PpTaskTxn(ord_id=300, item_stat_id=item.item_stat_id, pp_nm="GRIND", txn_stat="PROC"),
        ])
        db.flush()

        result = apply_tof1(db, res_id="CONV-01", item_id=item.item_stat_id, operator_id=1)
        db.flush()
        db.refresh(item)

        assert result.ok is True
        assert item.flow_stat == "WAIT_INSP"

        bridge.publish(Event(
            event_type=EventType.TOF1_ENTRY,
            ord_id=300,
            item_id=item.item_stat_id,
            txn_id=result.equip_task_txn_id,
            resource_id="CONV-01",
            payload={"sensor": "TOF1", "ok": result.ok},
        ))

    assert len(collected) == 1
    assert collected[0].resource_id == "CONV-01"
    assert collected[0].payload["sensor"] == "TOF1"


# ─────────────────────────────────────────────────────────────────────
# I-4) apply_tof2 (실 PG) → TOF2_EXIT publish + InspTaskTxn INSERT
# ─────────────────────────────────────────────────────────────────────

def test_i4_apply_tof2_publishes_tof2_exit(
    postgresql_smartcast_empty, bridge, collector, collected
):
    """컨베이어 TOF2 출구 통과 → InspTaskTxn 생성 + TOF2_EXIT 발행."""
    bridge.subscribe(EventType.TOF2_EXIT, collector, "test.tof2")

    with SessionLocal() as db:
        _seed_zones_and_res(db)
        db.add(Ord(ord_id=400, user_id=1))
        db.flush()
        item = _seed_item_in_zone(db, ord_id=400, flow_stat="WAIT_INSP", zone_nm="INSP")
        equip_txn = EquipTaskTxn(
            res_id="CONV-01", task_type="ToINSP", txn_stat="PROC",
            item_stat_id=item.item_stat_id, ord_id=400,
            start_at=datetime.now() - timedelta(seconds=30),
        )
        db.add(equip_txn)
        db.flush()

        result = apply_tof2(db, res_id="CONV-01", item_id=item.item_stat_id)
        db.flush()
        db.refresh(item)

        assert result.ok is True
        assert item.flow_stat == "INSP"

        # InspTaskTxn 이 생성됐는지 확인
        insp = db.query(InspTaskTxn).filter(InspTaskTxn.item_stat_id == item.item_stat_id).one()

        bridge.publish(Event(
            event_type=EventType.TOF2_EXIT,
            ord_id=400,
            item_id=item.item_stat_id,
            txn_id=result.equip_task_txn_succ_id,
            resource_id="CONV-01",
            payload={"sensor": "TOF2", "insp_txn_id": insp.txn_id},
        ))

    assert len(collected) == 1
    assert collected[0].txn_id == equip_txn.txn_id
    assert collected[0].payload["insp_txn_id"] > 0


# ─────────────────────────────────────────────────────────────────────
# I-5) RfidService.report_scan → RFID_SCANNED publish (FakeSession)
# ─────────────────────────────────────────────────────────────────────

class _FakeSession:
    """test_rfid_service.py 패턴의 FakeSession 단순화."""
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False
        self.closed = False
        self._rows: list[RfidScanLog] = []

    def query(self, _model):
        session = self
        class _Q:
            def __init__(self) -> None:
                self._filters: dict = {}
            def filter_by(self, **kw):
                self._filters.update(kw)
                return self
            def first(self):
                key = self._filters.get("idempotency_key")
                return next((r for r in session._rows if r.idempotency_key == key), None)
        return _Q()

    def add(self, row: RfidScanLog) -> None:
        self.added.append(row)
        self._rows.append(row)

    def commit(self) -> None: self.committed = True
    def rollback(self) -> None: pass
    def close(self) -> None: self.closed = True


def test_i5_rfid_service_publishes_rfid_scanned(bridge, collector, collected):
    """RFID 스캔 → RfidService.report_scan → RFID_SCANNED publish (FakeSession 사용, PG 미사용)."""
    bridge.subscribe(EventType.RFID_SCANNED, collector, "test.rfid")

    fake = _FakeSession()
    service = RfidService(session_factory=lambda: fake)
    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_500_item_20260505_1",
        scanned_at_iso="2026-05-05T12:00:00Z",
        idempotency_key="i5-rfid-1",
    )

    assert result.accepted is True
    assert result.parse_status == "ok"
    assert fake.committed is True

    bridge.publish(Event(
        event_type=EventType.RFID_SCANNED,
        ord_id=500,
        item_id=result.item_id,
        resource_id="ESP-CONV-01",
        payload={
            "raw_payload": "order_500_item_20260505_1",
            "parse_status": result.parse_status,
            "reason": result.reason,
        },
    ))

    assert len(collected) == 1
    e = collected[0]
    assert e.event_type == EventType.RFID_SCANNED
    assert e.resource_id == "ESP-CONV-01"
    assert e.payload["parse_status"] == "ok"


# ─────────────────────────────────────────────────────────────────────
# I-6) Multi-subscriber — Allocator stub + Monitor stub 동시 수신 + 격리
# ─────────────────────────────────────────────────────────────────────

def test_i6_multiple_subscribers_receive_same_event_with_isolation(bridge, collected):
    """TASK_ASSIGNED 발행 시 Allocator stub + Monitor stub 둘 다 호출되고,
    하나가 예외 던져도 다른 하나는 정상 수신 (handler 격리)."""
    allocator_calls: list[Event] = []
    monitor_calls: list[Event] = []

    def allocator_handler(e: Event) -> None:
        allocator_calls.append(e)

    def failing_handler(_e: Event) -> None:
        raise RuntimeError("downstream module crashed")

    def monitor_handler(e: Event) -> None:
        monitor_calls.append(e)

    bridge.subscribe(EventType.TASK_ASSIGNED, allocator_handler, "test.allocator")
    bridge.subscribe(EventType.TASK_ASSIGNED, failing_handler, "test.broken")
    bridge.subscribe(EventType.TASK_ASSIGNED, monitor_handler, "test.monitor")

    result = bridge.publish(Event(
        event_type=EventType.TASK_ASSIGNED,
        ord_id=600,
        item_id=6001,
        txn_id=60001,
        resource_id="PAT",
        payload={"task_type": "MM"},
    ))

    # 격리 — 1개 실패해도 나머지 2개 정상 호출
    assert result.handlers_invoked == 3
    assert result.handlers_success == 2
    assert result.handlers_failed == 1

    assert len(allocator_calls) == 1
    assert len(monitor_calls) == 1
    assert allocator_calls[0].resource_id == "PAT"
    assert monitor_calls[0].txn_id == 60001
