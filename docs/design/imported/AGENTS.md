<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# docs

프로젝트 문서 — 아키텍처 다이어그램, SPEC, 배포 런북, 작업 로그.

## Key Files

| File | Description |
|------|-------------|
| `CONFLUENCE_FACTS.md` | Confluence 위키 22페이지 전량 수집본 (1035줄, 주 1회 재검증) |
| `management_service_design.md` | Management Service 설계 문서 |
| `DEPLOY-phase-a-to-c3.md` | Phase A~C3 배포 런북 |
| `SPEC-C2-schema-migration.md` | smartcast v2 스키마 마이그레이션 SPEC |
| `SETUP.md` | 프로젝트 설정 가이드 |
| `POSTGRES_MIGRATION.md` | PostgreSQL 마이그레이션 가이드 |
| `barcode_jetson_ready.md` | 바코드 Jetson 연동 상태 |
| `e2e_jetson_image_flow.md` | Jetson 이미지 E2E 플로우 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `architecture/` | 12개 컴포넌트 아키텍처 HTML (index + 01~12) |
| `testing/` | 테스트 관련 문서 (RC522 회귀 체크리스트) |
| `worklog/` | 개발 작업 로그 HTML (2026-04 날짜별) |

## For AI Agents

### Working In This Directory
- CONFLUENCE_FACTS.md는 전체 읽기 금지 (1035줄) — 목차로 섹션 찾아 부분 로드
- HTML 파일은 Mermaid/SVG 포함 — 브라우저로 확인
- Confluence 동기화는 `scripts/sync_confluence_facts.py` 담당

### Common Patterns
- 아키텍처 HTML: `_shared.css` 공용 스타일, Mermaid.js 다이어그램
- SPEC 문서: `.moai/specs/` 에 소스, docs/에 스키마/런북
- 작업 로그: 날짜별 HTML, index.html에서 링크

## Dependencies

### Internal
- `scripts/sync_confluence_facts.py` — CONFLUENCE_FACTS.md 갱신
