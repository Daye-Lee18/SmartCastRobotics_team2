from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from smart_cast_db.models import (
    EquipTaskTxn,
    ItemStat,
    Ord,
    OrdStat,
    Pattern,
)

logger = logging.getLogger("app.production")

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


def _is_schedule_queue_candidate(db: Session, ord_id: int) -> bool:
    """생산 계획 큐 후보 여부.

    기준:
    - 주문 상태는 MFG 여야 함
    - 아직 실제 라인 투입 흔적(item_stat / equip_task_txn)이 없어야 함
    """
    if _latest_ord_stat(db, ord_id) != "MFG":
        return False

    has_item = (
        db.query(ItemStat.item_stat_id)
        .filter(ItemStat.ord_id == ord_id)
        .first()
        is not None
    )
    if has_item:
        return False

    has_equip_txn = (
        db.query(EquipTaskTxn.txn_id)
        .filter(EquipTaskTxn.ord_id == ord_id)
        .first()
        is not None
    )
    return not has_equip_txn


def _virtual_production_job(db: Session, ord_obj: Ord, rank: int = 1) -> dict[str, Any]:
    latest = _latest_ord_stat(db, ord_obj.ord_id)
    detail = ord_obj.detail
    user = ord_obj.user
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
        "started_at": None,
        "completed_at": None,
        "created_at": created_at,
        "company_name": user.co_nm if user else "-",
        "customer_name": user.user_nm if user else "-",
        "total_amount": float(detail.final_price or 0) if detail else 0.0,
        "requested_delivery": due_date.isoformat() if due_date else None,
        "confirmed_delivery": due_date.isoformat() if due_date else None,
        "order_status": "in_production" if latest == "MFG" else "approved",
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
        # v21 ord_detail 에는 material/load_class 가 없다.
        # product relation 또는 prod_id 기준으로만 안전하게 요약한다.
        product = getattr(detail, "product", None)
        parts = [
            getattr(product, "cate_cd", None) if product is not None else None,
            f"prod:{detail.prod_id}" if getattr(detail, "prod_id", None) is not None else None,
        ]
        product_summary = " / ".join(str(v) for v in parts if v) or product_summary
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
