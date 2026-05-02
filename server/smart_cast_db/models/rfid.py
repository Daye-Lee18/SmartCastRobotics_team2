"""RFID 로그 모델 — RfidScanLog.

public.rfid_scan_log 는 append-only 로그이므로 별도 파일로 분리한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ._base import Base, BigInteger, Column, DateTime, Index, String
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RfidScanLog(Base):
    """RFID 스캔 append-only 로그 (public.rfid_scan_log)."""

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
