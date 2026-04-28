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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Category,
    EquipLoadSpec,
    Ord,
    OrdDetail,
    OrdPpMap,
    OrdStat,
    OrdTxn,
    Pattern,
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

    detail = OrdDetail(ord_id=new_ord.ord_id, **payload.detail.model_dump(exclude_none=True))
    db.add(detail)

    for pp_id in payload.pp_ids:
        db.add(OrdPpMap(ord_id=new_ord.ord_id, pp_id=pp_id))

    # 초기 상태 RCVD (txn + stat 동시 INSERT)
    db.add(OrdTxn(ord_id=new_ord.ord_id, txn_type="RCVD"))
    db.add(OrdStat(ord_id=new_ord.ord_id, user_id=payload.user_id, ord_stat="RCVD"))
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
    "polish": "표면연마",
    "coat": "방청코팅",
    "zinc": "아연도금",
    "logo": "로고문구삽입",
}


# 자동 패턴 위치 매핑 — frontend product_id 첫 글자 기준
# CLAUDE.md (2026-04-27): 카테고리 → ptn_loc 자동 결정. 운영자 수동 입력 폐지.
#   R-* (원형 round)   → ptn_loc=1
#   S-* (사각 square)  → ptn_loc=2
#   O-* (타원형 oval)  → ptn_loc=3
# 4-6번 위치는 사용 안 함 (확장 여유).
_CATEGORY_PREFIX_TO_PTN_LOC: dict[str, int] = {
    "R": 1,  # Round
    "S": 2,  # Square
    "O": 3,  # Oval
}


def derive_ptn_loc(product_id: str | None) -> int | None:
    """frontend product_id ('R-D450', 'S-400', 'O-500' 등) → ptn_loc (1/2/3).

    매핑 없는 ID 는 None 반환 → 호출자가 Pattern row 생성 스킵.
    """
    if not product_id:
        return None
    prefix = product_id.strip()[:1].upper()
    return _CATEGORY_PREFIX_TO_PTN_LOC.get(prefix)


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
            password=None,
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

    # 폼의 diameter/thickness 는 다양한 형식:
    #   "600mm"      → 600.0 (원형맨홀)
    #   "450x450mm"  → 450.0 (사각맨홀 — 첫 값만)
    #   "450x300mm"  → 450.0 (타원맨홀 — 첫 값만)
    #   "50"         → 50.0
    # 첫 번째 숫자군만 추출하여 DECIMAL 에 저장.
    import re

    _NUM_RE = re.compile(r"\d+(?:\.\d+)?")

    def _strip_unit(v: str | None) -> float | None:
        if v is None:
            return None
        m = _NUM_RE.search(str(v))
        return float(m.group()) if m else None

    from datetime import date

    due_date = None
    if payload.requested_delivery:
        try:
            due_date = date.fromisoformat(payload.requested_delivery[:10])
        except ValueError:
            pass

    # prod_id 는 product 테이블에 실제 존재할 때만 사용 (없으면 NULL → FK 위반 방지).
    # 폼이 보내는 product_id 는 frontend mock-data 의 string id 이므로 즉시 매칭 어려움.
    candidate_prod_id: int | None = (
        int(d0.product_id) if (d0.product_id and d0.product_id.isdigit()) else None
    )
    safe_prod_id: int | None = None
    if candidate_prod_id is not None:
        if db.get(Product, candidate_prod_id) is not None:
            safe_prod_id = candidate_prod_id

    detail = OrdDetail(
        ord_id=new_ord.ord_id,
        prod_id=safe_prod_id,
        diameter=_strip_unit(d0.diameter),
        thickness=_strip_unit(d0.thickness),
        material=d0.material,
        load_class=d0.load_class,
        qty=d0.quantity,
        final_price=payload.total_amount,
        due_date=due_date,
        ship_addr=payload.shipping_address,
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

    # 5. 자동 패턴 위치 등록 — 카테고리에서 ptn_loc 결정 (운영자 수동 입력 폐지).
    # frontend product_id (예: 'R-D450') 첫 글자로 카테고리 판단:
    #   R → ptn_loc 1 (원형), S → 2 (사각), O → 3 (타원형)
    # 매핑 실패 시 Pattern row 생성 안 함 (Pattern 미등록 → 생산 시작 차단).
    ptn_loc = derive_ptn_loc(d0.product_id)
    if ptn_loc is not None:
        db.add(Pattern(ptn_id=new_ord.ord_id, ptn_loc=ptn_loc))

    # 6. 초기 상태 RCVD
    db.add(OrdTxn(ord_id=new_ord.ord_id, txn_type="RCVD"))
    db.add(OrdStat(ord_id=new_ord.ord_id, user_id=user.user_id, ord_stat="RCVD"))
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
    valid = {"RCVD", "APPR", "MFG", "DONE", "SHIP", "COMP", "REJT", "CNCL"}
    if new_stat not in valid:
        raise HTTPException(400, f"invalid status: {new_stat}")
    stat = OrdStat(ord_id=ord_id, user_id=user_id, ord_stat=new_stat)
    db.add(stat)
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
