"""
InterfaceServiceClient — OrderingService → Interface Service (FastAPI :8000) 포워더.

Seq 2: Ordering Service → Interface Service (주문 생성)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from services.order_manager import OrderDetailInput, OrdStat

# ==============================================================================
# 2. ENUM
# ==============================================================================


class InterfaceForwardStatus(StrEnum):
    OK = "OK"
    HTTP_ERROR = "HTTP_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID = "INVALID"


# ==============================================================================
# 3. DATATYPE
# ==============================================================================


class InterfaceForwardRequest(BaseModel):
    """OrderingService → InterfaceService 로 넘기는 주문 생성 요청."""

    user_id: int = Field(..., gt=0)
    detail: OrderDetailInput = Field(...)
    pp_ids: list[int] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None, max_length=64)


class InterfaceForwardResponse(BaseModel):
    """InterfaceService 응답. Ordering 이 고객에게 돌려줄 바탕."""

    status: InterfaceForwardStatus
    ord_id: int | None = None
    latest_stat: OrdStat | None = None
    http_code: int = 200
    message: str = ""


# ==============================================================================
# 4. INPUT / OUTPUT — Protocol
# ==============================================================================


@runtime_checkable
class IInterfaceServiceClient(Protocol):
    def forward_create_order(
        self,
        request: InterfaceForwardRequest,
    ) -> InterfaceForwardResponse: ...


# ==============================================================================
# 7. SIDE EFFECTS — 실제 구현
# ==============================================================================


class InterfaceServiceClientImpl:
    """
    OrderingServiceImpl 이 고객 주문을 받으면 이 클라이언트를 통해
    Interface Service (FastAPI :8000) 의 POST /api/orders 로 전달한다.

    Side Effects:
      - HTTP POST /api/orders (http_transport.post() 호출)
      - 응답 코드에 따라 InterfaceForwardStatus 매핑
      - InterfaceService 가 내부적으로 Management Service gRPC 호출

    주입:
      http_transport: Callable[[str, dict], (int, dict)]
        — URL, body 를 받아 (http_code, json_body) 반환하는 함수.
        실제 구현은 httpx/requests, 테스트는 mock.
    """

    def __init__(self, base_url: str, http_transport) -> None:
        self._base_url = base_url.rstrip("/")
        self._post = http_transport

    def forward_create_order(
        self,
        request: InterfaceForwardRequest,
    ) -> InterfaceForwardResponse:
        url = f"{self._base_url}/api/orders"
        body = request.model_dump(mode="json")

        try:
            http_code, resp_body = self._post(url, body)
        except TimeoutError:
            return InterfaceForwardResponse(
                status=InterfaceForwardStatus.TIMEOUT,
                http_code=504,
                message="Interface Service timeout",
            )
        except Exception as e:  # noqa: BLE001
            return InterfaceForwardResponse(
                status=InterfaceForwardStatus.HTTP_ERROR,
                http_code=502,
                message=f"transport error: {e}",
            )

        if http_code >= 400:
            return InterfaceForwardResponse(
                status=InterfaceForwardStatus.HTTP_ERROR,
                http_code=http_code,
                message=resp_body.get("detail", "interface error")
                if isinstance(resp_body, dict)
                else "",
            )

        # OK
        return InterfaceForwardResponse(
            status=InterfaceForwardStatus.OK,
            ord_id=resp_body.get("ord_id"),
            latest_stat=OrdStat(resp_body["latest_stat"]) if resp_body.get("latest_stat") else None,
            http_code=http_code,
            message="forwarded ok",
        )
