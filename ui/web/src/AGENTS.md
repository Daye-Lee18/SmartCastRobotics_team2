<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# src

Next.js 16 App Router 프론트엔드 — 관리자 대시보드, 고객 포털, 생산 모니터링 UI.

## Key Files

| File | Description |
|------|-------------|
| `app/layout.tsx` | Root layout with providers, sidebar, global styles |
| `app/page.tsx` | Homepage/landing page |
| `app/globals.css` | Global CSS styles |
| `lib/api.ts` | API client — backend/app FastAPI 통신 |
| `lib/types.ts` | TypeScript type definitions (27 tables 매핑) |
| `lib/utils.ts` | Utility functions |
| `lib/mock-data.ts` | Mock data for development |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `app/` | Next.js App Router pages (see `app/AGENTS.md`) |
| `components/` | Reusable React components (see `components/AGENTS.md`) |
| `lib/` | Shared utilities, API client, types |

## For AI Agents

### Working In This Directory
- `pnpm dev` — dev server (port 3000)
- `pnpm build` — production build
- `pnpm lint` — ESLint
- API_BASE: 빈 문자열 사용 (proxy/rewrites)

### Testing Requirements
- `pnpm test` — Jest/Vitest
- `pnpm build` — type-check + build verification

### Common Patterns
- App Router (app/ directory) with server/client components
- `lib/api.ts` 로 FastAPI REST 호출
- `lib/types.ts` 에 백엔드 스키마 매핑
- 차트: recharts (components/charts/)

## Dependencies

### Internal
- `backend/app/` — REST API server
- `backend/management/` — gRPC (indirect, via Interface Service)

### External
- Next.js 16, React 19, TypeScript, Tailwind CSS
- recharts, lucide-react
