"""Management Service gRPC proxy routes (V6 canonical Phase 4 · Phase C-1).

Admin/Customer PC 의 HTTP 요청 중 Management Service 직결이 필요한 엔드포인트를
이 라우터에 모은다. 이미지상 Interface↓Management 화살표를 실체화한다.

Phase C-1 범위:
  GET /api/management/health   Management gRPC 헬스체크 proxy

Phase C-2 예정 (smartcast v2 스키마 정합 후):
  POST /api/management/production/start   StartProduction RPC proxy
  GET  /api/management/items               ListItems RPC proxy
  WS   /api/management/items/stream        WatchItems stream proxy
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.management import (
    ManagementClient,
    ManagementUnavailable,
    get_management_client,
)

router = APIRouter(prefix="/api/management", tags=["management"])


@router.get("/health")
def management_health(
    client: ManagementClient = Depends(get_management_client),
) -> dict:
    """Management Service gRPC(:50051) 연결 확인.

    반환:
      200 OK  {"status": "ok", "grpc": "host:port"}
      503     Management 미가동 또는 proto stubs 미컴파일.
    """
    try:
        client.health()
    except ManagementUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Management Service unavailable: {exc}",
        ) from exc
    return {"status": "ok", "service": "management", "grpc": client.endpoint}
