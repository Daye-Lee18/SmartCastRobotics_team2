"""Pydantic v2 스키마 — smartcast schema (Confluence 32342045 v59 기준).

신규 27 테이블에 대응하는 Request/Response 모델.
Legacy 모델은 backend/app/schemas/schemas_legacy.py 에 보관.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# =====================
# Common
# =====================


class _ORM(BaseModel):
    """ORM mode 베이스. protected_namespaces=() 로 `model_nm` 필드 경고 무시."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# =====================
# USER
# =====================


class UserAccountBase(BaseModel):
    co_nm: str
    user_nm: str
    role: str | None = None
    phone: str | None = None
    email: str  # EmailStr 는 외부 dep 부담, str 로 가볍게


class UserAccountCreate(UserAccountBase):
    password: str | None = None


class UserAccountOut(_ORM, UserAccountBase):
    user_id: int


# =====================
# CATEGORY / PRODUCT
# =====================


class CategoryOut(_ORM):
    cate_cd: str
    cate_nm: str


class ProductOut(_ORM):
    prod_id: int
    cate_cd: str
    base_price: Decimal
    img_url: str | None = None


class ProductOptionOut(_ORM):
    prod_opt_id: int
    prod_id: int
    mat_type: str | None = None
    load_class: str | None = None


class PpOptionOut(_ORM):
    pp_id: int
    pp_nm: str | None = None
    extra_cost: Decimal | None = None


# =====================
# ORDER
# =====================


class OrdDetailIn(BaseModel):
    prod_id: int | None = None
    diameter: Decimal | None = None
    thickness: Decimal | None = None
    material: str | None = None
    load_class: str | None = None
    qty: int | None = None
    final_price: Decimal | None = None
    due_date: date | None = None
    ship_addr: str | None = None


class OrdDetailOut(_ORM, OrdDetailIn):
    ord_id: int


class OrdCreate(BaseModel):
    """발주 생성 — 고객 측 발주 폼 (비고란 없음, 핑크 GUI #2)."""

    user_id: int
    detail: OrdDetailIn
    pp_ids: list[int] = Field(default_factory=list)


class OrdOut(_ORM):
    ord_id: int
    user_id: int
    created_at: datetime | None = None


class OrdStatOut(_ORM):
    stat_id: int
    ord_id: int
    user_id: int | None = None
    ord_stat: str | None = None
    updated_at: datetime | None = None


class OrdFull(OrdOut):
    """발주 + 상세 + 후처리 + 최신 상태 + 상태 트레일 — 고객 조회용.

    user_* 필드는 user_account 에서 denormalize. Next.js/PyQt 가 발주 카드에
    회사명/담당자/연락처/이메일/주소를 바로 표시할 수 있게 한다.

    stats: ord_stat 변경 이력 (시간 오름차순). RCVD→APPR→MFG→…→COMP 트레일.
    """

    detail: OrdDetailOut | None = None
    pp_options: list[PpOptionOut] = Field(default_factory=list)
    latest_stat: str | None = None
    stats: list[OrdStatOut] = Field(default_factory=list)

    # user_account denormalize (고객 조회·관리자 리스트에서 즉시 표시용)
    user_co_nm: str | None = None
    user_nm: str | None = None
    user_phone: str | None = None
    user_email: str | None = None


class OrdTxnOut(_ORM):
    txn_id: int
    ord_id: int
    txn_type: str | None = None
    txn_at: datetime | None = None


# =====================
# ZONE / RES / EQUIP / TRANS
# =====================


class ZoneOut(_ORM):
    zone_id: int
    zone_nm: str | None = None


class ResOut(_ORM):
    res_id: str
    res_type: str | None = None
    model_nm: str


class EquipOut(_ORM):
    res_id: str
    zone_id: int | None = None


class TransOut(_ORM):
    res_id: str
    slot_count: int | None = None
    max_load_kg: Decimal | None = None


# =====================
# PATTERN (핑크 GUI #3)
# =====================


class PatternIn(BaseModel):
    """패턴 등록 — 발주 1:1, 위치 1-6."""

    ptn_id: int  # = ord_id
    ptn_loc: int = Field(ge=1, le=6)


class PatternOut(_ORM):
    ptn_id: int
    ptn_loc: int


# =====================
# ITEM
# =====================


class ItemOut(_ORM):
    item_id: int
    ord_id: int
    equip_task_type: str | None = None
    trans_task_type: str | None = None
    cur_stat: str | None = None
    cur_res: str | None = None
    is_defective: bool | None = None
    updated_at: datetime | None = None


# =====================
# TASK / STAT — equip / trans / pp / insp
# =====================


class EquipTaskTxnOut(_ORM):
    txn_id: int
    res_id: str | None = None
    task_type: str | None = None
    txn_stat: str | None = None
    item_id: int | None = None
    strg_loc_id: int | None = None
    ship_loc_id: int | None = None
    req_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class EquipStatOut(_ORM):
    stat_id: int
    res_id: str
    item_id: int | None = None
    txn_type: str | None = None
    cur_stat: str | None = None
    updated_at: datetime | None = None
    err_msg: str | None = None


class TransTaskTxnOut(_ORM):
    trans_task_txn_id: int
    trans_id: str | None = None
    task_type: str | None = None
    txn_stat: str | None = None
    chg_loc_id: int | None = None
    item_id: int | None = None
    ord_id: int | None = None
    req_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class TransStatOut(_ORM):
    res_id: str
    item_id: int | None = None
    cur_stat: str | None = None
    battery_pct: int | None = None
    cur_zone_type: str | None = None
    updated_at: datetime | None = None


class PpTaskTxnOut(_ORM):
    txn_id: int
    ord_id: int
    map_id: int | None = None
    pp_nm: str | None = None
    item_id: int | None = None
    operator_id: int | None = None
    txn_stat: str | None = None
    req_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class InspTaskTxnOut(_ORM):
    txn_id: int
    item_id: int | None = None
    res_id: str | None = None
    txn_stat: str | None = None
    result: bool | None = None
    req_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


# =====================
# 핑크 GUI #6 — Inspection summary per ord
# =====================


class InspectionSummary(BaseModel):
    """발주별 검사 요약 — 핑크 GUI #6 (PyQt 양품/불량 페이지)."""

    ord_id: int
    total_items: int
    inspected: int
    good_count: int  # GP
    defective_count: int  # DP
    pending_count: int  # 미검사


# =====================
# 핑크 GUI #4 — PP requirements per item
# =====================


class ItemPpRequirements(BaseModel):
    """item별 필요 후처리 목록 — 핑크 GUI #4."""

    item_id: int
    ord_id: int
    pp_options: list[PpOptionOut] = Field(default_factory=list)
    pp_task_status: list[PpTaskTxnOut] = Field(default_factory=list)


# =====================
# 핑크 GUI #5 — 생산 시작 요청
# =====================


class ProductionStartRequest(BaseModel):
    """발주 생산 시작 — 패턴 등록 후에만 호출 가능."""

    ord_id: int


# =====================
# Customer 폼 (이메일 기반, user_id 자동 upsert)
# =====================


class CustomerOrderDetailIn(BaseModel):
    """customer 발주 폼의 단일 detail."""

    product_id: str | None = None
    product_name: str | None = None
    quantity: int
    diameter: str | None = None  # 폼 select 값 (e.g. "600mm")
    thickness: str | None = None
    load_class: str | None = None
    material: str | None = None
    post_processing_ids: list[str] = Field(default_factory=list)  # ["polish","coat",...]
    unit_price: float
    subtotal: float


class CustomerOrderCreate(BaseModel):
    """customer 발주 폼 → 신규 schema upsert 전용 entry point."""

    company_name: str
    customer_name: str
    phone: str | None = None
    email: str
    shipping_address: str | None = None
    total_amount: float
    requested_delivery: str | None = None  # "2026-05-31" 형식
    details: list[CustomerOrderDetailIn]


class CustomerOrderResponse(BaseModel):
    """customer 발주 생성 응답."""

    ord_id: int
    id: str  # legacy 호환 "ord_{n}" 형태
    user_id: int
    created_at: datetime | None = None
    message: str
