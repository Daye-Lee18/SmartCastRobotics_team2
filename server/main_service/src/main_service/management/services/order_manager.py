"""
################################################################################
#                                                                              #
#   Interface Contract  —  OrderManager                                        #
#                                                                              #
################################################################################

이 파일의 목적:
    고객이 발주한 순간부터 DB 에 ord / ord_detail / ord_pp_map / ord_txn / ord_stat
    레코드가 저장되기까지를 한 트랜잭션으로 처리하는 컴포넌트.

흐름 (V모델 단위 테스트 대상):
    고객 상품 주문
        ↓ CreateOrderInput
    OrderManager.create_order()
        ↓ 비즈니스 검증 (user_id 존재, detail 필수, qty > 0)
        ↓ State Manager 경유 DB INSERT (ord + ord_detail + ord_pp_map + ord_txn + ord_stat)
        ↓ EventBridge.publish(ORDER_CREATED)
    OrderRecord 반환

관련 문서:
    - 42205202 코드 interface contracts 가이드 (본 파일의 템플릿 원본)
    - 32342045 DB Schema and ERD (ord/ord_detail/ord_txn/ord_stat 스펙)
    - 44794063 Event/Bridge v1 (ORDER_APPROVED 이벤트 소비자)
"""

from __future__ import annotations

# ── 필수 import ────────────────────────────────────────────────────────────────
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator

# ==============================================================================
# 1. OVERVIEW  ←  역할 정의 (문서화)
#    "이 컴포넌트가 왜 존재하는가"를 한 문단으로 설명합니다.
#    → 어디에 반영: INTERFACE_CONTRACTS.md 문서
# ==============================================================================
"""
[OrderManager]

역할:
    고객 상품 주문 시점부터 관리자 승인/반려/취소 까지, 주문(ord) 레코드의
    생명주기를 관리한다. 본 V모델 단위 테스트 범위는
    "고객 상품주문 → 주문 생성 → 주문 처리 요청 → DB 저장" 까지.

책임 범위:
    - 주문 생성 (create_order) — ord + ord_detail + ord_pp_map + ord_txn + ord_stat
      5개 테이블 한 트랜잭션 INSERT
    - 주문 상태 전이 검증 후 갱신 (process_order) — 승인/반려/취소
    - ORDER_CREATED / ORDER_APPROVED / ORDER_REJECTED / ORDER_CANCELLED 이벤트 발행
    - 단건 조회 (get_order)

책임 밖:
    - DB CRUD 의 실제 SQL → StateManager (세부는 self._state 로 위임)
    - 승인 후 실제 제조 task 생성 → TaskManager (ORDER_APPROVED 이벤트 구독자가 처리)
    - 결제·배송 → 본 프로젝트 범위 밖
"""


# ==============================================================================
# 2. ENUM  ←  상태값을 코드에서 강제
#    DB CHECK 제약과 동일한 값을 여기서도 선언합니다.
#    → 어디에 반영: Enum 코드
# ==============================================================================


class OrdStat(StrEnum):
    """
    ord_stat.ord_stat — 주문 상태
    DB CHECK: ord_stat IN ('RCVD','APPR','MFG','DONE','SHIP','COMP','REJT','CNCL')
    허용 전이: RCVD → APPR → MFG → DONE → SHIP → COMP
               RCVD → REJT (관리자 반려)
               RCVD → CNCL (고객 취소)
               APPR → CNCL (승인 후 취소)
    """

    RCVD = "RCVD"  # 수주 (Received)
    APPR = "APPR"  # 승인 (Approved)
    MFG = "MFG"  # 생산 (Manufacturing)
    DONE = "DONE"  # 생산 완료
    SHIP = "SHIP"  # 출고 중
    COMP = "COMP"  # 완료 (Completed)
    REJT = "REJT"  # 반려 (Rejected)
    CNCL = "CNCL"  # 취소 (Cancelled)


class OrdTxnType(StrEnum):
    """
    ord_txn.txn_type — 비즈니스 트랜잭션 종류
    DB CHECK: txn_type IN ('RCVD','APPR','CNCL','REJT')
    주문 생성/승인/반려/취소 시마다 append-only 로 1행 기록.
    """

    RCVD = "RCVD"  # 주문 접수
    APPR = "APPR"  # 승인 처리
    CNCL = "CNCL"  # 취소 처리
    REJT = "REJT"  # 반려 처리


# 상태 전이 규칙 — 이 dict 를 벗어난 전이는 ValueError
_ORDER_TRANSITIONS: dict[OrdStat, set[OrdStat]] = {
    OrdStat.RCVD: {OrdStat.APPR, OrdStat.REJT, OrdStat.CNCL},
    OrdStat.APPR: {OrdStat.MFG, OrdStat.CNCL},
    OrdStat.MFG: {OrdStat.DONE},
    OrdStat.DONE: {OrdStat.SHIP},
    OrdStat.SHIP: {OrdStat.COMP},
    OrdStat.COMP: set(),  # terminal
    OrdStat.REJT: set(),  # terminal
    OrdStat.CNCL: set(),  # terminal
}


def validate_order_transition(current: OrdStat, nxt: OrdStat) -> None:
    """현재 상태에서 nxt 상태로 전이 가능한지 검증. 불가능하면 ValueError."""
    if nxt not in _ORDER_TRANSITIONS[current]:
        raise ValueError(f"Invalid order transition: {current.value} → {nxt.value}")


# ==============================================================================
# 3. DATATYPE  ←  데이터 구조 정의
#    Pydantic BaseModel 로 선언 → 직렬화·검증 자동화
#    → 어디에 반영: Pydantic 모델
# ==============================================================================


class OrderDetailInput(BaseModel):
    """주문 상세 (ord_detail 1행에 대응). 고객 발주 폼 필드."""

    prod_id: int | None = Field(default=None, gt=0, description="표준 제품 ID (product.prod_id)")
    diameter: Decimal | None = Field(default=None, description="직경 mm")
    thickness: Decimal | None = Field(default=None, description="두께 mm")
    material: str | None = Field(default=None, max_length=30, description="재질 (회주철/덕타일 등)")
    load_class: str | None = Field(
        default=None, max_length=20, description="하중 등급 (A15/D400/F900 등)"
    )
    qty: int = Field(..., gt=0, description="수량 (필수, >0)")
    final_price: Decimal | None = Field(default=None, ge=0, description="확정 금액")
    due_date: date | None = Field(default=None, description="납기일")
    ship_addr: str | None = Field(default=None, description="배송지 주소")


class CreateOrderInput(BaseModel):
    """create_order() 입력값 — 고객이 "주문하기" 버튼을 누른 시점의 데이터."""

    user_id: int = Field(..., gt=0, description="주문자 user_account.user_id")
    detail: OrderDetailInput = Field(..., description="주문 상세 (1:1)")
    pp_ids: list[int] = Field(
        default_factory=list, description="선택한 후처리 pp_options.pp_id 목록"
    )


class OrderRecord(BaseModel):
    """DB ord 한 행 + 최신 ord_stat 요약. create_order / get_order 반환값."""

    ord_id: int
    user_id: int
    created_at: datetime | None = None
    latest_stat: OrdStat | None = None  # 최신 ord_stat.ord_stat
    detail: OrderDetailInput | None = None
    pp_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_ord_id_positive(self) -> OrderRecord:
        if self.ord_id is not None and self.ord_id <= 0:
            raise ValueError("ord_id 는 양수여야 합니다")
        return self


class ProcessOrderInput(BaseModel):
    """process_order() 입력값 — 관리자 승인/반려/취소 액션."""

    ord_id: int = Field(..., gt=0)
    new_stat: OrdStat = Field(..., description="RCVD 이후 전이할 상태 (APPR/REJT/CNCL/...)")
    reviewer_id: int | None = Field(default=None, gt=0, description="처리한 관리자 user_id")
    reason: str | None = Field(default=None, max_length=200, description="반려/취소 사유")


# ==============================================================================
# 4. INPUT / OUTPUT  ←  인터페이스 계약 (Protocol)
#    Protocol 로 선언 → 구현 클래스가 이 시그니처를 반드시 따라야 함
#    → 어디에 반영: Protocol + Pydantic
# ==============================================================================


@runtime_checkable
class IOrderManager(Protocol):
    """
    OrderManager 가 외부에 노출하는 공개 인터페이스.

    INPUT  → Pydantic 모델 (섹션 3 참조)
    OUTPUT → OrderRecord (Pydantic) 또는 None
    """

    def create_order(self, data: CreateOrderInput) -> OrderRecord:
        """
        고객 주문 접수 → DB 5개 테이블 INSERT 를 한 트랜잭션으로 수행.

        Input:  CreateOrderInput
        Output: OrderRecord (ord_id 자동 부여, latest_stat=RCVD)
        Raises:
          - ValueError — user_id / detail.qty 가 잘못된 경우
        Side Effects:
          - INSERT INTO ord
          - INSERT INTO ord_detail
          - INSERT INTO ord_pp_map (pp_ids 별로 1행씩, 빈 리스트면 skip)
          - INSERT INTO ord_txn (txn_type=RCVD)
          - INSERT INTO ord_stat (ord_stat=RCVD)
          - EventBridge.publish(ORDER_CREATED)
        """
        ...

    def process_order(self, data: ProcessOrderInput) -> OrderRecord:
        """
        주문 상태를 전이하고 변경 이력을 기록한다 (관리자 승인/반려/취소).

        Input:  ProcessOrderInput
        Output: OrderRecord (latest_stat 갱신 후)
        Raises:
          - ValueError — 허용되지 않은 전이 / 존재하지 않는 ord_id
        Side Effects:
          - INSERT INTO ord_txn (txn_type=APPR/REJT/CNCL)
          - INSERT INTO ord_stat (ord_stat=APPR/REJT/CNCL/...)
          - EventBridge.publish(ORDER_APPROVED/ORDER_REJECTED/ORDER_CANCELLED)
        """
        ...

    def get_order(self, ord_id: int) -> OrderRecord | None:
        """
        ord_id 로 단건 조회. 없으면 None. latest_stat 는 ord_stat 의 최신 row 기준.

        Input:  ord_id (int)
        Output: OrderRecord | None
        Side Effects: 없음 (read-only)
        """
        ...


# ==============================================================================
# 5. EVENT  ←  시스템 상태가 바뀌는 지점 (물리/DB)
#    "어떤 일이 벌어졌을 때 이벤트가 발생하는가" 를 명시합니다.
#    → 어디에 반영: 문서 + 일부 코드 (EventBridge 에서 사용)
# ==============================================================================
"""
[OrderManager 가 발행하는 이벤트]

이벤트명            발생 조건                          물리적 의미
─────────────────────────────────────────────────────────────────────────
ORDER_CREATED       create_order() 성공 직후           고객 발주 접수 완료, 승인 대기
ORDER_APPROVED      RCVD → APPR 전이 완료 시           TaskManager 가 CAST task 생성할 트리거
ORDER_REJECTED      RCVD → REJT 전이 완료 시           고객에게 반려 통지
ORDER_CANCELLED     * → CNCL 전이 완료 시               이미 진행 중인 공정은 중단 신호

[이벤트를 수신하는 컴포넌트]
  ORDER_CREATED    → (현 범위 외) 관리자 UI 에 신규 주문 표시
  ORDER_APPROVED   → TaskManager.on_order_approved (CAST task 생성)
                   → StateManager (ord_stat 변경 감사 로그)
  ORDER_REJECTED   → (현 범위 외) 고객 이메일 알림 서비스
  ORDER_CANCELLED  → TaskManager (진행 중 task 중단) · AuditLogger
"""


class OrderEventType(StrEnum):
    """OrderManager 가 EventBridge 에 발행하는 이벤트 종류."""

    ORDER_CREATED = "ORDER_CREATED"
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


class OrderEvent(BaseModel):
    """EventBridge 로 보내는 페이로드. Event Bridge 의 Event 로 변환되어 발행된다."""

    event_type: OrderEventType
    ord_id: int
    user_id: int
    occurred_at: datetime = Field(default_factory=datetime.now)
    reviewer_id: int | None = None
    reason: str | None = None


# ==============================================================================
# 6. RESULT  ←  인터페이스의 성공/실패 기준
#    테스트 파일(tests/test_order_manager.py) 에서 이 기준을 검증합니다.
#    → 어디에 반영: 테스트 코드
# ==============================================================================
"""
[create_order 성공 기준]
  ✅ 반환된 OrderRecord.ord_id > 0
  ✅ 반환된 OrderRecord.latest_stat == OrdStat.RCVD
  ✅ 반환된 OrderRecord.user_id == 입력 user_id
  ✅ DB ord / ord_detail / ord_txn / ord_stat 각 1행씩 INSERT
  ✅ pp_ids 가 N개면 ord_pp_map 에 N행 INSERT (빈 리스트면 0행)
  ✅ ord_txn.txn_type == 'RCVD'
  ✅ ord_stat.ord_stat == 'RCVD'
  ✅ EventBridge.publish 가 ORDER_CREATED 이벤트로 1회 호출됨

[create_order 실패 기준]
  ❌ user_id <= 0 → ValidationError
  ❌ detail.qty <= 0 → ValidationError
  ❌ detail 필드 누락 → ValidationError
  ❌ DB 커밋 실패 → 예외 전파 + 트랜잭션 롤백 + 이벤트 미발행

[process_order 성공 기준]
  ✅ RCVD → APPR: ord_txn + ord_stat INSERT, ORDER_APPROVED 이벤트 발행
  ✅ RCVD → REJT: ord_txn + ord_stat INSERT, ORDER_REJECTED 이벤트 발행
  ✅ RCVD → CNCL: ord_txn + ord_stat INSERT, ORDER_CANCELLED 이벤트 발행

[process_order 실패 기준]
  ❌ RCVD → MFG (skip) → ValueError: "Invalid order transition: RCVD → MFG"
  ❌ APPR → RCVD (역방향) → ValueError
  ❌ 존재하지 않는 ord_id → ValueError: "ord_id <N> not found"

[get_order 기준]
  ✅ 존재하는 ord_id → OrderRecord 반환 (latest_stat 포함)
  ✅ 존재하지 않는 ord_id → None 반환 (예외 아님)

[테스트 파일 위치]
  backend/management/tests/test_order_manager.py
"""


# ==============================================================================
# 7. SIDE EFFECTS  ←  시스템에 미치는 영향
#    실제 구현 — 단위 테스트 검증 대상.
#    → 어디에 반영: 실제 구현 코드
# ==============================================================================


class OrderManagerImpl:
    """
    IOrderManager 의 실제 구현체.

    Side Effects 목록:
      create_order()
        → state.insert_ord(user_id)                     [DB INSERT ord]
        → state.insert_ord_detail(ord_id, detail)       [DB INSERT ord_detail]
        → state.insert_ord_pp_maps(ord_id, pp_ids)      [DB INSERT ord_pp_map × N]
        → state.insert_ord_txn(ord_id, RCVD)            [DB INSERT ord_txn]
        → state.insert_ord_stat(ord_id, user_id, RCVD)  [DB INSERT ord_stat]
        → event_bridge.publish(ORDER_CREATED)

      process_order() RCVD → APPR
        → state.insert_ord_txn(ord_id, APPR)
        → state.insert_ord_stat(ord_id, reviewer_id, APPR)
        → event_bridge.publish(ORDER_APPROVED)

      process_order() RCVD → REJT
        → state.insert_ord_txn(ord_id, REJT)
        → state.insert_ord_stat(ord_id, reviewer_id, REJT)
        → event_bridge.publish(ORDER_REJECTED)

      process_order() * → CNCL
        → state.insert_ord_txn(ord_id, CNCL)
        → state.insert_ord_stat(ord_id, reviewer_id, CNCL)
        → event_bridge.publish(ORDER_CANCELLED)

    설계 원칙:
      - DB 접근은 State Manager 에 위임 (self._state). OrderManager 는 직접 SQL 실행하지 않음.
      - 이벤트 발행 주체 = 본 컴포넌트 (액션을 실제로 수행한 곳).
      - 상태 전이는 _ORDER_TRANSITIONS 규칙을 통과한 후에만 실행.
    """

    def __init__(self, state_manager, event_bridge) -> None:
        self._state = state_manager  # State Manager 의 read/write 래퍼 (DB 관문)
        self._eb = event_bridge  # EventBridge 인스턴스

    def create_order(self, data: CreateOrderInput) -> OrderRecord:
        """고객 주문 생성. 5개 테이블 INSERT + ORDER_CREATED 이벤트."""
        # 1. 추가 비즈니스 검증 (Pydantic 으로 걸러지지 않는 것)
        if data.detail.qty is None or data.detail.qty <= 0:
            raise ValueError("detail.qty 는 1 이상이어야 합니다")

        # 2. 한 트랜잭션으로 5개 테이블 INSERT (State Manager 에 위임)
        ord_id = self._state.insert_ord(user_id=data.user_id)
        self._state.insert_ord_detail(ord_id=ord_id, detail=data.detail)

        for pp_id in data.pp_ids:
            self._state.insert_ord_pp_map(ord_id=ord_id, pp_id=pp_id)

        self._state.insert_ord_txn(ord_id=ord_id, txn_type=OrdTxnType.RCVD)
        self._state.insert_ord_stat(ord_id=ord_id, user_id=data.user_id, ord_stat=OrdStat.RCVD)

        # 3. 이벤트 발행 — 액션 수행 주체가 발행 (EventBridge 원칙)
        self._eb.publish(
            OrderEvent(
                event_type=OrderEventType.ORDER_CREATED,
                ord_id=ord_id,
                user_id=data.user_id,
            )
        )

        # 4. 반환
        return OrderRecord(
            ord_id=ord_id,
            user_id=data.user_id,
            created_at=datetime.now(),
            latest_stat=OrdStat.RCVD,
            detail=data.detail,
            pp_ids=list(data.pp_ids),
        )

    def process_order(self, data: ProcessOrderInput) -> OrderRecord:
        """주문 상태 전이 (승인/반려/취소)."""
        # 1. 현재 상태 조회
        existing = self._state.get_ord_with_latest_stat(data.ord_id)
        if existing is None:
            raise ValueError(f"ord_id {data.ord_id} not found")

        current_stat: OrdStat = existing.latest_stat or OrdStat.RCVD

        # 2. 전이 검증
        validate_order_transition(current_stat, data.new_stat)

        # 3. ord_txn 기록 (APPR/REJT/CNCL 만 txn 남김. MFG/DONE/SHIP 은 txn 미사용)
        txn_map = {
            OrdStat.APPR: OrdTxnType.APPR,
            OrdStat.REJT: OrdTxnType.REJT,
            OrdStat.CNCL: OrdTxnType.CNCL,
        }
        if data.new_stat in txn_map:
            self._state.insert_ord_txn(ord_id=data.ord_id, txn_type=txn_map[data.new_stat])

        # 4. ord_stat 기록
        self._state.insert_ord_stat(
            ord_id=data.ord_id,
            user_id=data.reviewer_id or existing.user_id,
            ord_stat=data.new_stat,
        )

        # 5. 이벤트 발행
        event_map = {
            OrdStat.APPR: OrderEventType.ORDER_APPROVED,
            OrdStat.REJT: OrderEventType.ORDER_REJECTED,
            OrdStat.CNCL: OrderEventType.ORDER_CANCELLED,
        }
        if data.new_stat in event_map:
            self._eb.publish(
                OrderEvent(
                    event_type=event_map[data.new_stat],
                    ord_id=data.ord_id,
                    user_id=existing.user_id,
                    reviewer_id=data.reviewer_id,
                    reason=data.reason,
                )
            )

        # 6. 갱신된 record 반환
        return OrderRecord(
            ord_id=data.ord_id,
            user_id=existing.user_id,
            created_at=existing.created_at,
            latest_stat=data.new_stat,
            detail=existing.detail,
            pp_ids=existing.pp_ids,
        )

    def get_order(self, ord_id: int) -> OrderRecord | None:
        """단건 조회 — State Manager 에 위임."""
        return self._state.get_ord_with_latest_stat(ord_id)
