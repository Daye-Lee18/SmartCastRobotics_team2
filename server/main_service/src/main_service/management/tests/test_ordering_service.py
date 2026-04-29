"""OrderingService 단위 테스트 (V모델 Sprint 5 — Sequence 세분화).

시나리오: 고객 상품 주문 HTTP 요청 → OrderingService → OrderManager 위임까지.

Sequence 매핑 (Sprint 5 Test Plan 세분화):
  Seq 1  : 주문 요청 Pydantic 스키마 검증 (필수 필드, 타입)
  Seq 2  : user_id 인증 체크 (user_validator 주입)
  Seq 3  : 비즈니스 pre-check (qty > 0, pp_ids 중복 제거)
  Seq 4  : OrderManager.create_order() 1회 위임
  Seq 5  : DB 5개 테이블 INSERT 확인 (OrderManager 내부)
  Seq 6  : ORDER_CREATED 이벤트 발행 확인 (OrderManager 내부)
  Seq 7  : OrderSubmissionResponse 반환 (ACCEPTED + http 201 + ord_id)
  Seq 8  : Idempotency 중복 요청 처리 (DUPLICATE + http 200)
  Seq 9  : 내부 예외 → HTTP 에러 매핑 (SERVICE_ERR + http 503)
  Seq 10 : query_order 읽기 경로 (ACCEPTED + latest_stat 포함)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from services.order_manager import (
    CreateOrderInput,
    OrderDetailInput,
    OrderEvent,
    OrderEventType,
    OrderManagerImpl,
    OrderRecord,
    OrdStat,
)
from services.ordering_service import (
    HTTP_STATUS_MAP,
    IOrderingService,
    OrderingServiceImpl,
    OrderSubmissionRequest,
    OrderSubmissionResponse,
    OrderSubmissionStatus,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.insert_ord.return_value = 1001
    state.insert_ord_detail.return_value = None
    state.insert_ord_pp_map.return_value = None
    state.insert_ord_txn.return_value = None
    state.insert_ord_stat.return_value = None
    state.get_ord_with_latest_stat.return_value = None
    return state


@pytest.fixture
def mock_bridge():
    bridge = MagicMock()
    bridge.publish.return_value = None
    return bridge


@pytest.fixture
def real_order_manager(mock_state, mock_bridge):
    """실제 OrderManagerImpl (State/Bridge 만 mock) — 내부 로직 검증용."""
    return OrderManagerImpl(state_manager=mock_state, event_bridge=mock_bridge)


@pytest.fixture
def mock_order_manager():
    """OrderManager 전체 mock — OrderingService 만 검증할 때 사용."""
    om = MagicMock()
    om.create_order.return_value = OrderRecord(
        ord_id=1001,
        user_id=1,
        latest_stat=OrdStat.RCVD,
        created_at=datetime(2026, 4, 22, 10, 0),
    )
    om.get_order.return_value = None
    return om


@pytest.fixture
def user_validator_factory():
    """user_id 존재 여부 검증 함수 팩토리."""

    def _make(valid_ids: set[int]):
        return lambda uid: uid in valid_ids

    return _make


@pytest.fixture
def sample_detail() -> OrderDetailInput:
    return OrderDetailInput(
        prod_id=5,
        diameter=Decimal("600"),
        thickness=Decimal("40"),
        material="회주철",
        load_class="D400",
        qty=10,
        final_price=Decimal("1500000"),
        due_date=date(2026, 5, 1),
        ship_addr="서울시 강남구 테헤란로 123",
    )


@pytest.fixture
def sample_request(sample_detail) -> OrderSubmissionRequest:
    return OrderSubmissionRequest(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2, 3],
        idempotency_key=None,
    )


# ============================================================================
# Protocol 만족
# ============================================================================


def test_impl_satisfies_protocol(mock_order_manager):
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    assert isinstance(service, IOrderingService)


# ============================================================================
# Seq 1 — 주문 요청 Pydantic 스키마 검증
# ============================================================================


def test_seq1_missing_user_id_raises_validation_error():
    """Seq 1: user_id 누락 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        OrderSubmissionRequest(detail=OrderDetailInput(qty=10), pp_ids=[])  # type: ignore[call-arg]


def test_seq1_missing_detail_raises_validation_error():
    """Seq 1: detail 누락 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        OrderSubmissionRequest(user_id=1, pp_ids=[])  # type: ignore[call-arg]


def test_seq1_non_positive_user_id_raises_validation_error():
    """Seq 1: user_id <= 0 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        OrderSubmissionRequest(user_id=0, detail=OrderDetailInput(qty=10), pp_ids=[])


def test_seq1_non_positive_qty_raises_validation_error():
    """Seq 1: qty <= 0 → Pydantic ValidationError (OrderDetailInput 에서)."""
    with pytest.raises(ValidationError):
        OrderDetailInput(qty=0)


def test_seq1_valid_request_accepted(sample_request):
    """Seq 1: 올바른 요청 → ValidationError 없이 생성."""
    assert sample_request.user_id == 1
    assert sample_request.detail.qty == 10
    assert sample_request.pp_ids == [1, 2, 3]


# ============================================================================
# Seq 2 — user_id 인증 체크
# ============================================================================


def test_seq2_unauthorized_user_returns_401(
    mock_order_manager,
    user_validator_factory,
    sample_request,
):
    """Seq 2: user_validator 가 False → UNAUTHORIZED + http 401."""
    service = OrderingServiceImpl(
        order_manager=mock_order_manager,
        user_validator=user_validator_factory({99}),  # user_id=1 은 허용 안 됨
    )
    response = service.submit_order(sample_request)

    assert response.status == OrderSubmissionStatus.UNAUTHORIZED
    assert response.http_code == 401
    assert response.ord_id is None
    # OrderManager 호출 안 됨 (조기 반환)
    mock_order_manager.create_order.assert_not_called()


def test_seq2_authorized_user_passes(
    mock_order_manager,
    user_validator_factory,
    sample_request,
):
    """Seq 2: user_validator 가 True → 다음 단계로 진행."""
    service = OrderingServiceImpl(
        order_manager=mock_order_manager,
        user_validator=user_validator_factory({1}),  # user_id=1 허용
    )
    response = service.submit_order(sample_request)

    assert response.status == OrderSubmissionStatus.ACCEPTED
    mock_order_manager.create_order.assert_called_once()


def test_seq2_no_validator_means_skip_auth(
    mock_order_manager,
    sample_request,
):
    """Seq 2: user_validator=None → 인증 검증 건너뜀 (dev/테스트 환경)."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)  # validator 미지정
    response = service.submit_order(sample_request)
    assert response.status == OrderSubmissionStatus.ACCEPTED


# ============================================================================
# Seq 3 — 비즈니스 pre-check (pp_ids 중복 제거 등)
# ============================================================================


def test_seq3_pp_ids_duplicates_removed_before_delegation(
    mock_order_manager,
    sample_detail,
):
    """Seq 3: pp_ids 에 중복 있으면 OrderManager 로 넘기기 전에 제거."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    request = OrderSubmissionRequest(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2, 2, 3, 1],
    )
    service.submit_order(request)

    called_input: CreateOrderInput = mock_order_manager.create_order.call_args.args[0]
    assert called_input.pp_ids == [1, 2, 3]  # 중복 제거 + 순서 유지


def test_seq3_empty_pp_ids_preserved(mock_order_manager, sample_detail):
    """Seq 3: 빈 pp_ids 그대로 전달."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    service.submit_order(
        OrderSubmissionRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[],
        )
    )
    called_input: CreateOrderInput = mock_order_manager.create_order.call_args.args[0]
    assert called_input.pp_ids == []


# ============================================================================
# Seq 4 — OrderManager.create_order() 1회 위임
# ============================================================================


def test_seq4_delegates_to_order_manager_exactly_once(
    mock_order_manager,
    sample_request,
):
    """Seq 4: OrderManager.create_order() 1회 호출."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    service.submit_order(sample_request)
    mock_order_manager.create_order.assert_called_once()


def test_seq4_delegation_input_matches_request(
    mock_order_manager,
    sample_request,
):
    """Seq 4: 전달된 CreateOrderInput 이 요청과 동일 (pp_ids 중복 제거 고려)."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    service.submit_order(sample_request)

    called_input: CreateOrderInput = mock_order_manager.create_order.call_args.args[0]
    assert called_input.user_id == sample_request.user_id
    assert called_input.detail == sample_request.detail
    assert called_input.pp_ids == sample_request.pp_ids


# ============================================================================
# Seq 5 — DB 5개 테이블 INSERT (OrderManager 내부)
# ============================================================================


def test_seq5_db_inserts_all_5_tables_via_real_order_manager(
    real_order_manager,
    mock_state,
    sample_request,
):
    """Seq 5: OrderingService → 실제 OrderManager → mock State 의 5테이블 INSERT 확인."""
    service = OrderingServiceImpl(order_manager=real_order_manager)
    response = service.submit_order(sample_request)

    assert response.status == OrderSubmissionStatus.ACCEPTED
    assert mock_state.insert_ord.call_count == 1
    assert mock_state.insert_ord_detail.call_count == 1
    assert mock_state.insert_ord_pp_map.call_count == 3  # pp_ids 3개
    assert mock_state.insert_ord_txn.call_count == 1
    assert mock_state.insert_ord_stat.call_count == 1


# ============================================================================
# Seq 6 — ORDER_CREATED 이벤트 발행 (OrderManager 내부)
# ============================================================================


def test_seq6_order_created_event_published(
    real_order_manager,
    mock_bridge,
    sample_request,
):
    """Seq 6: ORDER_CREATED 이벤트가 EventBridge 로 1회 발행됨."""
    service = OrderingServiceImpl(order_manager=real_order_manager)
    service.submit_order(sample_request)

    assert mock_bridge.publish.call_count == 1
    event: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert event.event_type == OrderEventType.ORDER_CREATED
    assert event.ord_id == 1001
    assert event.user_id == 1


# ============================================================================
# Seq 7 — OrderSubmissionResponse 반환 (ACCEPTED + http 201 + ord_id)
# ============================================================================


def test_seq7_accepted_response_http_201(
    mock_order_manager,
    sample_request,
):
    """Seq 7: 성공 응답 = ACCEPTED + http 201 + ord_id."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.submit_order(sample_request)

    assert isinstance(response, OrderSubmissionResponse)
    assert response.status == OrderSubmissionStatus.ACCEPTED
    assert response.http_code == 201
    assert response.ord_id == 1001
    assert response.user_id == 1
    assert response.latest_stat == OrdStat.RCVD


def test_seq7_message_is_human_readable(
    mock_order_manager,
    sample_request,
):
    """Seq 7: 메시지가 사용자에게 의미 있음."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.submit_order(sample_request)
    assert "accepted" in response.message.lower()


# ============================================================================
# Seq 8 — Idempotency 중복 요청 처리
# ============================================================================


def test_seq8_idempotent_second_call_returns_duplicate(
    mock_order_manager,
    sample_detail,
):
    """Seq 8: 동일 idempotency_key 로 두 번 호출 → 두 번째는 DUPLICATE + http 200."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    request = OrderSubmissionRequest(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2],
        idempotency_key="abc-xyz-123",
    )

    first = service.submit_order(request)
    second = service.submit_order(request)

    assert first.status == OrderSubmissionStatus.ACCEPTED
    assert first.http_code == 201
    assert second.status == OrderSubmissionStatus.DUPLICATE
    assert second.http_code == 200
    assert second.ord_id == first.ord_id  # 동일한 ord_id 반환

    # OrderManager 는 1회만 호출됨 (중복은 캐시에서 반환)
    assert mock_order_manager.create_order.call_count == 1


def test_seq8_different_idempotency_keys_both_process(
    mock_order_manager,
    sample_detail,
):
    """Seq 8: 서로 다른 idempotency_key → 각각 처리."""
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    r1 = service.submit_order(
        OrderSubmissionRequest(
            user_id=1,
            detail=sample_detail,
            idempotency_key="key-1",
        )
    )
    r2 = service.submit_order(
        OrderSubmissionRequest(
            user_id=1,
            detail=sample_detail,
            idempotency_key="key-2",
        )
    )
    assert r1.status == OrderSubmissionStatus.ACCEPTED
    assert r2.status == OrderSubmissionStatus.ACCEPTED
    assert mock_order_manager.create_order.call_count == 2


# ============================================================================
# Seq 9 — 내부 예외 → HTTP 에러 매핑
# ============================================================================


def test_seq9_db_failure_maps_to_service_err_503(
    mock_order_manager,
    sample_request,
):
    """Seq 9: OrderManager 에서 비즈니스 오류 아닌 일반 예외 → SERVICE_ERR + 503."""
    mock_order_manager.create_order.side_effect = RuntimeError("DB connection lost")
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.submit_order(sample_request)

    assert response.status == OrderSubmissionStatus.SERVICE_ERR
    assert response.http_code == 503
    assert "DB connection lost" in response.message


def test_seq9_value_error_maps_to_validation_err_400(
    mock_order_manager,
    sample_request,
):
    """Seq 9: OrderManager 에서 ValueError (도메인 검증) → VALIDATION_ERR + 400."""
    mock_order_manager.create_order.side_effect = ValueError("invalid domain rule")
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.submit_order(sample_request)

    assert response.status == OrderSubmissionStatus.VALIDATION_ERR
    assert response.http_code == 400


def test_seq9_service_never_raises_even_on_failure(
    mock_order_manager,
    sample_request,
):
    """Seq 9: 어떤 경우에도 OrderingService 자체가 raise 하지 않음."""
    mock_order_manager.create_order.side_effect = Exception("arbitrary error")
    service = OrderingServiceImpl(order_manager=mock_order_manager)

    # 예외가 전파되지 않고 response 로 매핑되어야 함
    try:
        response = service.submit_order(sample_request)
        assert response.status == OrderSubmissionStatus.SERVICE_ERR
    except Exception:
        pytest.fail("OrderingService 가 예외를 전파했습니다 — HTTP 어댑터 안정성 위반")


# ============================================================================
# Seq 10 — query_order 읽기 경로
# ============================================================================


def test_seq10_query_existing_order_returns_record(
    mock_order_manager,
    sample_detail,
):
    """Seq 10: 존재하는 ord_id 조회 → ACCEPTED + latest_stat 포함."""
    mock_order_manager.get_order.return_value = OrderRecord(
        ord_id=1001,
        user_id=1,
        latest_stat=OrdStat.APPR,
        detail=sample_detail,
    )
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.query_order(ord_id=1001, user_id=1)

    assert response.status == OrderSubmissionStatus.ACCEPTED
    assert response.http_code == 201  # ACCEPTED 매핑
    assert response.ord_id == 1001
    assert response.latest_stat == OrdStat.APPR


def test_seq10_query_nonexistent_order_returns_validation_err(mock_order_manager):
    """Seq 10: 존재하지 않는 ord_id → VALIDATION_ERR + 400."""
    mock_order_manager.get_order.return_value = None
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.query_order(ord_id=999, user_id=1)

    assert response.status == OrderSubmissionStatus.VALIDATION_ERR
    assert response.http_code == 400


def test_seq10_query_other_user_order_returns_unauthorized(
    mock_order_manager,
    sample_detail,
):
    """Seq 10: 타인 주문 조회 시 → UNAUTHORIZED + 401."""
    mock_order_manager.get_order.return_value = OrderRecord(
        ord_id=1001,
        user_id=2,
        latest_stat=OrdStat.RCVD,
        detail=sample_detail,
    )
    service = OrderingServiceImpl(order_manager=mock_order_manager)
    response = service.query_order(ord_id=1001, user_id=1)  # 다른 유저

    assert response.status == OrderSubmissionStatus.UNAUTHORIZED
    assert response.http_code == 401


# ============================================================================
# HTTP_STATUS_MAP 완전성
# ============================================================================


def test_all_statuses_have_http_mapping():
    """모든 OrderSubmissionStatus 에 HTTP code 매핑 존재."""
    for status in OrderSubmissionStatus:
        assert status in HTTP_STATUS_MAP
        assert 200 <= HTTP_STATUS_MAP[status] <= 599
