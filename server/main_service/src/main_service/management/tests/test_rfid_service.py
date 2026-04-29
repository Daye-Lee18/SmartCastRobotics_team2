"""RFID service smoke tests for Wave 2 scope."""

from __future__ import annotations

from datetime import UTC, datetime

from services.rfid_service import RfidService

from app.models import RfidScanLog


class FakeQuery:
    def __init__(self, session: FakeSession) -> None:
        self._session = session
        self._filters: dict[str, object] = {}

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self):
        idempotency_key = self._filters.get("idempotency_key")
        for row in self._session.rows:
            if row.idempotency_key == idempotency_key:
                return row
        return None


class FakeSession:
    def __init__(self, rows: list[RfidScanLog] | None = None) -> None:
        self.rows = list(rows or [])
        self.added: list[RfidScanLog] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def query(self, _model):
        return FakeQuery(self)

    def add(self, row: RfidScanLog) -> None:
        self.added.append(row)
        self.rows.append(row)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_report_scan_happy_path_persists_parsed_fields() -> None:
    session = FakeSession()
    service = RfidService(session_factory=lambda: session)

    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_1_item_20260417_1",
        scanned_at_iso="2026-04-20T12:34:56Z",
        idempotency_key="ESP-CONV-01:1713616496000",
    )

    assert result.accepted is True
    assert result.item_id == 0
    assert result.parse_status == "ok"
    assert result.reason == "parsed"
    assert session.committed is True
    assert session.closed is True

    assert len(session.added) == 1
    row = session.added[0]
    assert row.reader_id == "ESP-CONV-01"
    assert row.zone == "conveyor_in"
    assert row.raw_payload == "order_1_item_20260417_1"
    assert row.ord_id == "1"
    assert row.item_key == "20260417_1"
    assert row.item_id is None
    assert row.parse_status == "ok"
    assert row.idempotency_key == "ESP-CONV-01:1713616496000"
    assert row.extra == {"via": "grpc", "reason": "parsed"}
    assert row.scanned_at == datetime(2026, 4, 20, 12, 34, 56, tzinfo=UTC)


def test_report_scan_bad_format_persists_raw_only() -> None:
    session = FakeSession()
    service = RfidService(session_factory=lambda: session)

    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="garbled-tag-value",
        scanned_at_iso="2026-04-20T12:34:56Z",
        idempotency_key="ESP-CONV-01:garbled-1",
    )

    assert result.accepted is True
    assert result.parse_status == "bad_format"
    assert result.reason == "payload regex mismatch"
    assert len(session.added) == 1

    row = session.added[0]
    assert row.raw_payload == "garbled-tag-value"
    assert row.ord_id is None
    assert row.item_key is None
    assert row.item_id is None
    assert row.parse_status == "bad_format"
    assert row.extra == {"via": "grpc", "reason": "payload regex mismatch"}


def test_report_scan_invalid_timestamp_surfaces_fallback_in_reason() -> None:
    session = FakeSession()
    service = RfidService(session_factory=lambda: session)

    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_1_item_20260417_1\n",
        scanned_at_iso="not-a-timestamp",
        idempotency_key="ESP-CONV-01:invalid-ts-1",
    )

    assert result.accepted is True
    assert result.parse_status == "ok"
    assert "scanned_at_fallback_now" in result.reason
    assert session.added[0].item_key == "20260417_1"


def test_report_scan_duplicate_idempotency_returns_duplicate_without_insert() -> None:
    existing = RfidScanLog(
        scanned_at=datetime(2026, 4, 20, 12, 34, 56, tzinfo=UTC),
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_1_item_20260417_1",
        ord_id="1",
        item_key="20260417_1",
        item_id=None,
        parse_status="ok",
        idempotency_key="ESP-CONV-01:1713616496000",
        extra={"via": "grpc", "reason": "parsed"},
    )
    session = FakeSession(rows=[existing])
    service = RfidService(session_factory=lambda: session)

    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_1_item_20260417_1",
        scanned_at_iso="2026-04-20T12:35:00Z",
        idempotency_key="ESP-CONV-01:1713616496000",
    )

    assert result.accepted is True
    assert result.item_id == 0
    assert result.parse_status == "duplicate"
    assert "original_parse_status=ok" in result.reason
    assert session.added == []
    assert session.committed is False
    assert session.closed is True


def test_report_scan_duplicate_conflict_rejects_mismatched_payload() -> None:
    existing = RfidScanLog(
        scanned_at=datetime(2026, 4, 20, 12, 34, 56, tzinfo=UTC),
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_1_item_20260417_1",
        ord_id="1",
        item_key="20260417_1",
        item_id=None,
        parse_status="ok",
        idempotency_key="ESP-CONV-01:1713616496000",
        extra={"via": "grpc", "reason": "parsed"},
    )
    session = FakeSession(rows=[existing])
    service = RfidService(session_factory=lambda: session)

    result = service.report_scan(
        reader_id="ESP-CONV-01",
        zone="conveyor_in",
        raw_payload="order_2_item_20260417_9",
        scanned_at_iso="2026-04-20T12:35:00Z",
        idempotency_key="ESP-CONV-01:1713616496000",
    )

    assert result.accepted is False
    assert result.parse_status == "duplicate"
    assert result.reason == "idempotency_key conflict: existing event differs"
    assert session.added == []
    assert session.committed is False
