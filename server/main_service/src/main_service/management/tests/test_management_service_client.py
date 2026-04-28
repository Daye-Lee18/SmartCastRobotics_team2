"""ManagementServiceClient 단위 테스트.

검증 대상:
  - Interface Service → Management Service (gRPC :50051) 어댑터
  - OrderManager mock 으로 내부 도메인 의존성 분리
  - 성공 / ValueError / ConnectionError / 일반 예외 경로 커버

대응 구현: backend/management/services/management_service_client.py
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from services.management_service_client import (
    IManagementServiceClient,
    ManagementCallStatus,
    ManagementOrderRequest,
    ManagementOrderResponse,
    ManagementServiceClientImpl,
)
from services.order_manager import (
    CreateOrderInput,
    OrderDetailInput,
    OrderRecord,
    OrdStat,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_detail() -> OrderDetailInput:
    return OrderDetailInput(
        prod_id=5,
        diameter=Decimal("600"),
        thickness=Decimal("40"),
        material="회주철",
        load_class="D400",
        qty=10,
    )


@pytest.fixture
def mock_order_manager():
    om = MagicMock()
    om.create_order.return_value = OrderRecord(
        ord_id=2001,
        user_id=1,
        created_at=datetime(2026, 4, 23, 10, 0),
        latest_stat=OrdStat.RCVD,
        detail=OrderDetailInput(
            prod_id=5,
            diameter=Decimal("600"),
            thickness=Decimal("40"),
            material="회주철",
            load_class="D400",
            qty=10,
        ),
    )
    return om


@pytest.fixture
def client(mock_order_manager) -> ManagementServiceClientImpl:
    return ManagementServiceClientImpl(order_manager=mock_order_manager)


@pytest.fixture
def sample_request(sample_detail) -> ManagementOrderRequest:
    return ManagementOrderRequest(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2],
        idempotency_key="mgmt-key-001",
    )


# ============================================================================
# Protocol 만족
# ============================================================================


def test_impl_satisfies_protocol(client):
    assert isinstance(client, IManagementServiceClient)


# ============================================================================
# submit_order — 성공 경로
# ============================================================================


def test_submit_order_ok_returns_OK_status(client, sample_request):
    response = client.submit_order(sample_request)
    assert response.status == ManagementCallStatus.OK
    assert response.ord_id == 2001
    assert response.user_id == 1
    assert response.latest_stat == OrdStat.RCVD
    assert response.message == "order persisted"


def test_submit_order_delegates_to_order_manager(client, sample_request, mock_order_manager):
    client.submit_order(sample_request)
    mock_order_manager.create_order.assert_called_once()

    called_input: CreateOrderInput = mock_order_manager.create_order.call_args.args[0]
    assert called_input.user_id == 1
    assert called_input.pp_ids == [1, 2]
    assert called_input.detail == sample_request.detail


def test_submit_order_propagates_detail_fields(client, sample_request, mock_order_manager):
    client.submit_order(sample_request)
    called_input: CreateOrderInput = mock_order_manager.create_order.call_args.args[0]
    assert called_input.detail.qty == 10
    assert called_input.detail.material == "회주철"
    assert called_input.detail.load_class == "D400"


# ============================================================================
# submit_order — ValueError (도메인 검증 실패)
# ============================================================================


def test_submit_order_value_error_returns_INVALID(client, sample_request, mock_order_manager):
    mock_order_manager.create_order.side_effect = ValueError("qty must be > 0")
    response = client.submit_order(sample_request)

    assert response.status == ManagementCallStatus.INVALID
    assert "qty must be > 0" in response.message
    assert response.ord_id is None


def test_submit_order_value_error_with_empty_pp_ids(mock_order_manager):
    mock_order_manager.create_order.side_effect = ValueError("invalid input")
    client = ManagementServiceClientImpl(order_manager=mock_order_manager)
    req = ManagementOrderRequest(user_id=1, detail=OrderDetailInput(qty=5))
    response = client.submit_order(req)
    assert response.status == ManagementCallStatus.INVALID


# ============================================================================
# submit_order — ConnectionError (gRPC 연결 불가)
# ============================================================================


def test_submit_order_connection_error_returns_UNAVAILABLE(
    client,
    sample_request,
    mock_order_manager,
):
    mock_order_manager.create_order.side_effect = ConnectionError("channel closed")
    response = client.submit_order(sample_request)

    assert response.status == ManagementCallStatus.UNAVAILABLE
    assert "channel closed" in response.message
    assert response.ord_id is None


def test_submit_order_connection_refused(client, sample_request, mock_order_manager):
    mock_order_manager.create_order.side_effect = ConnectionRefusedError("gRPC :50051 refused")
    response = client.submit_order(sample_request)
    assert response.status == ManagementCallStatus.UNAVAILABLE


# ============================================================================
# submit_order — 일반 예외 (gRPC 오류 등)
# ============================================================================


def test_submit_order_generic_exception_returns_GRPC_ERROR(
    client,
    sample_request,
    mock_order_manager,
):
    mock_order_manager.create_order.side_effect = RuntimeError("internal failure")
    response = client.submit_order(sample_request)

    assert response.status == ManagementCallStatus.GRPC_ERROR
    assert "internal failure" in response.message
    assert response.ord_id is None


def test_submit_order_exception_never_propagates(client, sample_request, mock_order_manager):
    mock_order_manager.create_order.side_effect = Exception("arbitrary error")
    response = client.submit_order(sample_request)

    assert response.status == ManagementCallStatus.GRPC_ERROR
    assert response.ord_id is None


# ============================================================================
# Pydantic 스키마 검증
# ============================================================================


def test_request_rejects_non_positive_user_id():
    with pytest.raises(Exception):  # noqa: B017
        ManagementOrderRequest(user_id=0, detail=OrderDetailInput(qty=1))


def test_request_rejects_missing_detail():
    with pytest.raises(Exception):  # noqa: B017
        ManagementOrderRequest(user_id=1)  # type: ignore[call-arg]


def test_request_accepts_empty_pp_ids():
    req = ManagementOrderRequest(user_id=1, detail=OrderDetailInput(qty=5))
    assert req.pp_ids == []


def test_response_default_values():
    resp = ManagementOrderResponse(status=ManagementCallStatus.OK)
    assert resp.ord_id is None
    assert resp.user_id is None
    assert resp.latest_stat is None
    assert resp.message == ""


# ============================================================================
# 모든 ManagementCallStatus 매핑 확인
# ============================================================================


def test_all_call_statuses_are_distinct():
    values = [s.value for s in ManagementCallStatus]
    assert len(values) == len(set(values))
