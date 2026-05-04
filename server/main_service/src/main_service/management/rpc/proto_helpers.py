"""Helpers for converting internal records to Management protobuf messages."""

from __future__ import annotations

import management_pb2  # type: ignore


_STAGE_NAME_TO_ENUM = {
    "QUE": 1,
    "MM": 2,
    "DM": 3,
    "TR_PP": 4,
    "PP": 5,
    "IP": 6,
    "TR_LD": 7,
    "SH": 8,
}

_FLOW_TO_LEGACY_STAGE = {
    "CREATED": "QUE",
    "CAST": "MM",
    "WAIT_PP": "TR_PP",
    "PP": "PP",
    "WAIT_INSP": "QUE",
    "INSP": "IP",
    "WAIT_PA": "QUE",
    "PA": "PP",
    "STORED": "TR_LD",
    "PICK": "TR_LD",
    "READY_TO_SHIP": "SH",
    "DISCARDED": "SH",
    "HOLD": "QUE",
}

_WO_STATUS_TO_ENUM = {"QUE": 1, "PROC": 2, "SUCC": 3, "FAIL": 4}


def _ts(iso_str):
    return management_pb2.Timestamp(iso8601=iso_str or "")


def _legacy_stage(item) -> str:
    flow_stat = getattr(item, "flow_stat", None)
    if flow_stat is None:
        cur_stat = getattr(item, "cur_stat", None)
        if cur_stat:
            return str(cur_stat)
    return _FLOW_TO_LEGACY_STAGE.get((flow_stat or "").upper(), "QUE")


def _current_resource(item) -> str:
    zone_nm = getattr(item, "zone_nm", None)
    if zone_nm is None:
        cur_res = getattr(item, "cur_res", None)
        if cur_res:
            return str(cur_res)
    return zone_nm or ""


def item_to_proto(item):
    """smartcast Item -> proto Item (SPEC-C3, 2026-04-20)."""
    updated = item.updated_at.isoformat() if getattr(item, "updated_at", None) else ""
    stage = _legacy_stage(item)
    item_id = getattr(item, "item_stat_id", None)
    if item_id is None:
        item_id = getattr(item, "item_id", 0)
    return management_pb2.Item(
        id=item_id,
        order_id=str(getattr(item, "ord_id", "") or ""),
        cur_stage=_STAGE_NAME_TO_ENUM.get(stage, 0),
        curr_res=_current_resource(item),
        insp_id=0,
        mfg_at=_ts(updated),
    )


def start_result_to_proto(r):
    """StartProductionResult dataclass -> proto."""
    return management_pb2.StartProductionResult(
        ord_id=r.ord_id,
        item_id=r.item_id,
        equip_task_txn_id=r.equip_task_txn_id,
        message=r.message or "",
    )


def start_result_to_order_ack(r, *, accepted=True, reason=""):
    """StartProductionResult dataclass -> canonical StartProductionOrderAck proto."""
    return management_pb2.StartProductionOrderAck(
        ord_id=r.ord_id,
        accepted=accepted,
        reason=reason or r.message or "",
        item_id=r.item_id,
        equip_task_txn_id=r.equip_task_txn_id,
    )


def build_batch_start_ack(order_ids, results):
    """Build per-order batch ack while keeping legacy TaskManager behavior.

    Legacy TaskManager currently returns only successful rows and silently skips
    invalid/missing/unregistered orders. For the skeleton response we preserve
    that behavior but expose it as explicit per-order accepted/rejected results.
    """
    normalized_order_ids = list(order_ids)
    accepted_by_ord_id = {int(r.ord_id): r for r in results}
    order_acks = []
    accepted_count = 0

    for raw in normalized_order_ids:
        try:
            parsed = int(str(raw).strip())
        except ValueError:
            order_acks.append(
                management_pb2.StartProductionOrderAck(
                    ord_id=0,
                    accepted=False,
                    reason=f"invalid order_id: {raw}",
                )
            )
            continue

        result = accepted_by_ord_id.get(parsed)
        if result is None:
            order_acks.append(
                management_pb2.StartProductionOrderAck(
                    ord_id=parsed,
                    accepted=False,
                    reason="rejected_or_skipped_by_legacy_path",
                )
            )
            continue

        accepted_count += 1
        order_acks.append(start_result_to_order_ack(result))

    requested_count = len(normalized_order_ids)
    rejected_count = requested_count - accepted_count
    return management_pb2.StartProductionAck(
        requested_count=requested_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        orders=order_acks,
        message=f"{accepted_count}/{requested_count} orders accepted",
    )


def result_to_legacy_work_order(r):
    """smartcast start_production_single result -> legacy WorkOrder proto."""
    return management_pb2.WorkOrder(
        id=r.item_id,
        order_id=str(r.ord_id),
        pattern_id="",
        qty=1,
        status=_WO_STATUS_TO_ENUM.get("QUE", 0),
        plan_start=_ts(None),
        act_start=_ts(None),
        act_end=_ts(None),
    )
