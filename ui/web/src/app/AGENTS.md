<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# src/app

Next.js 16 App Router — 8개 라우트 (admin, customer, orders, production, quality).

## Key Files

| File | Description |
|------|-------------|
| `layout.tsx` | Root layout — providers, sidebar, global styles |
| `page.tsx` | Homepage/landing page |
| `globals.css` | Global CSS styles |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `admin/` | 관리자 대시보드 (dashboard, login) |
| `customer/` | 고객 포털 (lookup, orders) |
| `orders/` | 주문 관리 페이지 |
| `production/` | 생산 모니터링 페이지 |
| `quality/` | 품질 검사 페이지 |

## For AI Agents

### Working In This Directory
- App Router 패턴: 각 디렉토리의 `page.tsx`가 라우트
- `layout.tsx` 로 중첩 레이아웃 정의
- Server Components 기본, `"use client"` 필요시만 명시

### Common Patterns
- `lib/api.ts` 로 API 호출
- `lib/types.ts` 에 타입 정의
- admin 라우트: `AdminShell` 컴포넌트로 래핑
- customer 라우트: 별도 layout.tsx로 고객 전용 UI

## Dependencies

### Internal
- `src/lib/api.ts` — API client
- `src/lib/types.ts` — TypeScript types
- `src/components/` — 공유 컴포넌트
