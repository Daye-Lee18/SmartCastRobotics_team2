"""4-Sequence Pipeline Test (Sprint 5 Seq 1~4).

Seq 1: 고객 → Ordering Service            (상품 주문)
Seq 2: Ordering Service → Interface Service (주문 생성)
Seq 3: Interface Service → Management Service (주문 처리 요청)
Seq 4: Management Service → DB Service     (주문 정보 저장)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from services.interface_service_client import (
    InterfaceForwardRequest,
    InterfaceForwardStatus,
    InterfaceServiceClientImpl,
)
from services.management_service_client import (
    ManagementCallStatus,
    ManagementOrderRequest,
    ManagementServiceClientImpl,
)
from services.order_manager import (
    OrderDetailInput,
    OrderManagerImpl,
    OrderRecord,
    OrdStat,
)
from services.ordering_service import (
    OrderingServiceImpl,
    OrderSubmissionRequest,
    OrderSubmissionStatus,
)

# ============================================================================
# Fixtures (공통)
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
        final_price=Decimal("1500000"),
        due_date=date(2026, 5, 1),
        ship_addr="서울시 강남구 테헤란로 123",
    )


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.insert_ord.return_value = 1001
    return state


@pytest.fixture
def mock_bridge():
    return MagicMock()


@pytest.fixture
def real_order_manager(mock_state, mock_bridge):
    return OrderManagerImpl(state_manager=mock_state, event_bridge=mock_bridge)


# ============================================================================
# Seq 1 — 고객 → Ordering Service (상품 주문)
# ============================================================================


def test_seq1_customer_to_ordering_service(sample_detail):
    """Seq 1: 고객이 OrderSubmissionRequest 를 OrderingService 에 제출."""
    mock_om = MagicMock()
    mock_om.create_order.return_value = OrderRecord(
        ord_id=1001,
        user_id=1,
        latest_stat=OrdStat.RCVD,
    )
    service = OrderingServiceImpl(order_manager=mock_om)

    response = service.submit_order(
        OrderSubmissionRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[1, 2, 3],
        )
    )

    # Seq 1 검증: Ordering Service 가 요청을 받고 정상 응답
    assert response.status == OrderSubmissionStatus.ACCEPTED
    assert response.http_code == 201
    assert response.ord_id == 1001
    mock_om.create_order.assert_called_once()


# ============================================================================
# Seq 2 — Ordering Service → Interface Service (주문 생성)
# ============================================================================


def test_seq2_ordering_to_interface_service(sample_detail):
    """Seq 2: InterfaceServiceClient 가 HTTP POST /api/orders 로 전달."""
    # http_transport mock: Interface 가 201 로 응답
    mock_transport = MagicMock(
        return_value=(
            201,
            {
                "ord_id": 1001,
                "latest_stat": "RCVD",
            },
        )
    )
    client = InterfaceServiceClientImpl(
        base_url="http://localhost:8000",
        http_transport=mock_transport,
    )

    response = client.forward_create_order(
        InterfaceForwardRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[1, 2, 3],
        )
    )

    # Seq 2 검증
    assert response.status == InterfaceForwardStatus.OK
    assert response.http_code == 201
    assert response.ord_id == 1001
    assert response.latest_stat == OrdStat.RCVD
    # HTTP POST 가 정확히 1회 호출되고 URL/body 검증
    mock_transport.assert_called_once()
    url, body = mock_transport.call_args.args
    assert url == "http://localhost:8000/api/orders"
    assert body["user_id"] == 1
    assert body["pp_ids"] == [1, 2, 3]


def test_seq2_interface_http_error_mapped(sample_detail):
    """Seq 2: Interface 가 4xx/5xx → HTTP_ERROR 상태로 매핑."""
    mock_transport = MagicMock(return_value=(500, {"detail": "DB down"}))
    client = InterfaceServiceClientImpl(
        base_url="http://localhost:8000",
        http_transport=mock_transport,
    )
    response = client.forward_create_order(
        InterfaceForwardRequest(
            user_id=1,
            detail=sample_detail,
        )
    )
    assert response.status == InterfaceForwardStatus.HTTP_ERROR
    assert response.http_code == 500


def test_seq2_interface_timeout_mapped(sample_detail):
    """Seq 2: Transport 가 TimeoutError → TIMEOUT 상태로 매핑."""

    def raise_timeout(url, body):
        raise TimeoutError("slow")

    client = InterfaceServiceClientImpl(
        base_url="http://localhost:8000",
        http_transport=raise_timeout,
    )
    response = client.forward_create_order(
        InterfaceForwardRequest(
            user_id=1,
            detail=sample_detail,
        )
    )
    assert response.status == InterfaceForwardStatus.TIMEOUT
    assert response.http_code == 504


# ============================================================================
# Seq 3 — Interface Service → Management Service (주문 처리 요청)
# ============================================================================


def test_seq3_interface_to_management_service(sample_detail):
    """Seq 3: ManagementServiceClient 가 gRPC 로 OrderManager 호출."""
    mock_om = MagicMock()
    mock_om.create_order.return_value = OrderRecord(
        ord_id=1001,
        user_id=1,
        latest_stat=OrdStat.RCVD,
    )
    client = ManagementServiceClientImpl(order_manager=mock_om)

    response = client.submit_order(
        ManagementOrderRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[1, 2, 3],
        )
    )

    # Seq 3 검증
    assert response.status == ManagementCallStatus.OK
    assert response.ord_id == 1001
    assert response.latest_stat == OrdStat.RCVD
    mock_om.create_order.assert_called_once()


def test_seq3_management_grpc_error_mapped(sample_detail):
    """Seq 3: gRPC 실패 → GRPC_ERROR."""
    mock_om = MagicMock()
    mock_om.create_order.side_effect = RuntimeError("grpc channel broken")
    client = ManagementServiceClientImpl(order_manager=mock_om)
    response = client.submit_order(
        ManagementOrderRequest(
            user_id=1,
            detail=sample_detail,
        )
    )
    assert response.status == ManagementCallStatus.GRPC_ERROR


def test_seq3_management_unavailable_mapped(sample_detail):
    """Seq 3: ConnectionError → UNAVAILABLE."""
    mock_om = MagicMock()
    mock_om.create_order.side_effect = ConnectionError("refused")
    client = ManagementServiceClientImpl(order_manager=mock_om)
    response = client.submit_order(
        ManagementOrderRequest(
            user_id=1,
            detail=sample_detail,
        )
    )
    assert response.status == ManagementCallStatus.UNAVAILABLE


# ============================================================================
# Seq 4 — Management Service → DB Service (주문 정보 저장)
# ============================================================================


def test_seq4_management_to_db_service_5_tables(
    real_order_manager,
    mock_state,
    mock_bridge,
    sample_detail,
):
    """Seq 4: OrderManager → StateManager 로 DB 5테이블 INSERT."""
    client = ManagementServiceClientImpl(order_manager=real_order_manager)
    response = client.submit_order(
        ManagementOrderRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[1, 2, 3],
        )
    )

    # Seq 4 검증
    assert response.status == ManagementCallStatus.OK
    assert response.ord_id == 1001
    assert mock_state.insert_ord.call_count == 1
    assert mock_state.insert_ord_detail.call_count == 1
    assert mock_state.insert_ord_pp_map.call_count == 3
    assert mock_state.insert_ord_txn.call_count == 1
    assert mock_state.insert_ord_stat.call_count == 1
    # 이벤트도 같이 발행됨
    assert mock_bridge.publish.call_count == 1


# ============================================================================
# End-to-End (Seq 1~4 체인)
# ============================================================================


def test_seq_1_to_4_end_to_end_chain(
    real_order_manager,
    mock_state,
    mock_bridge,
    sample_detail,
):
    """
    Seq 1~4 한 번에 체인 실행:
      고객 요청 → Ordering → Interface (mock HTTP) → Management → DB
    """
    # 가장 안쪽: Management ← OrderManager (실제)
    mgmt_client = ManagementServiceClientImpl(order_manager=real_order_manager)

    # Interface Service 의 POST /api/orders 핸들러를 mock 으로 대체
    # (실제로는 FastAPI 라우트 핸들러가 mgmt_client.submit_order 를 호출)
    def interface_handler(url, body):
        mgmt_resp = mgmt_client.submit_order(ManagementOrderRequest(**body))
        if mgmt_resp.status == ManagementCallStatus.OK:
            return (
                201,
                {
                    "ord_id": mgmt_resp.ord_id,
                    "latest_stat": mgmt_resp.latest_stat.value,
                },
            )
        return (500, {"detail": mgmt_resp.message})

    # Ordering → Interface 클라이언트
    iface_client = InterfaceServiceClientImpl(
        base_url="http://localhost:8000",
        http_transport=interface_handler,
    )

    # OrderingService 가 Interface Client 를 이용하지 않는 구조인데
    # 여기선 직접 호출 체인 구성
    iface_response = iface_client.forward_create_order(
        InterfaceForwardRequest(
            user_id=1,
            detail=sample_detail,
            pp_ids=[1, 2, 3],
        )
    )

    # 전체 체인 검증
    assert iface_response.status == InterfaceForwardStatus.OK
    assert iface_response.ord_id == 1001
    assert mock_state.insert_ord.call_count == 1
    assert mock_bridge.publish.call_count == 1
