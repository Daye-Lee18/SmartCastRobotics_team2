"""Field event ingestion RPC methods."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

import grpc
import management_pb2  # type: ignore

from services.rfid_service import RfidServiceError

logger = logging.getLogger(__name__)


class FieldEventRpcMixin:
    """Handoff, RFID, and conveyor event RPCs."""

    def ReportHandoffAck(self, request, context):
        from services.handoff_pipeline import apply_handoff

        from smart_cast_db.database import SessionLocal
        from smart_cast_db.models import HandoffAck

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
                        task_id=dup.extra.get("trans_task_txn_id")
                        if isinstance(dup.extra, dict)
                        else "",
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
                    "ack_at": now_utc.isoformat(),
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
        pp_options_proto: list = []
        if result.accepted and result.item_id:
            from services.handoff_pipeline import build_pp_options_view

            from smart_cast_db.database import SessionLocal
            from smart_cast_db.models import Item

            db = SessionLocal()
            try:
                item = db.get(Item, result.item_id)
                if item is not None:
                    item_cur_stat = item.cur_stat or ""
                    ord_id_int = int(item.ord_id) if item.ord_id else 0
                    for opt in build_pp_options_view(db, item):
                        pp_options_proto.append(
                            management_pb2.PpOptionView(
                                pp_id=int(opt.get("pp_id") or 0),
                                pp_nm=opt.get("pp_nm") or "",
                                extra_cost=float(opt.get("extra_cost") or 0.0),
                                txn_stat=str(opt.get("txn_stat") or ""),
                                txn_id=int(opt.get("txn_id") or 0),
                                map_id=int(opt.get("map_id") or 0),
                            )
                        )
            finally:
                db.close()

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
        from services.handoff_pipeline import apply_tof1, apply_tof2

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

