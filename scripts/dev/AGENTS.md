<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# scripts

프로젝트 스크립트 — Confluence 동기화, RC522 회귀 테스트.

## Key Files

| File | Description |
|------|-------------|
| `sync_confluence_facts.py` | Confluence v2 API → `docs/CONFLUENCE_FACTS.md` 자동 동기화 (stdlib only) |
| `test_rc522_regression.py` | RC522 RFID 안정성 회귀 테스트 스위트 (99%, 70 tests) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `tests/` | Conftest + regression test mirrors |

## For AI Agents

### Working In This Directory
- `python scripts/sync_confluence_facts.py` — 수동 동기화
- `python scripts/sync_confluence_facts.py --dry-run` — 변경 감지만
- `python scripts/test_rc522_regression.py` — RC522 회귀 테스트 실행
- launchd: 매일 09:07 자동 실행 (`~/Library/LaunchAgents/com.casting-factory.confluence-sync.plist`)
- 인증: macOS Keychain (`service=casting-factory-atlassian`)

### Common Patterns
- Confluence READ-ONLY — PUT/POST/DELETE 금지 (사용자 명시 허락 시만)
- sync 스크립트는 stdlib만 사용 (requests 미사용)
- `<!-- CURATED:START -->` / `<!-- CURATED:END -->` 마커로 수기 블록 보존

## Dependencies

### External
- stdlib only (sync_confluence_facts.py)
- pytest (test_rc522_regression.py)
