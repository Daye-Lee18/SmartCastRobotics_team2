"""RFID log model aligned to create_tables.sql."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

from ._base import Base, BigInteger, Column, DateTime, Index, SCHEMA, String, synonym


class LogActionOperatorRfidScan(Base):
    __tablename__ = "log_action_operator_rfid_scan"
    __table_args__ = (
        Index(
            "uq_rfid_scan_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": SCHEMA},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scanned_at = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    reader_id = Column(String, nullable=False)
    zone = Column(String)
    raw_payload = Column(String, nullable=False)
    ord_id = Column(String)
    item_key = Column(String)
    item_id = Column(BigInteger)
    parse_status = Column(String, nullable=False)
    idempotency_key = Column(String)
    extra = Column("metadata", JSONB)

    item_stat_id = synonym("item_id")


RfidScanLog = LogActionOperatorRfidScan
