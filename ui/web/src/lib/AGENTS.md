<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# src/lib

공유 유틸리티 — API 클라이언트, 타입 정의, 헬퍼 함수.

## Key Files

| File | Description |
|------|-------------|
| `api.ts` | API client — FastAPI backend 통신 (fetch wrapper) |
| `types.ts` | TypeScript type definitions — smartcast v2 27테이블 매핑 |
| `utils.ts` | 유틸리티 함수 (formatting, helpers) |
| `mock-data.ts` | 개발용 mock 데이터 |

## For AI Agents

### Working In This Directory
- `api.ts`: API_BASE 빈 문자열 사용 (Next.js rewrites/proxy)
- `types.ts`: 백엔드 Pydantic 스키마와 1:1 매칭 필요
- 새 엔드포인트 추가 시 types.ts + api.ts 동시 업데이트

### Common Patterns
- fetch 기반 API client
- 타입은 backend/app/schemas/schemas.py와 동기화
- mock-data.ts는 seed_legacy.py 데이터와 일치

## Dependencies

### Internal
- `backend/app/routes/` — API 엔드포인트
- `backend/app/schemas/` — Pydantic 스키마 (types.ts 소스)
