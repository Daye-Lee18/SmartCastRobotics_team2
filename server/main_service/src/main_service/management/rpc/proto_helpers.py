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

_WO_STATUS_TO_ENUM = {"QUE": 1, "PROC": 2, "SUCC": 3, "FAIL": 4}


def _ts(iso_str):
    return management_pb2.Timestamp(iso8601=iso_str or "")


def item_to_proto(item):
    """smartcast Item -> proto Item (SPEC-C3, 2026-04-20)."""
    updated = item.updated_at.isoformat() if getattr(item, "updated_at", None) else ""
    return management_pb2.Item(
        id=item.item_id,
        order_id=str(item.ord_id or ""),
        cur_stage=_STAGE_NAME_TO_ENUM.get(item.cur_stat or "", 0),
        curr_res=item.cur_res or "",
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

