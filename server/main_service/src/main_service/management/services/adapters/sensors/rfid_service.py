"""RFID scan ingest service for `ReportRfidScan`.

Wave 2 범위:
- append-only `rfid_scan_log` 저장
- payload regex 파싱
- idempotency duplicate 처리

제외 범위:
- item lookup / item binding
- unknown_item 판정
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MANAGEMENT_DIR = os.path.dirname(_THIS_DIR)
_BACKEND_DIR = os.path.dirname(_MANAGEMENT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from smart_cast_db.database import SessionLocal
from smart_cast_db.models import RfidScanLog

logger = logging.getLogger(__name__)

RFID_PAYLOAD_RE = re.compile(r"^order_(?P<ord>\d+)_item_(?P<date>\d{8})_(?P<seq>\d+)$")


@dataclass(frozen=True)
class RfidScanResult:
    """`RfidScanAck` 대응 내부 결과."""

    accepted: bool
    item_id: int
    parse_status: str
    reason: str


class RfidServiceError(ValueError):
    """RFID 도메인 오류 — gRPC INVALID_ARGUMENT 로 매핑."""


class RfidService:
    """RFID 스캔 이벤트를 파싱하고 append-only 로그에 저장한다."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def report_scan(
        self,
        *,
        reader_id: str,
        zone: str | None,
        raw_payload: str,
        scanned_at_iso: str | None,
        idempotency_key: str | None,
    ) -> RfidScanResult:
        normalized_reader_id = (reader_id or "").strip()
        if not normalized_reader_id:
            raise RfidServiceError("reader_id required")

        normalized_zone = (zone or "").strip() or None
        normalized_payload = raw_payload or ""
        parse_payload = normalized_payload.strip()
        normalized_key = (idempotency_key or "").strip() or None
        scanned_at, scanned_at_note = _parse_scanned_at(scanned_at_iso)

        match = RFID_PAYLOAD_RE.fullmatch(parse_payload)
        ord_id: str | None = None
        item_key: str | None = None
        parse_status = "bad_format"
        reason = "payload regex mismatch"
        if match is not None:
            ord_id = match.group("ord")
            item_key = f"{match.group('date')}_{match.group('seq')}"
            parse_status = "ok"
            reason = "parsed"
        if scanned_at_note:
            reason = f"{reason}; {scanned_at_note}"

        db = self._session_factory()
        try:
            if normalized_key:
                duplicate = db.query(RfidScanLog).filter_by(idempotency_key=normalized_key).first()
                if duplicate is not None:
                    logger.info("ReportRfidScan: duplicate skip key=%s", normalized_key)
                    return _duplicate_result(
                        duplicate,
                        reader_id=normalized_reader_id,
                        zone=normalized_zone,
                        raw_payload=normalized_payload,
                    )

            db.add(
                RfidScanLog(
                    scanned_at=scanned_at,
                    reader_id=normalized_reader_id,
                    zone=normalized_zone,
                    raw_payload=normalized_payload,
                    ord_id=ord_id,
                    item_key=item_key,
                    item_id=None,
                    parse_status=parse_status,
                    idempotency_key=normalized_key,
                    extra={"via": "grpc", "reason": reason},
                )
            )
            db.commit()
            return RfidScanResult(
                accepted=True,
                item_id=0,
                parse_status=parse_status,
                reason=reason,
            )
        except IntegrityError:
            db.rollback()
            if normalized_key:
                duplicate = db.query(RfidScanLog).filter_by(idempotency_key=normalized_key).first()
                if duplicate is not None:
                    logger.info("ReportRfidScan: duplicate on commit key=%s", normalized_key)
                    return _duplicate_result(
                        duplicate,
                        reader_id=normalized_reader_id,
                        zone=normalized_zone,
                        raw_payload=normalized_payload,
                    )
            raise
        finally:
            db.close()


def _parse_scanned_at(scanned_at_iso: str | None) -> tuple[datetime, str | None]:
    if not scanned_at_iso:
        return datetime.now(UTC), None

    try:
        parsed = datetime.fromisoformat(scanned_at_iso.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("ReportRfidScan: invalid scanned_at=%r, fallback now()", scanned_at_iso)
        return datetime.now(UTC), "scanned_at_fallback_now"

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC), None
    return parsed, None


def _duplicate_result(
    row: RfidScanLog,
    *,
    reader_id: str,
    zone: str | None,
    raw_payload: str,
) -> RfidScanResult:
    if row.reader_id != reader_id or row.zone != zone or row.raw_payload != raw_payload:
        return RfidScanResult(
            accepted=False,
            item_id=int(row.item_id or 0),
            parse_status="duplicate",
            reason="idempotency_key conflict: existing event differs",
        )

    original_status = row.parse_status or "unknown"
    return RfidScanResult(
        accepted=True,
        item_id=int(row.item_id or 0),
        parse_status="duplicate",
        reason=f"duplicate idempotency_key (original_parse_status={original_status})",
    )
