"""Alert and action/log models aligned to DB schema v21."""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import synonym

from smart_cast_db.database import Base
from smart_cast_db.models._base import (
    SCHEMA,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)


class AlertsStat(Base):
    __tablename__ = "alerts_stat"
    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="chk_alerts_severity"),
        {"schema": SCHEMA},
    )

    id = Column(String, primary_key=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, server_default="info")
    error_code = Column(String, server_default="")
    message = Column(String, nullable=False)
    abnormal_value = Column(String, server_default="")
    zone = Column(String)
    timestamp = Column(String, nullable=False)
    resolved_at = Column(String)
    acknowledged = Column(Boolean, nullable=False, server_default="false")

    # Legacy compatibility
    equipment_id = synonym("res_id")


class LogActionUser(Base):
    __tablename__ = "log_action_user"
    __table_args__ = ({"schema": SCHEMA},)

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"), nullable=False)
    screen_nm = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    ref_id = Column(Integer)
    acted_at = Column(DateTime, server_default=func.now())


class LogActionOperatorHandoffAcks(Base):
    __tablename__ = "log_action_operator_handoff_acks"
    __table_args__ = ({"schema": SCHEMA},)

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"), nullable=False)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    pp_task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.pp_task_txn.txn_id"))
    button_device_id = Column(String)
    idempotency_key = Column(String, unique=True)
    ack_at = Column(DateTime, server_default=func.now())

    # Legacy compatibility
    item_id = synonym("item_stat_id")


class LogActionOperatorRfidScan(Base):
    __tablename__ = "log_action_operator_rfid_scan"
    __table_args__ = (
        CheckConstraint("parse_status IN ('ok', 'bad_format', 'duplicate')", name="chk_rfid_parse_status"),
        Index(
            "uq_rfid_scan_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": SCHEMA},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scanned_at = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    reader_id = Column(String, nullable=False)
    zone = Column(String)
    raw_payload = Column(String, nullable=False)
    ord_id = Column(String)
    item_key = Column(String)
    item_stat_id = Column(Integer, ForeignKey(f"{SCHEMA}.item_stat.item_stat_id"))
    parse_status = Column(String, nullable=False)
    idempotency_key = Column(String)
    extra = Column("metadata", JSONB)

    # Legacy compatibility
    item_id = synonym("item_stat_id")


class LogActionAdmin(Base):
    __tablename__ = "log_action_admin"
    __table_args__ = (
        CheckConstraint("action_type IS NULL OR action_type IN ('INSERT', 'UPDATE', 'DELETE')", name="chk_admin_action_type"),
        {"schema": SCHEMA},
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_account.user_id"), nullable=False)
    target_table = Column(String(50), nullable=False)
    target_id = Column(String(50))
    action_type = Column(String(10))
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    acted_at = Column(DateTime, server_default=func.now())


class LogEvent(Base):
    __tablename__ = "log_event"
    __table_args__ = ({"schema": SCHEMA},)

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String(20), nullable=False)
    event_type = Column(String(50), nullable=False)
    txn_id = Column(Integer)
    detail = Column(Text)
    occured_at = Column(DateTime, server_default=func.now())
