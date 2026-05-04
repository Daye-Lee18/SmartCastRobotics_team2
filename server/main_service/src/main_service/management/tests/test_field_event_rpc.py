from __future__ import annotations

from types import SimpleNamespace

import management_pb2  # type: ignore

from rpc.field_event_rpc import FieldEventRpcMixin
from services.adapters.sensors.rfid_service import RfidScanResult
from smart_cast_db.database import SessionLocal
from smart_cast_db.models import ItemStat, Ord, Zone


class _Context:
    code = None
    details = None

    def set_code(self, code) -> None:
        self.code = code

    def set_details(self, details: str) -> None:
        self.details = details


class _RfidService:
    def __init__(self, result: RfidScanResult) -> None:
        self._result = result

    def report_scan(self, **_kwargs):
        return self._result


class _Servicer(FieldEventRpcMixin):
    def __init__(self, *, rfid_result: RfidScanResult | None = None) -> None:
        self.rfid_service = _RfidService(
            rfid_result or RfidScanResult(True, 0, "ok", "parsed")
        )


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_report_rfid_scan_uses_item_stat_canonical_fields(postgresql_smartcast_empty) -> None:
    with SessionLocal() as db:
        db.add(Zone(zone_nm="INSP"))
        db.add(Ord(ord_id=501, user_id=1))
        db.flush()
        item = ItemStat(ord_id=501, flow_stat="WAIT_INSP", zone_nm="INSP")
        db.add(item)
        db.flush()
        item_id = item.item_stat_id
        db.commit()

    servicer = _Servicer(rfid_result=RfidScanResult(True, item_id, "ok", "parsed"))
    request = management_pb2.RfidScanEvent(
        reader_id="R1",
        zone="conveyor_in",
        raw_payload="order_501_item_20260501_1",
        scanned_at=management_pb2.Timestamp(iso8601="2026-05-01T12:00:00+00:00"),
        idempotency_key="rfid-501",
    )

    response = servicer.ReportRfidScan(request, _Context())

    assert response.accepted is True
    assert response.item_id == item_id
    assert response.item_cur_stat == "WAIT_INSP"
    assert response.ord_id == 501
    assert list(response.pp_options) == []


def test_report_conveyor_event_tof1_projects_result_fields(monkeypatch) -> None:
    fake_session = _FakeSession()
    apply_result = SimpleNamespace(
        ok=True,
        item_id=17,
        item_cur_stat="WAIT_INSP",
        equip_task_txn_id=23,
        reason="tof1_ok",
    )

    import rpc.field_event_rpc as field_event_rpc_module
    import smart_cast_db.database as database_module
    import services.legacy.handoff_pipeline as handoff_pipeline_module

    monkeypatch.setattr(database_module, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(handoff_pipeline_module, "apply_tof1", lambda *args, **kwargs: apply_result)

    servicer = _Servicer()
    request = management_pb2.ConveyorEvent(
        res_id="CONV-01",
        event_type="tof1_entry",
        item_id=17,
    )

    response = servicer.ReportConveyorEvent(request, _Context())

    assert response.accepted is True
    assert response.item_id == 17
    assert response.item_cur_stat == "WAIT_INSP"
    assert response.equip_task_txn_id == 23
    assert response.insp_task_txn_id == 0
    assert response.reason == "tof1_ok"
    assert fake_session.committed is True
    assert fake_session.closed is True
