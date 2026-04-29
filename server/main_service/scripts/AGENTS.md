<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/scripts

DB 스키마/마이그레이션 SQL 스크립트 + TimescaleDB 설치.

## Key Files

| File | Description |
|------|-------------|
| `create_tables_v2.sql` | smartcast v2 스키마 DDL (27 tables) |
| `seed_masters_v2.sql` | 마스터 데이터 시딩 SQL |
| `seed_realistic.sql` | 현실적 mock 데이터 (200+ orders/items) |
| `install_timescaledb.sh` | TimescaleDB 원격 서버 설치 |
| `install_timescaledb_local.sh` | TimescaleDB 로컬 설치 |
| `timescale_verify.sql` | TimescaleDB 설치 확인 쿼리 |
| `migrate_*.sql` | 스키마 마이그레이션 (handoff_acks, rfid_scan_log, email, timestamps 등) |

## For AI Agents

### Working In This Directory
- 스키마 변경 시 additive + reversible 마이그레이션 작성
- `create_tables_v2.sql`이 소스 오브 트루스
- 마이그레이션 실행: `psql -h 100.107.120.14 -U team2 -d smartcast_robotics -f <script>`

### Common Patterns
- 모든 마이그레이션은 IF NOT EXISTS 사용
- hypertable: `create_hypertable('table', 'time_column')`
- seed 스크립트는 idempotent (ON CONFLICT DO NOTHING)
