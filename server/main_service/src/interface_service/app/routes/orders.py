"""Orders router — smartcast schema.

엔드포인트:
  POST   /api/orders                    발주 생성 (ord + ord_detail + ord_pp_map + RCVD txn/stat)
  GET    /api/orders                    발주 목록 (관리자 조회)
  GET    /api/orders/{ord_id}           발주 단건 (detail + pp_options + latest_stat)
  GET    /api/orders/lookup?email=...   고객 발주 조회 (핑크 GUI #1)
  POST   /api/orders/{ord_id}/status    발주 상태 전이 (RCVD→APPR→...)

  GET    /api/products                  표준 제품 목록 (카테고리/옵션 join)
  GET    /api/categories                카테고리 마스터
  GET    /api/pp-options                후처리 마스터
  GET    /api/equip-load-spec           하중 등급별 정밀 제어 수치 (legacy load_classes 대체)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from smart_cast_db.database import get_db
from smart_cast_db.models import (
    Category,
    EquipLoadSpec,
    Ord,
    OrdDetail,
    OrdLog,
    OrdPattern,
    OrdPpMap,
    OrdStat,
    OrdTxn,
    PpOption,
    Product,
    UserAccount,
)
from app.schemas.schemas import (
    CategoryOut,
    CustomerOrderCreate,
    CustomerOrderResponse,
    OrdCreate,
    OrdFull,
    OrdStatOut,
    PpOptionOut,
    ProductOut,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])
products_router = APIRouter(prefix="/api", tags=["products"])
load_classes_router = APIRouter(prefix="/api", tags=["load-classes"])


# -------------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------------


def _to_full(db: Session, ord_obj: Ord) -> OrdFull:
    """Ord ORM → OrdFull (detail + pp_options + latest_stat + user denormalized)."""
    pp_options = (
        db.query(PpOption)
        .join(OrdPpMap, OrdPpMap.pp_id == PpOption.pp_id)
        .filter(OrdPpMap.ord_id == ord_obj.ord_id)
        .all()
    )
    # ord_obj.stats 가 selectinload 로 미리 로드되었으면 추가 쿼리 없음.
    # 직접 호출(get_order)은 lazy load.
    stats_rows = sorted(ord_obj.stats or [], key=lambda s: s.stat_id)
    latest_stat = stats_rows[-1] if stats_rows else None
    user = db.get(UserAccount, ord_obj.user_id)
    return OrdFull(
        ord_id=ord_obj.ord_id,
        user_id=ord_obj.user_id,
        created_at=ord_obj.created_at,
        detail=ord_obj.detail,
        pp_options=[PpOptionOut.model_validate(p) for p in pp_options],
        latest_stat=latest_stat.ord_stat if latest_stat else "RCVD",
        stats=[OrdStatOut.model_validate(s) for s in stats_rows],
        user_co_nm=user.co_nm if user else None,
        user_nm=user.user_nm if user else None,
        user_phone=user.phone if user else None,
        user_email=user.email if user else None,
    )


def _resolve_product_id(db: Session, raw_product_id: str | None) -> int | None:
    """Best-effort frontend product id -> v21 product.prod_id."""
    if not raw_product_id:
        return None

    text = raw_product_id.strip()
    if text.isdigit():
        candidate = int(text)
        return candidate if db.get(Product, candidate) is not None else None

    prefix = text[:1].upper()
    cate_cd = {"R": "CMH", "S": "RMH", "O": "EMH"}.get(prefix)
    if cate_cd is None:
        return None

    row = db.query(Product).filter(Product.cate_cd == cate_cd).order_by(Product.prod_id.asc()).first()
    return row.prod_id if row is not None else None


def _parse_decimal_or_none(raw_value: str | int | float | Decimal | None) -> Decimal | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, Decimal):
        return raw_value
    text = str(raw_value).strip()
    if not text:
        return None
    filtered = "".join(ch for ch in text if ch.isdigit() or ch in {".", "-"})
    if not filtered or filtered in {".", "-", "-."}:
        return None
    try:
        return Decimal(filtered)
    except InvalidOperation:
        return None


def _pattern_id_from_prefix(prefix: str | None) -> int | None:
    if not prefix:
        return None
    return {"R": 1, "S": 2, "O": 3}.get(prefix[:1].upper())


def _resolve_pattern_id(
    db: Session,
    *,
    raw_product_id: str | None = None,
    prod_id: int | None = None,
) -> int | None:
    pattern_id = _pattern_id_from_prefix((raw_product_id or "").strip())
    if pattern_id is not None:
        return pattern_id
    if prod_id is None:
        return None
    product = db.get(Product, prod_id)
    if product is None:
        return None
    return {"CMH": 1, "RMH": 2, "EMH": 3}.get(product.cate_cd)


def _parse_due_date_or_400(raw_due_date: str | None) -> date:
    if not raw_due_date:
        raise HTTPException(400, "requested_delivery is required")
    try:
        return date.fromisoformat(raw_due_date[:10])
    except ValueError as exc:
        raise HTTPException(400, f"invalid requested_delivery: {raw_due_date}") from exc


def _require_ship_addr_or_400(raw_ship_addr: str | None) -> str:
    ship_addr = (raw_ship_addr or "").strip()
    if not ship_addr:
        raise HTTPException(400, "shipping_address is required")
    return ship_addr


def _normalize_ord_status(raw_status: str) -> str:
    status = (raw_status or "").strip().upper()
    if status == "SHIP":
        return "SHIPPING"
    return status


def _append_ord_log(
    db: Session,
    *,
    ord_id: int,
    prev_stat: str | None,
    new_stat: str,
    changed_by: int | None,
) -> None:
    db.add(
        OrdLog(
            ord_id=ord_id,
            prev_stat=prev_stat,
            new_stat=new_stat,
            changed_by=changed_by,
        )
    )


def _append_ord_txn_if_supported(db: Session, *, ord_id: int, new_stat: str) -> None:
    txn_type = {
        "RCVD": "RCVD",
        "APPR": "APPR",
        "REJT": "REJT",
        "CNCL": "CNCL",
    }.get(new_stat)
    if txn_type is not None:
        db.add(OrdTxn(ord_id=ord_id, txn_type=txn_type))


# -------------------------------------------------------------------------
# Order CRUD
# -------------------------------------------------------------------------


@router.post("", response_model=OrdFull, status_code=201)
def create_order(payload: OrdCreate, db: Session = Depends(get_db)) -> OrdFull:
    """발주 생성 — 고객 측 폼.

    Pink GUI #2: 비고란 제거됨 (OrdDetailIn 에 비고 필드 없음).
    """
    user = db.get(UserAccount, payload.user_id)
    if not user:
        raise HTTPException(404, f"user_id={payload.user_id} not found")

    new_ord = Ord(user_id=payload.user_id)
    db.add(new_ord)
    db.flush()  # ord_id 확보

    detail = OrdDetail(
        ord_id=new_ord.ord_id,
        prod_id=payload.detail.prod_id,
        diameter=payload.detail.diameter,
        thickness=payload.detail.thickness,
        material=payload.detail.material,
        load_class=payload.detail.load_class,
        qty=payload.detail.qty,
        final_price=payload.detail.final_price,
        due_date=payload.detail.due_date,
        ship_addr=payload.detail.ship_addr,
    )
    db.add(detail)

    pattern_id = _resolve_pattern_id(db, prod_id=payload.detail.prod_id)
    if pattern_id is not None:
        db.add(OrdPattern(ord_id=new_ord.ord_id, ptn_id=pattern_id))

    for pp_id in payload.pp_ids:
        db.add(OrdPpMap(ord_id=new_ord.ord_id, pp_id=pp_id))

    # 초기 상태 RCVD (txn + stat 동시 INSERT)
    db.add(OrdTxn(ord_id=new_ord.ord_id, txn_type="RCVD"))
    db.add(OrdStat(ord_id=new_ord.ord_id, user_id=payload.user_id, ord_stat="RCVD"))
    _append_ord_log(
        db,
        ord_id=new_ord.ord_id,
        prev_stat=None,
        new_stat="RCVD",
        changed_by=payload.user_id,
    )
    db.commit()
    db.refresh(new_ord)
    return _to_full(db, new_ord)


@router.get("", response_model=list[OrdFull])
def list_orders(db: Session = Depends(get_db)) -> list[OrdFull]:
    """발주 목록 — 관리자용. 일괄 조회로 N+1 제거."""
    rows = (
        db.query(Ord)
        .options(selectinload(Ord.detail), selectinload(Ord.stats))
        .order_by(desc(Ord.created_at))
        .all()
    )
    if not rows:
        return []

    ord_ids = [o.ord_id for o in rows]
    user_ids = list({o.user_id for o in rows if o.user_id})

    # pp_options 일괄 조회 (per-order 쿼리 제거)
    pp_maps = (
        db.query(OrdPpMap, PpOption)
        .join(PpOption, PpOption.pp_id == OrdPpMap.pp_id)
        .filter(OrdPpMap.ord_id.in_(ord_ids))
        .all()
    )
    pp_by_ord: dict[int, list[PpOption]] = {}
    for mapping, opt in pp_maps:
        pp_by_ord.setdefault(mapping.ord_id, []).append(opt)

    # user 일괄 조회 (per-order 쿼리 제거)
    users = db.query(UserAccount).filter(UserAccount.user_id.in_(user_ids)).all()
    user_by_id = {u.user_id: u for u in users}

    result: list[OrdFull] = []
    for o in rows:
        stats_rows = sorted(o.stats or [], key=lambda s: s.stat_id)
        latest_stat = stats_rows[-1] if stats_rows else None
        user = user_by_id.get(o.user_id)
        result.append(OrdFull(
            ord_id=o.ord_id,
            user_id=o.user_id,
            created_at=o.created_at,
            detail=o.detail,
            pp_options=[PpOptionOut.model_validate(p) for p in pp_by_ord.get(o.ord_id, [])],
            latest_stat=latest_stat.ord_stat if latest_stat else "RCVD",
            stats=[OrdStatOut.model_validate(s) for s in stats_rows],
            user_co_nm=user.co_nm if user else None,
            user_nm=user.user_nm if user else None,
            user_phone=user.phone if user else None,
            user_email=user.email if user else None,
        ))
    return result


# -------------------------------------------------------------------------
# Customer 폼 전용 — 이메일로 user upsert + ord 생성 한방 처리
# -------------------------------------------------------------------------

# 폼의 post-processing id 와 pp_options.pp_nm 매핑 (id 가 영문 코드, DB 는 한글명)
_PP_ID_TO_NM: dict[str, str] = {
    "polish": "표면 연마",
    "rustProof": "방청 코팅",
    "zinc": "아연 도금",
    "logo": "로고/문구 삽입",
}


@router.post("/customer", response_model=CustomerOrderResponse, status_code=201)
def create_customer_order(
    payload: CustomerOrderCreate, db: Session = Depends(get_db)
) -> CustomerOrderResponse:
    """고객 폼 전용 발주 생성. 이메일로 user_account upsert + ord/detail/pp_map/stat/txn 한방 INSERT.

    Pink GUI #2 만족 — 비고/notes 필드 없음.
    """
    # 1. user_account upsert (email 기준)
    user = db.query(UserAccount).filter(UserAccount.email == payload.email).first()
    if user is None:
        user = UserAccount(
            co_nm=payload.company_name,
            user_nm=payload.customer_name,
            role="customer",
            phone=payload.phone,
            email=payload.email,
            password="__customer_placeholder__",
        )
        db.add(user)
        db.flush()
    else:
        # 기존 사용자 정보 갱신 (회사명/담당자명/연락처 변경 가능)
        user.co_nm = payload.company_name
        user.user_nm = payload.customer_name
        if payload.phone:
            user.phone = payload.phone

    # 2. ord 생성
    new_ord = Ord(user_id=user.user_id)
    db.add(new_ord)
    db.flush()

    # 3. ord_detail (1:1) — 폼 1 detail 만 사용 (현 폼 구조)
    if not payload.details:
        raise HTTPException(400, "details 가 비어있습니다.")
    d0 = payload.details[0]

    due_date = _parse_due_date_or_400(payload.requested_delivery)
    ship_addr = _require_ship_addr_or_400(payload.shipping_address)
    safe_prod_id = _resolve_product_id(db, d0.product_id)

    detail = OrdDetail(
        ord_id=new_ord.ord_id,
        prod_id=safe_prod_id,
        diameter=_parse_decimal_or_none(d0.diameter),
        thickness=_parse_decimal_or_none(d0.thickness),
        material=d0.material,
        load_class=d0.load_class,
        qty=d0.quantity,
        final_price=payload.total_amount,
        due_date=due_date,
        ship_addr=ship_addr,
    )
    db.add(detail)

    # 4. ord_pp_map (post_processing_ids → pp_id)
    for pp_id_code in d0.post_processing_ids:
        pp_nm = _PP_ID_TO_NM.get(pp_id_code)
        if pp_nm is None:
            continue
        pp = db.query(PpOption).filter(PpOption.pp_nm == pp_nm).first()
        if pp:
            db.add(OrdPpMap(ord_id=new_ord.ord_id, pp_id=pp.pp_id))

    # 5. 자동 패턴 등록 — 제품 형상 기준으로 pattern_master(1~3) 매핑.
    # 매핑 실패 시 row 생성 안 함 → 생산 시작 전 운영자가 패턴을 보완 등록해야 한다.
    pattern_id = _resolve_pattern_id(db, raw_product_id=d0.product_id, prod_id=safe_prod_id)
    if pattern_id is not None:
        db.add(OrdPattern(ord_id=new_ord.ord_id, ptn_id=pattern_id))

    # 6. 초기 상태 RCVD
    db.add(OrdTxn(ord_id=new_ord.ord_id, txn_type="RCVD"))
    db.add(OrdStat(ord_id=new_ord.ord_id, user_id=user.user_id, ord_stat="RCVD"))
    _append_ord_log(
        db,
        ord_id=new_ord.ord_id,
        prev_stat=None,
        new_stat="RCVD",
        changed_by=user.user_id,
    )
    db.commit()
    db.refresh(new_ord)

    return CustomerOrderResponse(
        ord_id=new_ord.ord_id,
        id=f"ord_{new_ord.ord_id}",
        user_id=user.user_id,
        created_at=new_ord.created_at,
        message="발주 등록 완료",
    )


@router.get("/lookup", response_model=list[OrdFull])
def lookup_orders_by_email(
    email: str = Query(..., min_length=1), db: Session = Depends(get_db)
) -> list[OrdFull]:
    """이메일로 고객 발주 조회.

    Pink GUI #1: 결과 비어있어도 200 + 빈 배열로 반환
    (frontend 에서 빈 배열 → "발주 기록 없음" 표시 + 다음 페이지 차단).
    """
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if not user:
        return []
    rows = (
        db.query(Ord)
        .options(selectinload(Ord.detail), selectinload(Ord.stats))
        .filter(Ord.user_id == user.user_id)
        .order_by(desc(Ord.created_at))
        .all()
    )
    return [_to_full(db, o) for o in rows]


@router.get("/{ord_id}", response_model=OrdFull)
def get_order(ord_id: int, db: Session = Depends(get_db)) -> OrdFull:
    o = db.get(Ord, ord_id)
    if not o:
        raise HTTPException(404, f"ord_id={ord_id} not found")
    return _to_full(db, o)


@router.post("/{ord_id}/status", response_model=OrdStatOut)
def update_order_status(
    ord_id: int,
    new_stat: str = Query(..., description="RCVD/APPR/MFG/DONE/SHIP/COMP/REJT/CNCL"),
    user_id: int | None = None,
    db: Session = Depends(get_db),
) -> OrdStatOut:
    """발주 상태 전이 (관리자)."""
    o = db.get(Ord, ord_id)
    if not o:
        raise HTTPException(404, f"ord_id={ord_id} not found")
    normalized_stat = _normalize_ord_status(new_stat)
    valid = {"RCVD", "APPR", "MFG", "DONE", "SHIPPING", "COMP", "REJT", "CNCL"}
    if normalized_stat not in valid:
        raise HTTPException(400, f"invalid status: {new_stat}")
    stat = db.query(OrdStat).filter(OrdStat.ord_id == ord_id).first()
    prev_stat = stat.ord_stat if stat is not None else None
    if stat is None:
        stat = OrdStat(ord_id=ord_id, user_id=user_id, ord_stat=normalized_stat)
        db.add(stat)
    else:
        stat.user_id = user_id
        stat.ord_stat = normalized_stat
        stat.updated_at = datetime.utcnow()
    if prev_stat != normalized_stat:
        _append_ord_txn_if_supported(db, ord_id=ord_id, new_stat=normalized_stat)
        _append_ord_log(
            db,
            ord_id=ord_id,
            prev_stat=prev_stat,
            new_stat=normalized_stat,
            changed_by=user_id,
        )
    db.commit()
    db.refresh(stat)
    return OrdStatOut.model_validate(stat)


# -------------------------------------------------------------------------
# Product / Category / PpOption / EquipLoadSpec
# -------------------------------------------------------------------------


@products_router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[ProductOut]:
    return [ProductOut.model_validate(p) for p in db.query(Product).all()]


@products_router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in db.query(Category).all()]


@products_router.get("/pp-options", response_model=list[PpOptionOut])
def list_pp_options(db: Session = Depends(get_db)) -> list[PpOptionOut]:
    return [PpOptionOut.model_validate(p) for p in db.query(PpOption).all()]


@load_classes_router.get("/equip-load-spec", tags=["load-classes"])
def list_load_specs(db: Session = Depends(get_db)) -> list[dict]:
    """legacy /api/load-classes 의 후속. 하중 등급별 정밀 제어 수치 반환."""
    rows = db.query(EquipLoadSpec).all()
    return [
        {
            "load_spec_id": r.load_spec_id,
            "load_class": r.load_class,
            "press_f": float(r.press_f) if r.press_f is not None else None,
            "press_t": float(r.press_t) if r.press_t is not None else None,
            "tol_val": float(r.tol_val) if r.tol_val is not None else None,
        }
        for r in rows
    ]
