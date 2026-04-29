"""InterfaceServiceClient 단위 테스트.

검증 대상:
  - OrderingService → Interface Service (FastAPI :8000) HTTP 포워딩
  - http_transport mock 으로 외부 HTTP 의존성 분리
  - 성공 / HTTP 에러 / 타임아웃 / 일반 예외 경로 커버

대응 구현: backend/management/services/interface_service_client.py
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from services.interface_service_client import (
    IInterfaceServiceClient,
    InterfaceForwardRequest,
    InterfaceForwardResponse,
    InterfaceForwardStatus,
    InterfaceServiceClientImpl,
)
from services.order_manager import OrderDetailInput, OrdStat

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
def mock_transport():
    """http_transport mock — (http_code, json_body) 반환."""
    transport = MagicMock()
    transport.return_value = (
        201,
        {
            "ord_id": 1001,
            "latest_stat": "RCVD",
        },
    )
    return transport


@pytest.fixture
def client(mock_transport) -> InterfaceServiceClientImpl:
    return InterfaceServiceClientImpl(
        base_url="http://localhost:8000",
        http_transport=mock_transport,
    )


@pytest.fixture
def sample_request(sample_detail) -> InterfaceForwardRequest:
    return InterfaceForwardRequest(
        user_id=1,
        detail=sample_detail,
        pp_ids=[1, 2],
        idempotency_key="test-key-001",
    )


# ============================================================================
# Protocol 만족
# ============================================================================


def test_impl_satisfies_protocol(client):
    assert isinstance(client, IInterfaceServiceClient)


# ============================================================================
# forward_create_order — 성공 경로
# ============================================================================


def test_forward_ok_returns_OK_status(client, sample_request):
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.OK
    assert response.http_code == 201
    assert response.ord_id == 1001
    assert response.latest_stat == OrdStat.RCVD
    assert response.message == "forwarded ok"


def test_forward_ok_calls_transport_with_correct_url(client, sample_request, mock_transport):
    client.forward_create_order(sample_request)
    called_url = mock_transport.call_args.args[0]
    assert called_url == "http://localhost:8000/api/orders"


def test_forward_ok_passes_request_body(client, sample_request, mock_transport):
    client.forward_create_order(sample_request)
    called_body = mock_transport.call_args.args[1]
    assert called_body["user_id"] == 1
    assert called_body["pp_ids"] == [1, 2]
    assert called_body["idempotency_key"] == "test-key-001"


def test_forward_ok_without_latest_stat(client, sample_request, mock_transport):
    mock_transport.return_value = (201, {"ord_id": 42})
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.OK
    assert response.ord_id == 42
    assert response.latest_stat is None


# ============================================================================
# forward_create_order — HTTP 에러 경로 (4xx/5xx)
# ============================================================================


def test_forward_http_4xx_returns_HTTP_ERROR(client, sample_request, mock_transport):
    mock_transport.return_value = (400, {"detail": "bad request"})
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 400
    assert "bad request" in response.message


def test_forward_http_5xx_returns_HTTP_ERROR(client, sample_request, mock_transport):
    mock_transport.return_value = (500, {"detail": "internal error"})
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 500


def test_forward_http_error_with_non_dict_body(client, sample_request, mock_transport):
    mock_transport.return_value = (502, "plain text error")
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 502
    assert response.message == ""


# ============================================================================
# forward_create_order — TimeoutError
# ============================================================================


def test_forward_timeout_returns_TIMEOUT_status(client, sample_request, mock_transport):
    mock_transport.side_effect = TimeoutError("connection timed out")
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.TIMEOUT
    assert response.http_code == 504
    assert "timeout" in response.message.lower()


# ============================================================================
# forward_create_order — 일반 예외
# ============================================================================


def test_forward_generic_exception_returns_HTTP_ERROR(client, sample_request, mock_transport):
    mock_transport.side_effect = ConnectionRefusedError("refused")
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 502
    assert "refused" in response.message


def test_forward_runtime_exception_returns_HTTP_ERROR(client, sample_request, mock_transport):
    mock_transport.side_effect = RuntimeError("unexpected")
    response = client.forward_create_order(sample_request)
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 502


# ============================================================================
# base_url 슬래시 정규화
# ============================================================================


def test_trailing_slash_stripped_from_base_url(mock_transport):
    client = InterfaceServiceClientImpl(
        base_url="http://localhost:8000/",
        http_transport=mock_transport,
    )
    req = InterfaceForwardRequest(user_id=1, detail=OrderDetailInput(qty=1))
    client.forward_create_order(req)
    called_url = mock_transport.call_args.args[0]
    assert called_url == "http://localhost:8000/api/orders"
    assert "//api" not in called_url


# ============================================================================
# Pydantic 스키마 검증
# ============================================================================


def test_request_rejects_non_positive_user_id():
    with pytest.raises(Exception):  # noqa: B017
        InterfaceForwardRequest(user_id=0, detail=OrderDetailInput(qty=1))


def test_request_rejects_missing_detail():
    with pytest.raises(Exception):  # noqa: B017
        InterfaceForwardRequest(user_id=1)  # type: ignore[call-arg]


def test_response_default_values():
    resp = InterfaceForwardResponse(status=InterfaceForwardStatus.OK)
    assert resp.ord_id is None
    assert resp.latest_stat is None
    assert resp.http_code == 200
    assert resp.message == ""
