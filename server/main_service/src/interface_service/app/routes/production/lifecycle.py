from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.clients.management import ManagementClient, ManagementUnavailable
from app.schemas.schemas import ProductionStartRequest
from smart_cast_db.database import get_db
from smart_cast_db.models import EquipTaskTxn, Item, Ord, OrdDetail, OrdLog, OrdPattern, OrdStat

router = APIRouter(prefix="/api/production", tags=["production"])


# -----------------------------------------------------------------------------
# Production Start (Pink GUI #5)
# -----------------------------------------------------------------------------

def _start_production_proxy(payload: ProductionStartRequest) -> dict:
    """Management gRPC proxy 경로 (feature flag ON). SPEC-C2 Iteration 3."""
    try:
        result = ManagementClient.get().start_production(payload.ord_id)
    except ValueError as exc:
        msg = str(exc)
        # task_manager 의 "not found" 는 404, "not registered" 는 400 으로 매핑
        if "not found" in msg:
            raise HTTPException(404, msg) from exc
        raise HTTPException(400, msg) from exc
    except ManagementUnavailable as exc:
        raise HTTPException(503, f"Management Service unavailable: {exc}") from exc
    return {
        "ord_id": result.ord_id,
        "item_id": result.item_id,
        "equip_task_txn_id": result.equip_task_txn_id,
        "message": result.message,
    }


def _start_production_local(payload: ProductionStartRequest, db: Session) -> dict:
    """Local DB fallback for PyQt/manual runs when Management gRPC is not running."""
    ord_obj = db.get(Ord, payload.ord_id)
    if ord_obj is None:
        raise HTTPException(404, f"ord_id={payload.ord_id} not found")

    detail = db.get(OrdDetail, payload.ord_id)
    if detail is None:
        raise HTTPException(400, f"ord_id={payload.ord_id} has no ord_detail")

    pattern = db.get(OrdPattern, payload.ord_id)
    if pattern is None or pattern.ptn_loc_id is None:
        raise HTTPException(400, f"pattern location for ord_id={payload.ord_id} not registered")

    stat = db.query(OrdStat).filter(OrdStat.ord_id == payload.ord_id).first()
    prev_stat = stat.ord_stat if stat is not None else None
    if prev_stat != "APPR":
        raise HTTPException(400, f"ord_id={payload.ord_id} must be APPR before production start; current={prev_stat}")

    existing_item = db.query(Item).filter(Item.ord_id == payload.ord_id).first()
    if existing_item is not None:
        raise HTTPException(400, f"ord_id={payload.ord_id} already started on line")

    item_ids: list[int] = []
    equip_task_txn_ids: list[int] = []
    qty = int(detail.qty or 0)
    for _ in range(qty):
        item = Item(
            ord_id=payload.ord_id,
            equip_task_type="MM",
            cur_stat="CREATED",
            cur_res="PAT",
            is_defective=None,
        )
        db.add(item)
        db.flush()
        item_ids.append(item.item_id)

        equip_task = EquipTaskTxn(
            res_id="PAT",
            task_type="MM",
            txn_stat="QUE",
            item_id=item.item_id,
        )
        db.add(equip_task)
        db.flush()
        equip_task_txn_ids.append(equip_task.txn_id)

    stat.ord_stat = "MFG"
    db.add(OrdLog(ord_id=payload.ord_id, prev_stat=prev_stat, new_stat="MFG", changed_by=None))
    db.commit()

    return {
        "ord_id": payload.ord_id,
        "item_id": item_ids[0] if item_ids else None,
        "item_ids": item_ids,
        "equip_task_txn_id": equip_task_txn_ids[0] if equip_task_txn_ids else None,
        "equip_task_txn_ids": equip_task_txn_ids,
        "message": f"Production started locally: {len(item_ids)} item(s), ptn_loc_id={pattern.ptn_loc_id}.",
    }


@router.post("/start")
def start_production(payload: ProductionStartRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return _start_production_proxy(payload)
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        return _start_production_local(payload, db)
