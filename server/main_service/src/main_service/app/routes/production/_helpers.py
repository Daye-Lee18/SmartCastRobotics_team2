"""production sub-routes 공통 헬퍼.

이 모듈은 endpoint 를 정의하지 않는다. 다른 sub-route 들이 import 해서 사용.

주요 export:
    - _PROXY_START_PRODUCTION (feature flag, 모듈 import 시점 고정)
    - _EQUIP_CHAIN, _TRANS_AFTER_EQUIP (자동 진행 매핑)
    - _pick_idle_amr, _spawn_next_equip, _spawn_trans_topp, _auto_progress_after_idle
    - _parse_ord_id, _latest_ord_stat
    - _virtual_production_job, _priority_result
    - ScheduleOrderIdsIn, PriorityLogIn (Pydantic models)

2026-04-27: backend/app/routes/production.py (821 LOC) 분할 산출.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import (
    EquipTaskTxn,
    Item,
    Ord,
    OrdStat,
    Pattern,
    Trans,
    TransStat,
    TransTaskTxn,
)

logger = logging.getLogger("app.production")


# -----------------------------------------------------------------------------
# Feature flag — INTERFACE_PROXY_START_PRODUCTION
# -----------------------------------------------------------------------------
# SPEC-C2 §11.2: 모듈 import 시점에 상수로 고정.
# Flip 하려면 모든 uvicorn worker 재시작 필수 (per-request env read 금지 — worker race 방지).
_PROXY_START_PRODUCTION = os.environ.get("INTERFACE_PROXY_START_PRODUCTION", "0") in (
    "1",
    "true",
    "True",
    "yes",
)
logger.info(
    "[INTERFACE-PROXY] start_production proxy = %s (flag pinned at module import)",
    "ON" if _PROXY_START_PRODUCTION else "OFF (legacy DB-direct)",
)


# -----------------------------------------------------------------------------
# Auto-progression mapping (Gap 1, 2026-04-27)
# -----------------------------------------------------------------------------
# advance_equip_task 가 IDLE 도달 시 RA_NEXT_TASK 체인을 따라 다음 작업을
# 자동 생성한다. 실제 ESP32/AMR 연동 후에도 같은 endpoint 가 호출되면
# 후속 단계가 끊기지 않고 진행되도록 한다.
#
#   MM   → POUR   (equip_task_txn, 동일 RA, QUE)
#   POUR → DM     (equip_task_txn, 동일 RA, QUE)
#   DM   → ToPP   (trans_task_txn, 가용 AMR, PROC + trans_stat WAIT_HANDOFF)
_EQUIP_CHAIN: dict[str, str] = {
    "MM": "POUR",
    "POUR": "DM",
}
_TRANS_AFTER_EQUIP: dict[str, str] = {
    "DM": "ToPP",
}


def _pick_idle_amr(db: Session) -> str | None:
    """가용 AMR 1대 선택. trans_stat 미등록 또는 cur_stat IN ('IDLE','WAIT_DLD',NULL).

    동시 advance 호출 race 방지를 위해 row-level lock + skip_locked 사용.
    Postgres FOR UPDATE SKIP LOCKED 가 동시 트랜잭션의 동일 row 조회를 차단한다.
    """
    used_busy = (
        db.query(TransStat.res_id)
        .filter(TransStat.cur_stat.notin_(["IDLE", "WAIT_DLD", None]))
        .subquery()
    )
    cand = (
        db.query(Trans.res_id)
        .filter(Trans.res_id.notin_(used_busy))
        .order_by(Trans.res_id)
        .with_for_update(skip_locked=True)
        .first()
    )
    return cand[0] if cand else None


def _spawn_next_equip(db: Session, *, item: Item, prev_res_id: str, next_type: str) -> EquipTaskTxn:
    """동일 RA 에서 다음 equip_task_txn 생성 (QUE).

    EquipTaskTxn 스키마에는 ord_id 컬럼이 없음 (item_id 만으로 ord 추적).
    """
    new_txn = EquipTaskTxn(
        item_id=item.item_id,
        res_id=prev_res_id,
        task_type=next_type,
        txn_stat="QUE",
    )
    db.add(new_txn)
    db.flush()
    item.equip_task_type = next_type
    item.cur_stat = "QUE"
    item.cur_res = prev_res_id
    item.updated_at = datetime.utcnow()
    return new_txn


def _spawn_trans_topp(db: Session, *, item: Item) -> TransTaskTxn | None:
    """DM IDLE → ToPP 트랜스포트 작업 + AMR WAIT_HANDOFF 상태 직접 진입.

    AMR 가용성이 없으면 None 반환 (실제 운영에서는 큐 대기, 데모에서는 fail-fast).
    """
    amr_id = _pick_idle_amr(db)
    if not amr_id:
        logger.warning("[GAP1] no idle AMR; skipping ToPP creation for item_id=%s", item.item_id)
        return None
    if item.ord_id is None:
        logger.warning("[GAP1] item_id=%s has NULL ord_id; skipping ToPP", item.item_id)
        return None

    now = datetime.utcnow()
    ttxn = TransTaskTxn(
        trans_id=amr_id,
        task_type="ToPP",
        txn_stat="PROC",
        item_id=item.item_id,
        ord_id=item.ord_id,
        start_at=now,
    )
    db.add(ttxn)
    db.flush()

    # trans_stat: AMR 을 WAIT_HANDOFF 상태로. (실제 환경에서는 fms_sequencer 가
    # MV_SRC → MV_DEST 경유 후 WAIT_HANDOFF 로 가지만, 데모 단축 경로.)
    stat = db.get(TransStat, amr_id)
    if stat is None:
        stat = TransStat(
            res_id=amr_id,
            item_id=item.item_id,
            cur_stat="WAIT_HANDOFF",
            battery_pct=85,
        )
        db.add(stat)
    else:
        stat.cur_stat = "WAIT_HANDOFF"
        stat.item_id = item.item_id
        stat.updated_at = now

    item.cur_stat = "ToPP"
    item.trans_task_type = "ToPP"
    item.equip_task_type = None
    item.cur_res = amr_id
    item.updated_at = now
    return ttxn


def _auto_progress_after_idle(
    db: Session, *, txn: EquipTaskTxn, item: Item | None
) -> dict[str, Any]:
    """advance_equip_task IDLE 도달 후 후속 task 자동 생성. 메타 dict 반환."""
    meta: dict[str, Any] = {"next_equip_txn_id": None, "next_trans_txn_id": None, "amr_id": None}
    if item is None or not txn.task_type:
        return meta

    if txn.task_type in _EQUIP_CHAIN:
        nxt_type = _EQUIP_CHAIN[txn.task_type]
        new_txn = _spawn_next_equip(db, item=item, prev_res_id=txn.res_id, next_type=nxt_type)
        meta["next_equip_txn_id"] = new_txn.txn_id
        logger.info(
            "[GAP1] %s SUCC → equip_task_txn(%s) QUE @ %s, item_id=%s",
            txn.task_type,
            nxt_type,
            txn.res_id,
            item.item_id,
        )
    elif txn.task_type in _TRANS_AFTER_EQUIP:
        ttxn = _spawn_trans_topp(db, item=item)
        if ttxn is not None:
            meta["next_trans_txn_id"] = ttxn.trans_task_txn_id
            meta["amr_id"] = ttxn.trans_id
            logger.info(
                "[GAP1] %s SUCC → trans_task_txn(ToPP) PROC @ %s, item_id=%s",
                txn.task_type,
                ttxn.trans_id,
                item.item_id,
            )
    return meta


# -----------------------------------------------------------------------------
# Schedule helpers (priority/queue)
# -----------------------------------------------------------------------------
class ScheduleOrderIdsIn(BaseModel):
    order_ids: list[str] = []


class PriorityLogIn(BaseModel):
    order_id: str
    old_rank: int = 0
    new_rank: int = 0
    reason: str = ""


def _parse_ord_id(raw: str | int) -> int:
    text = str(raw).strip()
    if text.startswith("ord_"):
        text = text[4:]
    try:
        value = int(text)
    except ValueError as exc:
        raise HTTPException(400, f"invalid order_id: {raw}") from exc
    if value <= 0:
        raise HTTPException(400, f"invalid order_id: {raw}")
    return value


def _latest_ord_stat(db: Session, ord_id: int) -> str:
    latest = (
        db.query(OrdStat)
        .filter(OrdStat.ord_id == ord_id)
        .order_by(desc(OrdStat.updated_at))
        .first()
    )
    return latest.ord_stat if latest else "RCVD"


def _virtual_production_job(db: Session, ord_obj: Ord, rank: int = 1) -> dict[str, Any]:
    latest = _latest_ord_stat(db, ord_obj.ord_id)
    detail = ord_obj.detail
    qty = int(detail.qty or 0) if detail else 0
    est_days = 3 + (qty // 50)
    created_at = (
        ord_obj.created_at.isoformat() if ord_obj.created_at else datetime.utcnow().isoformat()
    )
    estimated_completion = None
    due_date = getattr(detail, "due_date", None) if detail else None
    if due_date:
        estimated_completion = due_date.isoformat()
    else:
        estimated_completion = (datetime.utcnow() + timedelta(days=est_days)).isoformat()
    return {
        "id": f"PJ-ORD-{ord_obj.ord_id}",
        "order_id": str(ord_obj.ord_id),
        "priority_score": 0.0,
        "priority_rank": rank,
        "assigned_stage": "production-planning",
        "status": "queued" if latest in {"APPR", "MFG"} else "completed",
        "estimated_completion": estimated_completion,
        "started_at": created_at if latest == "MFG" else None,
        "completed_at": None,
        "created_at": created_at,
    }


def _priority_result(db: Session, ord_obj: Ord, rank: int = 1) -> dict[str, Any]:
    detail = ord_obj.detail
    user = ord_obj.user
    qty = int(detail.qty or 0) if detail else 0
    due_date = getattr(detail, "due_date", None) if detail else None
    days_left = 999
    if due_date:
        days_left = (due_date - datetime.utcnow().date()).days

    delivery_score = (
        25.0 if days_left <= 3 else 20.0 if days_left <= 7 else 15.0 if days_left <= 14 else 10.0
    )
    age_days = (
        (datetime.utcnow() - ord_obj.created_at.replace(tzinfo=None)).days
        if ord_obj.created_at
        else 0
    )
    age_score = min(15.0, 5.0 + age_days * 2.0)
    qty_score = min(10.0, max(3.0, qty / 5.0))
    amount = float(detail.final_price or 0) if detail else 0.0
    customer_score = 10.0 if amount >= 1_000_000 else 7.0 if amount >= 500_000 else 5.0
    delay_score = 15.0 if days_left <= 7 else 10.0 if days_left <= 14 else 7.0
    setup_score = 5.0
    has_pattern = db.get(Pattern, ord_obj.ord_id) is not None
    ready_score = 20.0 if has_pattern else 8.0
    blocking = (
        []
        if has_pattern
        else ["패턴 위치 미등록: 운영관리 페이지에서 패턴 등록 후 실제 생산 시작 가능"]
    )

    factors = [
        {
            "name": "납기일 긴급도",
            "score": delivery_score,
            "max_score": 25.0,
            "detail": f"납기 D-{days_left}" if due_date else "납기 미지정",
        },
        {
            "name": "착수 가능 여부",
            "score": ready_score,
            "max_score": 20.0,
            "detail": "패턴 등록 완료" if has_pattern else "패턴 미등록",
        },
        {
            "name": "주문 체류 시간",
            "score": age_score,
            "max_score": 15.0,
            "detail": f"접수 후 {age_days}일",
        },
        {
            "name": "지연 위험도",
            "score": delay_score,
            "max_score": 15.0,
            "detail": "납기 기반 위험도",
        },
        {
            "name": "고객 중요도",
            "score": customer_score,
            "max_score": 10.0,
            "detail": f"주문 금액 {amount:,.0f}",
        },
        {"name": "수량 효율", "score": qty_score, "max_score": 10.0, "detail": f"수량 {qty}"},
        {
            "name": "세팅 변경 비용",
            "score": setup_score,
            "max_score": 5.0,
            "detail": "동일 라인 기본 배정",
        },
    ]
    total_score = round(sum(float(f["score"]) for f in factors), 1)
    delay_risk = "high" if days_left <= 3 else "medium" if days_left <= 7 else "low"
    product_summary = "주물 제품"
    if detail:
        product_summary = (
            " / ".join(str(v) for v in (detail.material, detail.load_class) if v) or product_summary
        )
    return {
        "order_id": str(ord_obj.ord_id),
        "company_name": user.co_nm if user else "-",
        "product_summary": product_summary,
        "total_quantity": qty,
        "requested_delivery": due_date.isoformat() if due_date else None,
        "total_score": total_score,
        "rank": rank,
        "factors": factors,
        "recommendation_reason": f"납기/수량/금액 기준 점수 {total_score:.1f}.",
        "delay_risk": delay_risk,
        "ready_status": "ready" if has_pattern else "not_ready",
        "blocking_reasons": blocking,
        "estimated_days": 3 + (qty // 50),
    }
