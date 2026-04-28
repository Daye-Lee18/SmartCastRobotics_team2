"""
ManagementServiceClient — Interface Service → Management Service (gRPC :50051) 어댑터.

Seq 3: Interface Service → Management Service (주문 처리 요청)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from services.order_manager import (
    CreateOrderInput,
    IOrderManager,
    OrderDetailInput,
    OrderRecord,
    OrdStat,
)

# ==============================================================================
# 2. ENUM
# ==============================================================================


class ManagementCallStatus(StrEnum):
    OK = "OK"
    GRPC_ERROR = "GRPC_ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


# ==============================================================================
# 3. DATATYPE
# ==============================================================================


class ManagementOrderRequest(BaseModel):
    """Interface Service → Management Service gRPC payload 에 대응."""

    user_id: int = Field(..., gt=0)
    detail: OrderDetailInput = Field(...)
    pp_ids: list[int] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None)


class ManagementOrderResponse(BaseModel):
    status: ManagementCallStatus
    ord_id: int | None = None
    user_id: int | None = None
    latest_stat: OrdStat | None = None
    message: str = ""


# ==============================================================================
# 4. INPUT / OUTPUT — Protocol
# ==============================================================================


@runtime_checkable
class IManagementServiceClient(Protocol):
    def submit_order(self, request: ManagementOrderRequest) -> ManagementOrderResponse: ...


# ==============================================================================
# 7. SIDE EFFECTS — 실제 구현
# ==============================================================================


class ManagementServiceClientImpl:
    """
    Interface Service (FastAPI :8000) 의 POST /api/orders 핸들러가 호출.
    내부에서 Management Service 의 OrderManager.create_order() 를 호출한다.

    Side Effects:
      - OrderManager.create_order() 1회 호출 (내부에서 DB INSERT + ORDER_CREATED 이벤트)
      - gRPC 실패 시 상태 매핑만, 예외 전파 안 함

    주입:
      order_manager: IOrderManager
        — Management Service 프로세스 내부의 OrderManagerImpl 인스턴스.
        테스트는 MagicMock.
    """

    def __init__(self, order_manager: IOrderManager) -> None:
        self._om = order_manager

    def submit_order(
        self,
        request: ManagementOrderRequest,
    ) -> ManagementOrderResponse:
        try:
            record: OrderRecord = self._om.create_order(
                CreateOrderInput(
                    user_id=request.user_id,
                    detail=request.detail,
                    pp_ids=request.pp_ids,
                )
            )
        except ValueError as e:
            return ManagementOrderResponse(
                status=ManagementCallStatus.INVALID,
                message=f"invalid: {e}",
            )
        except ConnectionError as e:
            return ManagementOrderResponse(
                status=ManagementCallStatus.UNAVAILABLE,
                message=f"mgmt unavailable: {e}",
            )
        except Exception as e:  # noqa: BLE001
            return ManagementOrderResponse(
                status=ManagementCallStatus.GRPC_ERROR,
                message=f"grpc error: {e}",
            )

        return ManagementOrderResponse(
            status=ManagementCallStatus.OK,
            ord_id=record.ord_id,
            user_id=record.user_id,
            latest_stat=record.latest_stat,
            message="order persisted",
        )
