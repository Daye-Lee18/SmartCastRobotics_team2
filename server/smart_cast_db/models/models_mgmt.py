"""Management/action log models aligned to create_tables.sql."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    synonym,
)
from .alert import AlertsStat
from .rfid import LogActionOperatorRfidScan


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
    item_id = Column(Integer, ForeignKey(f"{SCHEMA}.item.item_id"))
    pp_task_txn_id = Column(Integer, ForeignKey(f"{SCHEMA}.pp_task_txn.txn_id"))
    button_device_id = Column(String)
    idempotency_key = Column(String, unique=True)
    ack_at = Column(DateTime, server_default=func.now())

    item_stat_id = synonym("item_id")


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
