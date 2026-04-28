<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/app (Interface Service)

FastAPI Interface Service — HTTP REST API (:8000).
Admin/Customer PC용, Next.js 프론트엔드와 통신.

## Key Files

| File | Description |
|------|-------------|
| `main.py` | FastAPI entry point — CORS, router registration, lifespan (DB seed, gRPC channel cleanup) |
| `database.py` | PostgreSQL async engine + session factory (TimescaleDB, SQLite 제거) |
| `seed.py` | smartcast v2 마스터 데이터 시딩 (idempotent: category, zone, equip, users...) |
| `seed_legacy.py` | Legacy mock data 시딩 (200+ orders/items for dev) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `clients/` | gRPC client for Management Service |
| `constants/` | Production workflow constants (RA task states, step delays) |
| `models/` | SQLAlchemy ORM models (smartcast v2 + management tables) |
| `routes/` | FastAPI route handlers (smartcast v2 + legacy) |
| `schemas/` | Pydantic v2 request/response schemas |
| `services/` | TimescaleDB detection helper |

## For AI Agents

### Working In This Directory
- `uvicorn backend.app.main:app --reload --port 8000`
- DB: `100.107.120.14:5432/smartcast_robotics`
- DATABASE_URL 미설정 시 fail-fast

### Testing Requirements
- `python -m pytest backend/app/`

### Common Patterns
- 라우트: smartcast v2 (routes/*.py) + legacy (routes/legacy/*.py) 병존
- 스키마: Pydantic v2, Request/Response 쌍
- DB: SQLAlchemy async session, smartcast 스키마 27테이블
- `clients/management.py` 싱글톤 gRPC 채널로 Management Service 호출

## Dependencies

### Internal
- `backend/management/` — gRPC Management Service (via clients/management.py)
- `backend/app/models/` — ORM models shared with Management Service

### External
- FastAPI, uvicorn, SQLAlchemy, asyncpg, psycopg2
