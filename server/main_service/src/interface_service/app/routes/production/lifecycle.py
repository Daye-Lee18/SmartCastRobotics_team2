from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.clients.management import ManagementClient, ManagementUnavailable
from smart_cast_db.database import get_db
from smart_cast_db.models import EquipStat, EquipTaskTxn, Item, Ord, OrdStat, Pattern
from app.schemas.schemas import ProductionStartRequest

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

@router.post("/start")
def start_production(payload: ProductionStartRequest) -> dict:
    return _start_production_proxy(payload)
