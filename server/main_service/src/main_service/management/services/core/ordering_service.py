"""
################################################################################
#                                                                              #
#   Interface Contract  —  OrderingService                                     #
#                                                                              #
################################################################################

이 파일의 목적:
    고객 UI (Next.js / PyQt) 의 상품 주문 HTTP/gRPC 요청을 받아서
    OrderManager 도메인 서비스에 위임하는 "API 경계 레이어".

흐름:
    고객 상품 주문 (HTTP POST /api/orders)
        ↓ OrderSubmissionRequest (HTTP body)
    OrderingService.submit_order()
        ↓ 입력 검증 (Pydantic) · 권한 체크 · 비즈니스 규칙
        ↓ OrderManager.create_order() 위임
        ↓ OrderRecord 수신
    OrderSubmissionResponse 반환 (HTTP 201 + JSON body)

OrderManager 와의 차이:
    OrderManager   = 도메인 로직 (상태 전이, DB 트랜잭션, 이벤트 발행)
    OrderingService = 프로토콜 어댑터 (HTTP 파싱, 인증, 응답 직렬화, 에러 매핑)

관련 문서:
    - 42205202 코드 interface contracts 가이드 (템플릿 원본)
    - 39324832 Sprint 5 Test Plan (본 서비스의 Sequence 세분화 테스트 대상)
"""

from __future__ import annotations

# ── 필수 import ────────────────────────────────────────────────────────────────
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

# OrderManager 와 타입 공유
from services.core.order_manager import (
    CreateOrderInput,
    IOrderManager,
    OrderDetailInput,
    OrderRecord,
    OrdStat,
)

# ==============================================================================
# 1. OVERVIEW  ←  역할 정의 (문서화)
# ==============================================================================
"""
[OrderingService]

역할:
    고객 UI 가 "주문하기" 버튼을 누른 순간부터 OrderManager 가 비즈니스 로직을
    시작하기 직전까지의 **프로토콜 경계·사용자 레이어** 를 담당한다.

책임 범위:
    - HTTP/gRPC 요청 파싱 → OrderSubmissionRequest
    - 입력 형식 검증 (Pydantic 필수 필드, 타입)
    - 인증·권한 검증 (user_id 존재 여부)
    - 비즈니스 규칙 pre-check (qty > 0, pp_ids 중복 제거 등)
    - OrderManager.create_order() 호출 + 반환값 변환
    - 에러 매핑 (ValidationError → 400, 권한 실패 → 401, DB 실패 → 503)
    - OrderSubmissionResponse 반환 (HTTP status + JSON body)

책임 밖:
    - ord 테이블 INSERT / 상태 전이 → OrderManager
    - DB 세션·트랜잭션 관리 → State Manager
    - 이벤트 발행 → OrderManager (EventBridge 경유)
    - 상품 카탈로그 조회 → ProductService (별도)
"""


# ==============================================================================
# 2. ENUM  ←  상태값을 코드에서 강제
# ==============================================================================


class OrderSubmissionStatus(StrEnum):
    """
    OrderSubmissionResponse.status — 요청 결과 분류.
    HTTP status code 와 매핑되는 논리 상태.
    """

    ACCEPTED = "ACCEPTED"  # 주문 정상 접수 → HTTP 201
    DUPLICATE = "DUPLICATE"  # 동일 idempotency_key 재요청 → HTTP 200 (기존 결과 반환)
    VALIDATION_ERR = "VALIDATION_ERR"  # 입력 검증 실패 → HTTP 400
    UNAUTHORIZED = "UNAUTHORIZED"  # 권한 없음 → HTTP 401
    SERVICE_ERR = "SERVICE_ERR"  # DB 실패 등 → HTTP 503


# HTTP status code 매핑 (어댑터가 사용)
HTTP_STATUS_MAP: dict[OrderSubmissionStatus, int] = {
    OrderSubmissionStatus.ACCEPTED: 201,
    OrderSubmissionStatus.DUPLICATE: 200,
    OrderSubmissionStatus.VALIDATION_ERR: 400,
    OrderSubmissionStatus.UNAUTHORIZED: 401,
    OrderSubmissionStatus.SERVICE_ERR: 503,
}


# ==============================================================================
# 3. DATATYPE  ←  데이터 구조 정의
# ==============================================================================


class OrderSubmissionRequest(BaseModel):
    """
    고객 UI → OrderingService HTTP body.
    HTTP 어댑터가 FastAPI Pydantic body 로 수신하는 그 형태.

    idempotency_key 는 선택 — "새로고침 더블 클릭" 같은 중복 방지용.
    """

    user_id: int = Field(..., gt=0, description="로그인한 user_account.user_id")
    detail: OrderDetailInput = Field(..., description="상품 주문 상세")
    pp_ids: list[int] = Field(
        default_factory=list, description="선택한 후처리 pp_options.pp_id 목록"
    )
    idempotency_key: str | None = Field(
        default=None, max_length=64, description="UI 쪽 생성 고유 키 (중복 요청 방지)"
    )


class OrderSubmissionResponse(BaseModel):
    """
    OrderingService → 고객 UI HTTP response body.
    HTTP 어댑터가 status_code + 이 body 를 그대로 내려준다.
    """

    status: OrderSubmissionStatus
    ord_id: int | None = Field(default=None, description="생성된 주문 ID (ACCEPTED 시)")
    user_id: int | None = None
    latest_stat: OrdStat | None = Field(default=None, description="주문 상태 (현재는 RCVD 고정)")
    message: str = Field(default="", description="사용자에게 표시할 메시지")
    http_code: int = 200


# ==============================================================================
# 4. INPUT / OUTPUT  ←  인터페이스 계약 (Protocol)
# ==============================================================================


@runtime_checkable
class IOrderingService(Protocol):
    """OrderingService 가 외부에 노출하는 공개 인터페이스."""

    def submit_order(self, request: OrderSubmissionRequest) -> OrderSubmissionResponse:
        """
        고객 상품 주문을 받아 OrderManager 에 위임하고 결과를 반환한다.

        Input:  OrderSubmissionRequest (HTTP body)
        Output: OrderSubmissionResponse (status + ord_id + http_code)
        Raises: 예외를 던지지 않음 — 모든 오류는 response.status 로 매핑
        Side Effects: OrderManager.create_order() 호출 (→ DB INSERT + 이벤트 발행)
        """
        ...

    def query_order(self, ord_id: int, user_id: int) -> OrderSubmissionResponse:
        """
        주문 단건 조회 (본인 소유만).

        Input:  ord_id, user_id
        Output: OrderSubmissionResponse (찾으면 ACCEPTED + latest_stat, 없으면 VALIDATION_ERR)
        Raises: 없음
        Side Effects: 없음 (read-only)
        """
        ...


# ==============================================================================
# 5. EVENT  ←  발행하는 이벤트
# ==============================================================================
"""
[OrderingService 가 직접 발행하는 이벤트]

  없음. 이벤트 발행은 OrderManager 에 위임.

  OrderingService 는 순수한 "프로토콜 어댑터" 로서 이벤트를 발행하지 않고,
  OrderManager.create_order() 내부에서 ORDER_CREATED 이벤트가 발행된다.
  (EventBridge 고정 원칙: 이벤트 발행 주체 = 상태를 실제로 바꾼 도메인 서비스)
"""


# ==============================================================================
# 6. RESULT  ←  성공/실패 기준
# ==============================================================================
"""
[submit_order 성공 기준]
  ✅ 반환 OrderSubmissionResponse.status == ACCEPTED
  ✅ 반환 ord_id > 0
  ✅ 반환 http_code == 201
  ✅ OrderManager.create_order() 가 정확히 1회 호출됨
  ✅ 내부 OrderManager 가 ORDER_CREATED 이벤트를 발행

[submit_order 실패 기준]
  ❌ user_id <= 0 / detail 누락 → status=VALIDATION_ERR, http_code=400
  ❌ qty <= 0 → status=VALIDATION_ERR, http_code=400
  ❌ 알 수 없는 user_id (권한 실패) → status=UNAUTHORIZED, http_code=401
  ❌ DB 실패 (OrderManager 가 예외 전파) → status=SERVICE_ERR, http_code=503
  ❌ 어떤 경우에도 OrderingService 자체가 예외를 던지지 않음 (HTTP 어댑터 안정성)

[query_order 성공/실패 기준]
  ✅ 존재하는 ord_id + 본인 소유 → ACCEPTED + latest_stat
  ❌ 존재하지 않음 / 타인 소유 → VALIDATION_ERR

[테스트 파일 위치]
  backend/management/tests/test_ordering_service.py

[Sprint 5 Sequence 매핑]
  Seq 1 — 주문 요청 Pydantic 스키마 검증 (필수 필드, 타입)
  Seq 2 — user_id 인증 체크 (존재 여부)
  Seq 3 — 비즈니스 pre-check (qty > 0, pp_ids 중복 제거)
  Seq 4 — OrderManager.create_order() 위임 1회 호출
  Seq 5 — DB 5개 테이블 INSERT (OrderManager 내부)
  Seq 6 — ORDER_CREATED 이벤트 발행 (OrderManager 내부)
  Seq 7 — OrderSubmissionResponse 반환 (ACCEPTED + http 201 + ord_id)
  Seq 8 — Idempotency 중복 요청 처리 (DUPLICATE + http 200)
  Seq 9 — 내부 예외를 HTTP 에러로 매핑 (SERVICE_ERR + http 503)
  Seq 10 — query_order 읽기 경로 (ACCEPTED + latest_stat 포함)
"""


# ==============================================================================
# 7. SIDE EFFECTS  ←  실제 구현
# ==============================================================================


class OrderingServiceImpl:
    """
    IOrderingService 의 실제 구현체.

    Side Effects 목록:
      submit_order() ACCEPTED 경로:
        → OrderManager.create_order() 1회 호출 (내부에서 DB INSERT + 이벤트 발행)
        → OrderSubmissionResponse 생성 (status=ACCEPTED, http=201)

      submit_order() 실패 경로:
        → OrderManager 호출하지 않음 (조기 반환)
        → OrderSubmissionResponse 생성 (status=VALIDATION_ERR/UNAUTHORIZED, 4xx)

      submit_order() 내부 예외 시:
        → OrderManager 에서 던진 예외를 잡아서 SERVICE_ERR 로 매핑
        → OrderingService 자체가 raise 하지 않음 (HTTP 어댑터 보장)

      query_order():
        → OrderManager.get_order() 호출 (read-only)
        → 본인 소유 여부 검증

    설계 원칙:
      - OrderingService 는 HTTP/gRPC 프로토콜 지식만 가짐. 도메인 로직은 없음
      - 모든 오류를 예외 대신 response.status 로 반환 (어댑터 간결화)
      - OrderManager 는 도메인 서비스로 신뢰 (검증·트랜잭션 책임)
      - 중복 방지를 위한 idempotency_key 내부 캐시 사용 (간단한 인메모리)
    """

    def __init__(
        self,
        order_manager: IOrderManager,
        user_validator=None,
    ) -> None:
        """
        order_manager:   OrderManager 인스턴스 (도메인 서비스)
        user_validator:  Callable[[int], bool] — user_id 존재 여부 검증 (선택).
                         None 이면 인증 검증 건너뜀 (테스트·개발 환경용).
        """
        self._om = order_manager
        self._user_validator = user_validator
        # idempotency: {key: response} — 간단한 인메모리 (프로덕션은 Redis 권장)
        self._idempotency_cache: dict[str, OrderSubmissionResponse] = {}

    # ── submit_order ────────────────────────────────────────────────────
    def submit_order(self, request: OrderSubmissionRequest) -> OrderSubmissionResponse:
        """IOrderingService.submit_order 참조."""
        # [Seq 8] Idempotency 우선 체크
        if request.idempotency_key and request.idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[request.idempotency_key]
            return OrderSubmissionResponse(
                status=OrderSubmissionStatus.DUPLICATE,
                ord_id=cached.ord_id,
                user_id=cached.user_id,
                latest_stat=cached.latest_stat,
                message="duplicate idempotency_key — existing result returned",
                http_code=HTTP_STATUS_MAP[OrderSubmissionStatus.DUPLICATE],
            )

        # [Seq 3] 비즈니스 pre-check — Pydantic 으로 잡히지 않는 규칙
        # (qty<=0 등은 OrderDetailInput 단에서 걸러지지만, 추가 규칙은 여기)
        if request.detail.qty is None or request.detail.qty <= 0:
            return self._err(OrderSubmissionStatus.VALIDATION_ERR, "qty 는 1 이상이어야 합니다")

        # [Seq 2] 인증 검증
        if self._user_validator is not None and not self._user_validator(request.user_id):
            return self._err(
                OrderSubmissionStatus.UNAUTHORIZED, f"user_id {request.user_id} 권한 없음"
            )

        # [Seq 4] OrderManager 위임
        try:
            record: OrderRecord = self._om.create_order(
                CreateOrderInput(
                    user_id=request.user_id,
                    detail=request.detail,
                    pp_ids=list(dict.fromkeys(request.pp_ids)),  # 중복 제거, 순서 유지
                )
            )
        except ValueError as e:
            # 도메인 검증 실패
            return self._err(OrderSubmissionStatus.VALIDATION_ERR, str(e))
        except Exception as e:  # noqa: BLE001 — HTTP 레이어 안정성 최우선
            return self._err(OrderSubmissionStatus.SERVICE_ERR, f"service error: {e}")

        # [Seq 7] 성공 응답 생성
        response = OrderSubmissionResponse(
            status=OrderSubmissionStatus.ACCEPTED,
            ord_id=record.ord_id,
            user_id=record.user_id,
            latest_stat=record.latest_stat,
            message="order accepted",
            http_code=HTTP_STATUS_MAP[OrderSubmissionStatus.ACCEPTED],
        )

        # Idempotency 캐시 저장
        if request.idempotency_key:
            self._idempotency_cache[request.idempotency_key] = response

        return response

    # ── query_order ─────────────────────────────────────────────────────
    def query_order(self, ord_id: int, user_id: int) -> OrderSubmissionResponse:
        """IOrderingService.query_order 참조."""
        if ord_id <= 0 or user_id <= 0:
            return self._err(OrderSubmissionStatus.VALIDATION_ERR, "ord_id / user_id 는 양수")

        record = self._om.get_order(ord_id)
        if record is None:
            return self._err(OrderSubmissionStatus.VALIDATION_ERR, f"ord_id {ord_id} not found")

        if record.user_id != user_id:
            return self._err(OrderSubmissionStatus.UNAUTHORIZED, "본인 주문만 조회 가능")

        return OrderSubmissionResponse(
            status=OrderSubmissionStatus.ACCEPTED,
            ord_id=record.ord_id,
            user_id=record.user_id,
            latest_stat=record.latest_stat,
            message="ok",
            http_code=HTTP_STATUS_MAP[OrderSubmissionStatus.ACCEPTED],
        )

    # ── helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _err(status: OrderSubmissionStatus, message: str) -> OrderSubmissionResponse:
        """에러 응답 빌더 — status 와 HTTP code 매핑을 일관되게."""
        return OrderSubmissionResponse(
            status=status,
            ord_id=None,
            user_id=None,
            latest_stat=None,
            message=message,
            http_code=HTTP_STATUS_MAP[status],
        )
