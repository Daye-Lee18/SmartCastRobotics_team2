"""Field event ingestion RPC methods."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

import grpc
import management_pb2  # type: ignore

from services.adapters.sensors.rfid_service import RfidServiceError

logger = logging.getLogger(__name__)


def _item_state_label(item) -> str:
    return getattr(item, "flow_stat", None) or ""


def _handoff_task_id_from_extra(extra: object) -> str:
    if not isinstance(extra, dict):
        return ""
    task_id = extra.get("trans_task_txn_id")
    return str(task_id) if task_id is not None else ""


def _pp_option_proto(option: dict) -> management_pb2.PpOptionView:
    return management_pb2.PpOptionView(
        pp_id=int(option.get("pp_id") or 0),
        pp_nm=option.get("pp_nm") or "",
        extra_cost=float(option.get("extra_cost") or 0.0),
        txn_stat=str(option.get("txn_stat") or ""),
        txn_id=int(option.get("txn_id") or 0),
        map_id=int(option.get("map_id") or 0),
    )


def _notify_handoff_ack(result, *, zone: str, ack_at_iso: str) -> None:
    import json as _json
    import urllib.request

    notify_url = os.environ.get(
        "INTERFACE_NOTIFY_URL",
        "http://localhost:8000/api/debug/_notify/handoff-ack",
    )
    body = _json.dumps(
        {
            "task_id": result.task_id,
            "amr_id": result.amr_id or "",
            "item_id": result.item_id,
            "ord_id": result.ord_id,
            "zone": zone,
            "ack_at": ack_at_iso,
            "orphan": result.orphan,
            "source": "management_grpc",
            "pp_task_txn_ids": result.pp_task_txn_ids,
            "item_cur_stat": result.item_cur_stat,
        }
    ).encode()
    req = urllib.request.Request(
        notify_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=1.0).read()


def _build_rfid_ack_details(item_id: int) -> tuple[str, int, list[management_pb2.PpOptionView]]:
    from services.core.legacy.handoff_pipeline import build_pp_options_view

    from smart_cast_db.database import SessionLocal
    from smart_cast_db.models import ItemStat

    item_cur_stat = ""
    ord_id_int = 0
    pp_options_proto: list[management_pb2.PpOptionView] = []
    db = SessionLocal()
    try:
        item = db.get(ItemStat, item_id)
        if item is not None:
            item_cur_stat = _item_state_label(item)
            ord_id_int = int(item.ord_id) if item.ord_id else 0
            for opt in build_pp_options_view(db, item):
                pp_options_proto.append(_pp_option_proto(opt))
    finally:
        db.close()
    return item_cur_stat, ord_id_int, pp_options_proto


class FieldEventRpcMixin:
    """Handoff, RFID, and conveyor event RPCs."""

    def ReportHandoffAck(self, request, context):
        from services.core.legacy.handoff_pipeline import apply_handoff

        from smart_cast_db.database import SessionLocal
        from smart_cast_db.models.models_legacy import HandoffAck

        zone = request.zone or "postprocessing"
        source_device = request.source_device or "unknown"
        idempotency_key = request.idempotency_key or None
        now_utc = datetime.now(UTC)

        if idempotency_key:
            dup_db = SessionLocal()
            try:
                dup = (
                    dup_db.query(HandoffAck)
                    .filter(HandoffAck.idempotency_key == idempotency_key)
                    .first()
                )
                if dup is not None:
                    logger.info("ReportHandoffAck: 중복 이벤트 skip key=%s", idempotency_key)
                    return management_pb2.HandoffAckResponse(
                        accepted=True,
                        task_id=_handoff_task_id_from_extra(dup.extra),
                        amr_id=dup.amr_id or "",
                        reason="duplicate",
                        ack_at=dup.ack_at.isoformat() if dup.ack_at else now_utc.isoformat(),
                    )
            finally:
                dup_db.close()

        db = SessionLocal()
        try:
            try:
                result = apply_handoff(
                    db,
                    button_device_id=source_device,
                    ack_source="esp32_button",
                    via="grpc",
                    idempotency_key=idempotency_key,
                )
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
                raise
        finally:
            db.close()

        fsm_reason = result.reason
        if result.amr_id:
            ok, _r = self.amr_state_machine.confirm_handoff(result.amr_id)
            if ok:
                fsm_reason = "released"
            else:
                fsm_reason = f"db_committed_fsm_reject:{_r}"

        try:
            _notify_handoff_ack(result, zone=zone, ack_at_iso=now_utc.isoformat())
        except Exception as e:  # noqa: BLE001
            logger.warning("Handoff WebSocket notify 실패 (무시): %s", e)

        return management_pb2.HandoffAckResponse(
            accepted=True,
            task_id=str(result.task_id) if result.task_id else "",
            amr_id=result.amr_id or "",
            reason=fsm_reason,
            ack_at=now_utc.isoformat(),
        )

    def ReportRfidScan(self, request, context):
        try:
            result = self.rfid_service.report_scan(
                reader_id=request.reader_id,
                zone=request.zone or None,
                raw_payload=request.raw_payload,
                scanned_at_iso=request.scanned_at.iso8601 or None,
                idempotency_key=request.idempotency_key or None,
            )
        except RfidServiceError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return management_pb2.RfidScanAck()

        item_cur_stat = ""
        ord_id_int = 0
        pp_options_proto: list[management_pb2.PpOptionView] = []
        if result.accepted and result.item_id:
            item_cur_stat, ord_id_int, pp_options_proto = _build_rfid_ack_details(result.item_id)

        return management_pb2.RfidScanAck(
            accepted=result.accepted,
            item_id=result.item_id,
            parse_status=result.parse_status,
            reason=result.reason,
            item_cur_stat=item_cur_stat,
            ord_id=ord_id_int,
            pp_options=pp_options_proto,
        )

    def ReportConveyorEvent(self, request, context):
        from services.core.legacy.handoff_pipeline import apply_tof1, apply_tof2

        from smart_cast_db.database import SessionLocal

        res_id = request.res_id or "CONV-01"
        event = (request.event_type or "").strip().lower()
        rfid_payload = request.rfid_payload or None
        item_id = int(request.item_id) if request.item_id else None

        if event not in ("tof1_entry", "tof2_exit"):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"unknown event_type={event!r} (expected tof1_entry|tof2_exit)")
            return management_pb2.ConveyorEventAck()

        db = SessionLocal()
        try:
            try:
                if event == "tof1_entry":
                    r1 = apply_tof1(db, res_id=res_id, rfid_payload=rfid_payload, item_id=item_id)
                    db.commit()
                    return management_pb2.ConveyorEventAck(
                        accepted=r1.ok,
                        item_id=int(r1.item_id or 0),
                        item_cur_stat=r1.item_cur_stat or "",
                        equip_task_txn_id=int(r1.equip_task_txn_id or 0),
                        insp_task_txn_id=0,
                        reason=r1.reason,
                    )
                r2 = apply_tof2(db, res_id=res_id, item_id=item_id)
                db.commit()
                return management_pb2.ConveyorEventAck(
                    accepted=r2.ok,
                    item_id=int(r2.item_id or 0),
                    item_cur_stat=r2.item_cur_stat or "",
                    equip_task_txn_id=int(r2.equip_task_txn_succ_id or 0),
                    insp_task_txn_id=int(r2.insp_task_txn_id or 0),
                    reason=r2.reason,
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.exception("ReportConveyorEvent 실패 res=%s event=%s: %s", res_id, event, exc)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(exc))
                return management_pb2.ConveyorEventAck()
        finally:
            db.close()
