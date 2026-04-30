"""Management Service 전용 테이블 (SPEC-C5 / 2026-04-23 스키마 이관).

- TransportTask (smartcast.transport_tasks) — SPEC-AMR-001 이송 작업
- HandoffAck (smartcast.handoff_acks) — SPEC-AMR-001 후처리존 인수인계 이벤트
- Alert (public.alerts) — execution_monitor 의 SLA 타임아웃 기록 (public 유지)
- RfidScanLog (public.rfid_scan_log) — SPEC-RFID-001 RFID 스캔 append-only 로그 (public 유지)
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from smart_cast_db.database import Base
from smart_cast_db.models._base import (
    SCHEMA as SMARTCAST_SCHEMA,
)  # 2026-04-27 models.py 분할 후 _base.py 로 이동


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Alert(Base):
    """알림 (public.alerts)."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, index=True)
    equipment_id = Column(String, nullable=True, default="")
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="info")
    error_code = Column(String, nullable=True, default="")
    message = Column(String, nullable=False)
    abnormal_value = Column(String, nullable=True, default="")
    zone = Column(String, nullable=True)
    timestamp = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)
    acknowledged = Column(Boolean, nullable=False, default=False)


class TransportTask(Base):
    """이송 작업 (smartcast.transport_tasks) — 2026-04-23 public → smartcast 이관."""

    __tablename__ = "transport_tasks"
    __table_args__ = ({"schema": SMARTCAST_SCHEMA},)

    id = Column(String, primary_key=True, index=True)
    from_name = Column(String, nullable=False)
    from_coord = Column(String, nullable=True, default="")
    to_name = Column(String, nullable=False)
    to_coord = Column(String, nullable=True, default="")
    item_id = Column(String, nullable=True, default="")
    item_name = Column(String, nullable=True, default="")
    quantity = Column(Integer, nullable=False, default=1)
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="unassigned")
    assigned_robot_id = Column(String, nullable=True, default="")
    requested_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)


class HandoffAck(Base):
    """후처리존 인수인계 확인 이벤트 (smartcast.handoff_acks) — SPEC-AMR-001.

    Management Service 가 ESP32 버튼 이벤트 수신 시 AMR FSM 전이와 함께 INSERT.
    2026-04-23: public → smartcast 이관.
    """

    __tablename__ = "handoff_acks"
    __table_args__ = ({"schema": SMARTCAST_SCHEMA},)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ack_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    task_id = Column(
        String,
        ForeignKey(f"{SMARTCAST_SCHEMA}.transport_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    zone = Column(String, nullable=False, index=True)
    amr_id = Column(String, nullable=True)
    ack_source = Column(
        String, nullable=False
    )  # 'esp32_button' | 'debug_endpoint' | 'gui_override'
    operator_id = Column(String, nullable=True)
    button_device_id = Column(String, nullable=True)
    orphan_ack = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String, nullable=True)
    extra = Column("metadata", JSONB, nullable=True)  # 'metadata' 충돌 회피


class RfidScanLog(Base):
    """RFID 스캔 append-only 로그 (public.rfid_scan_log) — SPEC-RFID-001 Wave 2.

    payload 파싱과 idempotency 만 저장하며, item lookup 은 현재 범위에서 제외한다.
    DB migration 의 composite PK(hypertable 호환)를 ORM 에도 반영한다.
    """

    __tablename__ = "rfid_scan_log"
    __table_args__ = (
        Index(
            "idx_rfid_scan_reader_time",
            "reader_id",
            text("scanned_at DESC"),
        ),
        Index(
            "idx_rfid_scan_item_time",
            "item_id",
            text("scanned_at DESC"),
            postgresql_where=text("item_id IS NOT NULL"),
        ),
        Index(
            "idx_rfid_scan_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": "public"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scanned_at = Column(
        DateTime(timezone=True), primary_key=True, nullable=False, default=_utc_now, index=True
    )
    reader_id = Column(String, nullable=False, index=True)
    zone = Column(String, nullable=True)
    raw_payload = Column(String, nullable=False)
    ord_id = Column(String, nullable=True)
    item_key = Column(String, nullable=True)
    item_id = Column(BigInteger, nullable=True)
    parse_status = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=True)
    extra = Column("metadata", JSONB, nullable=True)  # 'metadata' 충돌 회피
