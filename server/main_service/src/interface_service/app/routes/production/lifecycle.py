"""Production lifecycle endpoints — 생산 시작 + equip_task 진행.

Endpoints:
    POST /api/production/start                          발주 생산 시작 (Pink GUI #5)
    POST /api/production/equip-tasks/{txn_id}/advance   equip_task_txn 다음 cur_stat 진행

V6 canonical Phase C-2: INTERFACE_PROXY_START_PRODUCTION=1 이면 Mgmt gRPC proxy,
아니면 legacy DB-direct 경로. flag 는 모듈 import 시점 고정 (worker race 방지).

advance_equip_task 는 IDLE 도달 시 _auto_progress_after_idle 가
MM→POUR→DM→ToPP 자동 체인 생성 (Gap 1, 2026-04-27).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.clients.management import ManagementClient, ManagementUnavailable
from smart_cast_db.database import get_db
from smart_cast_db.models import EquipStat, EquipTaskTxn, Item, Ord, OrdPattern, OrdStat
from app.schemas.schemas import ProductionStartRequest

from ._helpers import _PROXY_START_PRODUCTION, _auto_progress_after_idle, _latest_ord_stat

router = APIRouter(prefix="/api/production", tags=["production"])


# -----------------------------------------------------------------------------
# Production Start (Pink GUI #5)
# -----------------------------------------------------------------------------


def _start_production_legacy(payload: ProductionStartRequest, db: Session) -> dict:
    """Legacy DB-direct 경로 (feature flag OFF 기본값). 2주 유예 후 제거 예정."""
    ord_obj = db.get(Ord, payload.ord_id)
    if not ord_obj:
        raise HTTPException(404, f"ord_id={payload.ord_id} not found")
    latest_stat = _latest_ord_stat(db, payload.ord_id)
    if latest_stat not in {"APPR", "MFG"}:
        raise HTTPException(
            400,
            f"ord_id={payload.ord_id} must be APPR/MFG before production start; current={latest_stat}",
        )
    if not db.get(OrdPattern, payload.ord_id):
        raise HTTPException(
            400,
            f"pattern for ord_id={payload.ord_id} not registered. "
            "Register pattern first (Pink GUI #3) before starting production.",
        )
    db.add(OrdStat(ord_id=payload.ord_id, ord_stat="MFG"))
    new_item = Item(
        ord_id=payload.ord_id,
        equip_task_type="MM",
        trans_task_type=None,
        cur_stat="QUE",
        cur_res="PAT",
    )
    db.add(new_item)
    db.flush()
    txn = EquipTaskTxn(
        res_id="PAT",
        task_type="MM",
        txn_stat="QUE",
        item_id=new_item.item_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(new_item)
    db.refresh(txn)
    return {
        "ord_id": payload.ord_id,
        "item_id": new_item.item_id,
        "equip_task_txn_id": txn.txn_id,
        "message": "Production started: PAT/MM task queued.",
    }


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
def start_production(payload: ProductionStartRequest, db: Session = Depends(get_db)) -> dict:
    """발주 생산 시작 — V6 canonical Phase C-2.

    INTERFACE_PROXY_START_PRODUCTION=1 (모듈 import 시점 고정) 이면 Management
    gRPC proxy, 아니면 legacy DB-direct 경로. 응답 shape 은 두 경로 동일.

    선행 조건: pattern 등록 완료 (Pink GUI #3, 또는 자동 매핑).
    """
    latest_stat = _latest_ord_stat(db, payload.ord_id)
    if latest_stat not in {"APPR", "MFG"}:
        raise HTTPException(
            400,
            f"ord_id={payload.ord_id} must be APPR/MFG before production start; current={latest_stat}",
        )
    if _PROXY_START_PRODUCTION:
        return _start_production_proxy(payload)
    return _start_production_legacy(payload, db)


# -----------------------------------------------------------------------------
# RA cur_stat 진행 (Confluence 32342045 open inline comment 대응)
# -----------------------------------------------------------------------------


@router.post("/equip-tasks/{txn_id}/advance")
def advance_equip_task(txn_id: int, db: Session = Depends(get_db)) -> dict:
    """equip_task_txn 의 다음 cur_stat 으로 진행 + equip_stat 레코드 INSERT.

    task_type 별 하드코딩 시퀀스는 backend/app/constants/ra_task_stat.py 참조.
    RA: MV_SRC → GRASP → MV_DEST → RELEASE → RETURN → IDLE
    POUR 은 POURING 단계 삽입.
    CONV: ON / OFF / ERR.

    시퀀스 종료 시 (IDLE 반환) txn_stat 을 SUCC 로 자동 전환.
    Gap 1 (2026-04-27): IDLE 도달 후 후속 task (POUR/DM/ToPP) 자동 생성.
    """
    from app.constants import next_state  # local import to keep top lean

    # Race 방지: 동일 txn 에 대한 동시 advance 를 직렬화
    txn = db.query(EquipTaskTxn).filter(EquipTaskTxn.txn_id == txn_id).with_for_update().first()
    if not txn:
        raise HTTPException(404, f"equip_task_txn={txn_id} not found")
    if txn.txn_stat in ("SUCC", "FAIL"):
        raise HTTPException(400, f"equip_task_txn={txn_id} already {txn.txn_stat}")
    if not txn.res_id:
        raise HTTPException(400, "res_id not assigned yet; cannot advance")

    # 최신 cur_stat 조회
    latest = (
        db.query(EquipStat)
        .filter(
            EquipStat.res_id == txn.res_id,
            EquipStat.item_id == txn.item_id,
            EquipStat.txn_type == txn.task_type,
        )
        .order_by(desc(EquipStat.updated_at))
        .first()
    )
    cur = latest.cur_stat if latest else None
    nxt = next_state(txn.task_type or "", cur)
    if nxt is None:
        raise HTTPException(400, f"no sequence defined for task_type={txn.task_type!r}")

    # equip_stat INSERT
    new_stat = EquipStat(
        res_id=txn.res_id,
        item_id=txn.item_id,
        txn_type=txn.task_type,
        cur_stat=nxt,
    )
    db.add(new_stat)

    item: Item | None = None
    item_stat = None
    if txn.item_id:
        item = db.get(Item, txn.item_id)
        if item:
            item.cur_stat = txn.task_type
            item.cur_res = txn.res_id
            item.equip_task_type = txn.task_type
            item.updated_at = datetime.utcnow()
            item_stat = item.cur_stat

    if txn.txn_stat == "QUE":
        txn.txn_stat = "PROC"
        txn.start_at = txn.start_at or datetime.utcnow()

    # IDLE 도달 시 txn 완료 처리 + Gap 1: 후속 task 자동 생성
    auto_meta: dict[str, Any] = {}
    if nxt == "IDLE" and txn.txn_stat not in ("SUCC", "FAIL"):
        txn.txn_stat = "SUCC"
        txn.end_at = datetime.utcnow()
        auto_meta = _auto_progress_after_idle(db, txn=txn, item=item)
        # item.cur_stat 가 helper 안에서 갱신됐을 수 있음 → 응답용 stat 동기화
        if item is not None:
            item_stat = item.cur_stat

    db.commit()
    db.refresh(new_stat)
    return {
        "txn_id": txn_id,
        "res_id": txn.res_id,
        "task_type": txn.task_type,
        "prev_stat": cur,
        "new_stat": nxt,
        "item_id": txn.item_id,
        "item_cur_stat": item_stat,
        "txn_stat": txn.txn_stat,
        "auto": auto_meta,  # Gap 1: 자동 생성된 후속 task 정보
    }
