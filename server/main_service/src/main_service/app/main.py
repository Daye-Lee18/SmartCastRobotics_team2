import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.clients.management import ManagementClient
from smart_cast_db.database import Base, SessionLocal, engine
from app.routes import (
    alerts,
    auth,
    dashboard,
    logistics,
    management,
    orders,
    production,
    quality,
    schedule,
    websocket,
)
from app.seed import seed_database

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # smartcast schema (Confluence 32342045 v59) 정착.
    # DDL 은 backend/scripts/create_tables_v2.sql 로 사전 적용됨 — create_all 은 보조.
    # search_path=smartcast,public 옵션이 DATABASE_URL 에 포함되어 있어 ORM 이 자동 사용.
    #
    # NOTE: V6 canonical 아키텍처에 맞춰 Phase B 에서 FMS 자동 진행 시퀀서와 ROS2 publisher 는
    # Management Service (backend/management/server.py) 로 이관됨. Interface Service 는
    # Admin/Customer PC 의 HTTP 요청만 처리하고 DB 조회/쓰기 책임만 가진다.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield

    # Phase C-1: Management gRPC 채널 싱글톤 정리 (open 된 경우만)
    try:
        ManagementClient.get().close()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(
    title="주물공장 관제 API",
    description="Casting factory dashboard REST API and WebSocket service",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for development with the Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routers
app.include_router(orders.router)
app.include_router(orders.products_router)
app.include_router(orders.load_classes_router)
app.include_router(production.router)
app.include_router(quality.router)
app.include_router(logistics.router)
app.include_router(alerts.router)
app.include_router(schedule.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
# V6 canonical Phase 4 (Phase C-1): Interface → Management gRPC proxy
app.include_router(management.router)

# WebSocket router
app.include_router(websocket.router)

# Dev-only debug router (SPEC-AMR-001 FR-AMR-01-07)
# APP_ENV=development 이 아니면 등록하지 않음 → production 에서 404 반환
if os.environ.get("APP_ENV", "development").lower() == "development":
    from app.routes import debug  # noqa: E402  지연 import: dev 환경에서만 로드

    app.include_router(debug.router)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "ok", "service": "casting-factory-api"}
