"""OrderManager 단위 테스트 (V모델 Sprint 5 / Sequence 1).

시나리오: 고객 상품 주문 → 주문 생성 → 주문 처리 요청 → DB 저장 까지.

검증 전략:
  - State Manager 는 MagicMock 으로 대체 (실제 DB 호출 없이 순수 로직 검증)
  - EventBridge 도 MagicMock 으로 대체
  - OrderManagerImpl 의 메소드 호출 순서·횟수·인자 검증
  - 42205202 계약 파일 섹션 6 (RESULT) 의 성공/실패 기준 전부 커버

대응 구현: backend/management/services/order_manager.py
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from services.order_manager import (
    CreateOrderInput,
    IOrderManager,
    OrderDetailInput,
    OrderEvent,
    OrderEventType,
    OrderManagerImpl,
    OrderRecord,
    OrdStat,
    OrdTxnType,
    ProcessOrderInput,
    validate_order_transition,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_state():
    """State Manager mock — insert_* / get_* 메소드 호출 검증용."""
    state = MagicMock()
    # insert_ord 는 새 ord_id (autoincrement) 를 반환한다고 가정
    state.insert_ord.return_value = 1001
    state.insert_ord_detail.return_value = None
    state.insert_ord_pp_map.return_value = None
    state.insert_ord_txn.return_value = None
    state.insert_ord_stat.return_value = None
    state.get_ord_with_latest_stat.return_value = None  # 기본: 존재하지 않음
    return state


@pytest.fixture
def mock_bridge():
    """EventBridge mock — publish 호출 검증용."""
    bridge = MagicMock()
    bridge.publish.return_value = None
    return bridge


@pytest.fixture
def om(mock_state, mock_bridge) -> OrderManagerImpl:
    """테스트 대상 OrderManagerImpl 인스턴스."""
    return OrderManagerImpl(state_manager=mock_state, event_bridge=mock_bridge)


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
def sample_create_input(sample_detail) -> CreateOrderInput:
    return CreateOrderInput(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2, 3],  # 3개 후처리 선택
    )


# ============================================================================
# A. Protocol 만족
# ============================================================================


def test_impl_satisfies_protocol(om):
    """OrderManagerImpl 은 IOrderManager Protocol 을 만족한다."""
    assert isinstance(om, IOrderManager)


# ============================================================================
# B. create_order 성공 기준 (계약 §6)
# ============================================================================


def test_create_order_returns_record_with_positive_ord_id(om, sample_create_input, mock_state):
    """create_order → OrderRecord.ord_id > 0."""
    mock_state.insert_ord.return_value = 42
    record = om.create_order(sample_create_input)
    assert isinstance(record, OrderRecord)
    assert record.ord_id == 42
    assert record.ord_id > 0


def test_create_order_initial_stat_is_RCVD(om, sample_create_input):
    """create_order 직후 latest_stat 은 RCVD."""
    record = om.create_order(sample_create_input)
    assert record.latest_stat == OrdStat.RCVD


def test_create_order_preserves_user_id(om, sample_create_input):
    """반환된 record 의 user_id 가 입력과 동일."""
    record = om.create_order(sample_create_input)
    assert record.user_id == sample_create_input.user_id


def test_create_order_inserts_ord_row(om, sample_create_input, mock_state):
    """ord 테이블에 1행 INSERT."""
    om.create_order(sample_create_input)
    mock_state.insert_ord.assert_called_once_with(user_id=1)


def test_create_order_inserts_ord_detail_row(om, sample_create_input, mock_state):
    """ord_detail 테이블에 1행 INSERT (input 의 detail 과 함께)."""
    om.create_order(sample_create_input)
    mock_state.insert_ord_detail.assert_called_once()
    call_kwargs = mock_state.insert_ord_detail.call_args.kwargs
    assert call_kwargs["ord_id"] == 1001
    assert call_kwargs["detail"] == sample_create_input.detail


def test_create_order_inserts_pp_map_rows_for_each_pp_id(om, sample_create_input, mock_state):
    """pp_ids 가 N개면 ord_pp_map 에 N행 INSERT."""
    om.create_order(sample_create_input)
    assert mock_state.insert_ord_pp_map.call_count == 3
    called_pp_ids = [c.kwargs["pp_id"] for c in mock_state.insert_ord_pp_map.call_args_list]
    assert called_pp_ids == [1, 2, 3]


def test_create_order_skips_pp_map_when_empty(om, sample_detail, mock_state):
    """pp_ids 빈 리스트면 ord_pp_map INSERT 0회."""
    data = CreateOrderInput(user_id=1, detail=sample_detail, pp_ids=[])
    om.create_order(data)
    mock_state.insert_ord_pp_map.assert_not_called()


def test_create_order_inserts_ord_txn_RCVD(om, sample_create_input, mock_state):
    """ord_txn 에 txn_type=RCVD 로 1행 INSERT."""
    om.create_order(sample_create_input)
    mock_state.insert_ord_txn.assert_called_once_with(ord_id=1001, txn_type=OrdTxnType.RCVD)


def test_create_order_inserts_ord_stat_RCVD(om, sample_create_input, mock_state):
    """ord_stat 에 ord_stat=RCVD 로 1행 INSERT."""
    om.create_order(sample_create_input)
    mock_state.insert_ord_stat.assert_called_once_with(
        ord_id=1001,
        user_id=1,
        ord_stat=OrdStat.RCVD,
    )


def test_create_order_publishes_ORDER_CREATED_event(om, sample_create_input, mock_bridge):
    """EventBridge.publish 가 ORDER_CREATED 1회 호출."""
    om.create_order(sample_create_input)
    mock_bridge.publish.assert_called_once()
    published_event: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert published_event.event_type == OrderEventType.ORDER_CREATED
    assert published_event.ord_id == 1001
    assert published_event.user_id == 1


def test_create_order_inserts_in_correct_sequence(om, sample_create_input, mock_state, mock_bridge):
    """호출 순서: ord → detail → pp_map × N → txn → stat → event publish."""
    om.create_order(sample_create_input)

    # 각 mock 의 호출 순서 확인
    ord_call_order = mock_state.insert_ord.call_count
    detail_call_order = mock_state.insert_ord_detail.call_count
    txn_call_order = mock_state.insert_ord_txn.call_count
    stat_call_order = mock_state.insert_ord_stat.call_count
    publish_call_order = mock_bridge.publish.call_count

    assert ord_call_order == 1
    assert detail_call_order == 1
    assert txn_call_order == 1
    assert stat_call_order == 1
    assert publish_call_order == 1


# ============================================================================
# C. create_order 실패 기준 (계약 §6)
# ============================================================================


def test_create_order_rejects_non_positive_user_id():
    """user_id <= 0 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        CreateOrderInput(
            user_id=0,
            detail=OrderDetailInput(qty=10),
            pp_ids=[],
        )


def test_create_order_rejects_non_positive_qty():
    """detail.qty <= 0 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        OrderDetailInput(qty=0)


def test_create_order_rejects_missing_detail():
    """detail 필드 누락 → Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        CreateOrderInput(user_id=1, pp_ids=[])  # type: ignore[call-arg]


def test_create_order_db_failure_does_not_publish_event(
    om, sample_create_input, mock_state, mock_bridge
):
    """DB INSERT 실패 시 이벤트 미발행 + 예외 전파."""
    mock_state.insert_ord.side_effect = RuntimeError("DB connection lost")
    with pytest.raises(RuntimeError, match="DB connection lost"):
        om.create_order(sample_create_input)
    mock_bridge.publish.assert_not_called()


# ============================================================================
# D. process_order 성공 기준 (계약 §6)
# ============================================================================


@pytest.fixture
def existing_order_record(sample_detail):
    """RCVD 상태 기존 주문 fixture."""
    return OrderRecord(
        ord_id=100,
        user_id=1,
        created_at=datetime(2026, 4, 22, 10, 0),
        latest_stat=OrdStat.RCVD,
        detail=sample_detail,
        pp_ids=[1, 2],
    )


def test_process_order_RCVD_to_APPR_publishes_ORDER_APPROVED(
    om,
    mock_state,
    mock_bridge,
    existing_order_record,
):
    """RCVD → APPR: ord_txn=APPR + ord_stat=APPR + ORDER_APPROVED 이벤트."""
    mock_state.get_ord_with_latest_stat.return_value = existing_order_record

    result = om.process_order(
        ProcessOrderInput(
            ord_id=100,
            new_stat=OrdStat.APPR,
            reviewer_id=5,
        )
    )

    assert result.latest_stat == OrdStat.APPR
    mock_state.insert_ord_txn.assert_called_once_with(ord_id=100, txn_type=OrdTxnType.APPR)
    mock_state.insert_ord_stat.assert_called_once_with(
        ord_id=100,
        user_id=5,
        ord_stat=OrdStat.APPR,
    )
    published: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert published.event_type == OrderEventType.ORDER_APPROVED
    assert published.reviewer_id == 5


def test_process_order_RCVD_to_REJT_publishes_ORDER_REJECTED(
    om,
    mock_state,
    mock_bridge,
    existing_order_record,
):
    """RCVD → REJT: 반려 이벤트 발행."""
    mock_state.get_ord_with_latest_stat.return_value = existing_order_record

    om.process_order(
        ProcessOrderInput(
            ord_id=100,
            new_stat=OrdStat.REJT,
            reviewer_id=5,
            reason="도면 불명확",
        )
    )

    published: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert published.event_type == OrderEventType.ORDER_REJECTED
    assert published.reason == "도면 불명확"


def test_process_order_RCVD_to_CNCL_publishes_ORDER_CANCELLED(
    om,
    mock_state,
    mock_bridge,
    existing_order_record,
):
    """RCVD → CNCL: 취소 이벤트 발행."""
    mock_state.get_ord_with_latest_stat.return_value = existing_order_record

    om.process_order(
        ProcessOrderInput(
            ord_id=100,
            new_stat=OrdStat.CNCL,
            reason="고객 요청",
        )
    )

    published: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert published.event_type == OrderEventType.ORDER_CANCELLED


# ============================================================================
# E. process_order 실패 기준 (계약 §6)
# ============================================================================


def test_process_order_invalid_transition_raises(om, mock_state, existing_order_record):
    """RCVD → MFG (skip) → ValueError."""
    mock_state.get_ord_with_latest_stat.return_value = existing_order_record
    with pytest.raises(ValueError, match="Invalid order transition"):
        om.process_order(ProcessOrderInput(ord_id=100, new_stat=OrdStat.MFG))


def test_process_order_reverse_transition_raises(om, mock_state, sample_detail):
    """APPR → RCVD (역방향) → ValueError."""
    appr_record = OrderRecord(
        ord_id=100,
        user_id=1,
        latest_stat=OrdStat.APPR,
        detail=sample_detail,
    )
    mock_state.get_ord_with_latest_stat.return_value = appr_record
    with pytest.raises(ValueError, match="Invalid order transition"):
        om.process_order(ProcessOrderInput(ord_id=100, new_stat=OrdStat.RCVD))


def test_process_order_nonexistent_ord_raises(om, mock_state):
    """존재하지 않는 ord_id → ValueError."""
    mock_state.get_ord_with_latest_stat.return_value = None
    with pytest.raises(ValueError, match="not found"):
        om.process_order(ProcessOrderInput(ord_id=999, new_stat=OrdStat.APPR))


# ============================================================================
# F. validate_order_transition 규칙 검증
# ============================================================================


def test_validate_transition_allows_RCVD_to_APPR():
    validate_order_transition(OrdStat.RCVD, OrdStat.APPR)  # no raise


def test_validate_transition_allows_full_happy_path():
    """RCVD → APPR → MFG → DONE → SHIP → COMP 모두 허용."""
    path = [OrdStat.RCVD, OrdStat.APPR, OrdStat.MFG, OrdStat.DONE, OrdStat.SHIP, OrdStat.COMP]
    for cur, nxt in zip(path, path[1:], strict=False):
        validate_order_transition(cur, nxt)


def test_validate_transition_blocks_terminal_states():
    """COMP / REJT / CNCL 에서 어느 상태로도 전이 불가."""
    for terminal in (OrdStat.COMP, OrdStat.REJT, OrdStat.CNCL):
        with pytest.raises(ValueError):
            validate_order_transition(terminal, OrdStat.MFG)


def test_validate_transition_blocks_skip_forward():
    """중간 단계 건너뛰기 불가."""
    with pytest.raises(ValueError):
        validate_order_transition(OrdStat.RCVD, OrdStat.MFG)
    with pytest.raises(ValueError):
        validate_order_transition(OrdStat.RCVD, OrdStat.SHIP)


# ============================================================================
# G. get_order
# ============================================================================


def test_get_order_returns_record_from_state_manager(om, mock_state, existing_order_record):
    """존재하는 ord_id → State Manager 가 반환한 record 그대로."""
    mock_state.get_ord_with_latest_stat.return_value = existing_order_record
    result = om.get_order(100)
    assert result is existing_order_record


def test_get_order_returns_None_when_not_exists(om, mock_state):
    """존재하지 않는 ord_id → None."""
    mock_state.get_ord_with_latest_stat.return_value = None
    assert om.get_order(999) is None


# ============================================================================
# H. V모델 Sprint 5 Sequence 1 통합 시나리오
# ============================================================================


def test_sprint5_sequence_1_end_to_end(om, mock_state, mock_bridge, sample_create_input):
    """
    [Sprint 5 Sequence 1] 고객 상품주문 → 주문 생성 → 주문 처리 요청 → DB 저장.

    Input:  CreateOrderInput(user_id=1, detail={prod=5, qty=10, ...}, pp_ids=[1,2,3])

    Expected Output:
      - OrderRecord(ord_id=1001, user_id=1, latest_stat=RCVD, ...)
      - ord 1행 INSERT
      - ord_detail 1행 INSERT
      - ord_pp_map 3행 INSERT
      - ord_txn 1행 INSERT (RCVD)
      - ord_stat 1행 INSERT (RCVD)
      - EventBridge.publish(ORDER_CREATED) 1회

    Result: PASS
    """
    result = om.create_order(sample_create_input)

    # 반환 record
    assert result.ord_id == 1001
    assert result.user_id == 1
    assert result.latest_stat == OrdStat.RCVD
    assert result.detail == sample_create_input.detail
    assert result.pp_ids == [1, 2, 3]

    # DB INSERT 횟수
    assert mock_state.insert_ord.call_count == 1
    assert mock_state.insert_ord_detail.call_count == 1
    assert mock_state.insert_ord_pp_map.call_count == 3
    assert mock_state.insert_ord_txn.call_count == 1
    assert mock_state.insert_ord_stat.call_count == 1

    # 이벤트 발행
    assert mock_bridge.publish.call_count == 1
    event: OrderEvent = mock_bridge.publish.call_args.args[0]
    assert event.event_type == OrderEventType.ORDER_CREATED
    assert event.ord_id == 1001
    assert event.user_id == 1
