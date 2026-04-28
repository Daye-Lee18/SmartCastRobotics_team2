# 04. 개발 문서

> **버전**: V6 (2026-04-24)
> **대상 독자**: 개발자 (프론트엔드 / 백엔드 / 펌웨어 / 데이터)
> **관련**: [01_PRD.md](./01_PRD.md), [02_DESIGN.md](./02_DESIGN.md)

---

## 1. 기술 스택

### 1.1 Frontend (`src/`)
- Next.js **16** (App Router)
- React 19, TypeScript (strict mode 필수)
- Tailwind + shadcn/ui
- Three.js (3D 렌더 맵, 실험 단계)
- package manager: `pnpm` 또는 `npm`

### 1.2 Backend
- **Interface Service** (`backend/app/`): FastAPI + SQLAlchemy 2.0 + Pydantic
- **Management Service** (`backend/management/`): grpcio + SQLAlchemy + asyncio
- Python **3.12** 강제 (PyQt5/grpcio macOS Apple Silicon 호환)

### 1.3 Monitoring
- `monitoring/`: PyQt5 + grpcio + pg8000/psycopg2
- Python 3.12 venv 전용

### 1.4 Firmware
- `firmware/`: ESP32-S3 / ESP32 (Arduino framework)
- Arduino CLI 1.4.1 + ESP32 core 3.3.7
- `micro_ros_arduino` (라이브러리 선택 사항)

### 1.5 Jetson Publisher
- `jetson_publisher/`: Python 3.x on Jetson Orin NX
- grpcio-tools 1.59.5 (protobuf 4.25.9 매칭)
- python-evdev (바코드 HID)
- ROS2 Jazzy

### 1.6 Infra / Tooling
- PostgreSQL 16 (로컬) / 18.3 (AWS RDS)
- Tailscale 메시 네트워크
- DBeaver Community (GUI)
- Docker (로컬 실험 한정)
- launchd (Confluence 동기화)

---

## 2. 개발 환경 준비

### 2.1 macOS (Apple Silicon) 권장 설정
1. **Homebrew**: `brew install node python@3.12 postgresql@16 tailscale`
2. **pnpm**: `npm install -g pnpm`
3. **Tailscale 로그인**: addineduteam2@ tailnet
4. **DBeaver 설치**: `brew install --cask dbeaver-community`

### 2.2 Python 3.12 venv
```bash
cd backend/management
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../../monitoring
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
**주의**: Python 3.14는 PyQt5 / grpcio 휠 미제공 → 3.12 고정.

### 2.3 프런트엔드
```bash
pnpm install
cp .env.local.example .env.local  # API_BASE 등
pnpm dev
```

### 2.4 DB 접속 설정
`backend/.env.local`:
```
DATABASE_URL=postgresql+psycopg://team2:Addteam2!@100.107.120.14:5432/smartcast_robotics
```
AWS RDS 접속 (특별 요청 시):
```
DATABASE_URL=postgresql+psycopg://postgres:team21234@teamdb.ct4cesagstqf.ap-northeast-2.rds.amazonaws.com:5432/Casting?sslmode=verify-full&sslrootcert=/Users/ibkim/Downloads/dbeaver-drivers/global-bundle.pem
```

---

## 3. 워크플로우

### 3.1 브랜치 전략
- `main`: 안정 (프로덕션 배포 대상)
- `feat/<scope>-<desc>`: 기능 브랜치 (예: `feat/v6-phase-c2-proxy`)
- `fix/<scope>`: 버그 수정
- `chore/<scope>`: 빌드/설정
- `docs/<scope>`: 문서 전용

### 3.2 Conventional Commits
```
<type>(<scope>): <subject>

본문 (선택)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `i18n`
Scopes 예: `mgmt`, `bridge`, `amr`, `handoff`, `barcode`, `docs`, `tools`, `session`

### 3.3 커밋 규칙
- **기능 완료 시점**에 자동 커밋 (feature/bugfix/refactor 완료 시)
- **Auto-push 금지** — 사용자가 결정
- Atomic commits: 한 커밋은 한 목적만
- 리팩토링과 기능 개발 분리

### 3.4 PR 흐름
1. 브랜치 생성 (예: `feat/xxx`)
2. 로컬 테스트 + lint + typecheck
3. 커밋 (conventional)
4. Push → PR 생성 (gh CLI 권장)
5. 리뷰 + CI 통과 확인
6. Squash-merge 기본

### 3.5 PR 체인 squash 패턴 (실전 경험)
base 의존 PR 체인 머지 시 자동 close → cherry-pick rebase + 새 PR 발급 패턴 (2026-04-19 DB v2 마이그레이션 경험).

### 3.6 MoAI-ADK 워크플로우
SPEC → Plan → Run → Sync:
- `/moai plan "설명"` → `manager-spec` 에이전트가 EARS 포맷 SPEC 생성
- `/moai run SPEC-XXX` → `manager-ddd` 또는 `manager-tdd` 가 구현
- `/moai sync SPEC-XXX` → `manager-docs` 가 문서 동기화

자동 파이프라인 실행 예: `/moai` (자연어 라우팅) 또는 `/ultrareview` (교정 루프).

---

## 4. DB 운영 룰

### 4.1 2026-04-24 확정 정책
- **평소 개발**: 로컬 Tailscale `100.107.120.14:5432 / smartcast_robotics`, role `team2` (`Addteam2!`), 스키마 `public` (v2, 22 테이블)
- **특별 요청 시만**: AWS RDS `teamdb.ct4cesagstqf.ap-northeast-2.rds.amazonaws.com:5432 / Casting`, role `postgres` (`team21234`), SSL `verify-full` 필수
- **로컬 `smartcast` 스키마** (31 테이블 ERP 복사본) — 참조/실험용
- 두 DB 스키마 **호환 불가** — 코드 재사용 금지

### 4.2 DATABASE_URL fail-fast
- 미설정 시 `backend/app/database.py` 에서 RuntimeError raise
- SQLite 폴백 **완전 제거** (2026-04-14 결정, SPEC-C3)

### 4.3 마이그레이션
- Alembic 기반 (backend/alembic/)
- 신규 컬럼 추가는 additive (NOT NULL은 default 동반)
- 파괴적 변경은 별도 SPEC + 백업 선행

### 4.4 시드 데이터
- 마스터 데이터는 `backend/scripts/` 에 재현 가능한 스크립트로
- 과거 시각 넣으면 ExecutionMonitor SLA 폭주 주의 (2026-04-15 사고) — `items.mfg_at` 은 `now() ±30초`만

---

## 5. 로컬 실행

### 5.1 Interface Service
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.2 Management Service
```bash
cd backend/management
source .venv/bin/activate
python server.py  # 기본 :50051
```
환경 변수:
- `MGMT_ROS2_ENABLED=1`: ROS2 DDS 활성화
- `INTERFACE_PROXY_START_PRODUCTION=1`: SPEC-C2 Interface proxy 활성화

### 5.3 Frontend
```bash
pnpm dev
# http://localhost:3000
```
`allowedDevOrigins` 는 Next.js 16에서 필수 (LAN 접근용).

### 5.4 Monitoring (PyQt)
```bash
cd monitoring
source .venv/bin/activate
python main.py
```

### 5.5 Jetson Publisher (원격)
```bash
ssh jetson-conveyor  # 100.77.62.67
cd ~/casting-factory/jetson_publisher
source .venv/bin/activate
python image_publisher.py &
python esp_bridge.py &
```

---

## 6. 테스트 전략

### 6.1 Backend (pytest)
```bash
cd backend
python -m pytest
# 또는
cd backend/management
python -m pytest tests/
```
주요 테스트:
- `test_order_pipeline_4seq.py` — 4 스테이지 순차 주문 파이프라인
- `test_event_bridge.py` — EventBridge 20 테스트
- `test_interface_service_client.py`, `test_management_service_client.py` — 클라이언트 통합

### 6.2 Frontend (Jest + Vitest)
```bash
pnpm test
pnpm test:e2e  # Playwright
```

### 6.3 Monitoring
```bash
cd monitoring
python -m pytest
```

### 6.4 Firmware
Arduino CLI:
```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3 firmware/conveyor
arduino-cli upload --port /dev/cu.usbserial-xxx --fqbn esp32:esp32:esp32s3 firmware/conveyor
```

### 6.5 E2E (LSP + AST)
- `/moai loop` — Ralph 엔진 (LSP 진단 + AST grep + 자동 수정)
- `/moai fix` — LSP 에러 자동 수정
- `/moai coverage` — 커버리지 분석

### 6.6 품질 게이트 (LSP)
`.moai/config/sections/quality.yaml`:
- plan 단계: LSP baseline 캡처
- run 단계: 에러 0, 타입 에러 0, 린트 에러 0 필수
- sync 단계: 에러 0, 경고 최대 10

---

## 7. 코드 컨벤션

### 7.1 TypeScript / React
- **strict mode 필수**, `any` 금지
- **named exports 우선** (default export 지양)
- 작은 모듈 + 순수 함수 선호
- 컴포넌트 단일 책임
- `className` + Tailwind 유틸 클래스
- `useEffect` 최소화 (파생 상태 우선)

### 7.2 Python
- Python 3.12 고정
- ruff + black 포맷팅
- Pydantic v2 기반 모델
- SQLAlchemy 2.0 async 스타일
- f-string 권장
- 타입 힌트 전부 표기
- `async`/`await` 패턴 → 오류는 `async-await-coder` 스킬 활용

### 7.3 Proto
- `management.proto` 단일 소스
- Monitoring 에서는 `monitoring/scripts/gen_proto.sh` 로 relative import 패치 필수
- Jetson 에서는 `grpcio-tools==1.59.5` 로 재생성

### 7.4 주석 규칙
- 주석은 **Why** 위주 (무엇이 아닌 왜)
- TODO 는 이슈 번호 함께
- 작업 지시자가 명확해야 함 (`TODO(user):`)

### 7.5 파일 구조
- AGENTS.md: 디렉토리별 AI 컨텍스트 (29개 파일, 2026-04-24 생성)
- CLAUDE.md: 프로젝트 루트 AI 지시
- .moai/specs/: SPEC 디렉터리
- docs/: 문서 루트

---

## 8. 배포

### 8.1 Phase 별 런북
- Phase A → C3: `docs/DEPLOY-phase-a-to-c3.md`
- Barcode 핸드오프: `docs/barcode_jetson_ready.md`

### 8.2 배포 순서 (공장 환경)
1. DB 상태 확인 (Tailscale: `nc -zv 100.107.120.14 5432`)
2. Management Service 기동
3. Interface Service 기동
4. Next.js (production build: `pnpm build && pnpm start`)
5. Jetson Publisher (image_publisher + esp_bridge)
6. PyQt Monitoring
7. 기능 smoke test (주문 생성 → PyQt 표시 확인)

### 8.3 Tailscale 이슈 대응
- 노드 unreachable 일시적 (yejin-laptop, 100.107.120.14)
- CLI: `/Applications/Tailscale.app/Contents/MacOS/Tailscale status`
- DB 실패 시 자동 reconnect 로직 (Interface/Management 양쪽)

### 8.4 FastDDS (AMR)
- `deploy/fastdds/` 설정
- Tailscale 피어별 discovery 설정

---

## 9. CI/CD (현재 로컬 중심, CI 도입 예정)

### 9.1 로컬 검증
- `pnpm lint`, `pnpm typecheck`, `pnpm test`
- `ruff check backend/`, `pytest backend/`
- 커밋 전 훅 (pre-commit): ruff + black + eslint

### 9.2 Confluence 동기화 (launchd)
- 스크립트: `scripts/sync_confluence_facts.py`
- 스케줄: 매일 09:07 로컬 시각
- plist: `~/Library/LaunchAgents/com.casting-factory.confluence-sync.plist`
- 인증: macOS Keychain (`service=casting-factory-atlassian`)

### 9.3 문서 검증
- `/moai sync` 로 CLAUDE.md ↔ 코드 일관성 체크
- AGENTS.md 상위 참조 무결성 검증 (DeepInit 실행 시)

---

## 10. MCP 및 AI 도구

### 10.1 MCP 서버
- **Atlassian**: Confluence 조회·동기화
- **claude-context**: 시맨틱 코드 검색 (645 파일 / 27,035 청크 인덱스 완료)
- **context7**: 라이브러리 문서 조회
- **gemini-code-reviewer**, **gemini-web**: 교차 검증
- **sequential-thinking**: --deepthink 플래그 사용 시 구조적 분석
- **oh-my-claudecode**: OMC 워크플로우

### 10.2 MCP 서버 timeout 이슈
claude-context의 Zilliz Milvus 15초 timeout 패치 필요:
- 파일: `~/.npm/_npx/<HASH>/node_modules/@zilliz/claude-context-core/dist/vectordb/milvus-vectordb.js`
- 코드: `timeout: Number(process.env.MILVUS_CLIENT_TIMEOUT) || 120000` 추가
- 자세한 내용: 메모리 `reference_claude_context_timeout.md`

### 10.3 Confluence 자동화 규칙
- **READ-ONLY** (사용자 명시 허락 없이 PUT/POST/DELETE 금지)
- `docs/CONFLUENCE_FACTS.md` 로컬 동기화만 허용

---

## 11. 디버깅 패턴

### 11.1 Claude Code UTF-8 크래시 방지
- TodoWrite content/activeForm 은 **영어만** 사용
- 한국어는 본문 대화만 허용
- 크래시 시 복구: `~/.claude/todos/*.json` → `todos_backup/`

### 11.2 PyQt 종료 exit 134 (SIGABRT)
- 원인: closeEvent 에서 QThread 정리 누락 (alert/stream/frame thread)
- 해결: 각 thread `requestInterruption()` + `wait()` 후 종료

### 11.3 gRPC protobuf 버전 mismatch
- 증상: `VersionError` Jetson 기동 실패
- 원인: Mac protoc 6.31 → Jetson protobuf 5.29 불일치
- 해결: Jetson 에서 `grpcio-tools 1.59.5` 로 재생성

### 11.4 RC522 healthcheck 버그
- 증상: `PICC_IsNewCardPresent` 간섭으로 카드 감지 실패
- 원인: 주기적 `VersionReg` 읽기
- 해결: 펌웨어 v1.5.1 에서 제거

### 11.5 모터 brownout (Mac USB)
- 증상: L298N 모터 기동 전류로 Mac USB 전원 끊김
- 해결: Jetson 직접 또는 외부 12V 전원 필수

### 11.6 디버깅 도구
- `/oh-my-claudecode:debug` — OMC 세션 진단
- `/oh-my-claudecode:tracer` — 가설 기반 추적
- `claude --debug "hooks,api,mcp"` — 전체 디버그

---

## 12. 프로젝트 메모리 / AGENTS.md

### 12.1 CLAUDE.md (프로젝트 루트)
MoAI 실행 지시 + V6 아키텍처 + DB 정책. 40,000자 이하 유지.

### 12.2 AGENTS.md (계층별)
2026-04-24 DeepInit로 29개 생성 (Level 0~4):
- Level 0: 루트 (프로젝트 전체)
- Level 1: 9개 디렉토리
- Level 2: 9개 핵심 서브디렉토리
- Level 3: 10개
- Level 4: 2개

### 12.3 세션 메모리 (`~/.claude/projects/-Users-ibkim-Project-casting-factory/memory/`)
- MEMORY.md: 엔트리 인덱스 (200줄 이내)
- 개별 메모리: `<type>_<topic>.md`
- 타입: user / feedback / project / reference

### 12.4 중요 메모리 항목
- `project_v6_grpc_decision.md`, `project_v6_complete.md`
- `feedback_db_postgresql_only.md` (DB 운영 룰)
- `reference_db_aws_rds_casting.md` (AWS RDS 연결)
- `feedback_handoff_fsm_seed_test.md`, `project_spec_amr_001_wave3.md`
- `project_event_bridge_contract.md`
- `feedback_grpc_proto_version_match.md`

---

## 13. 자주 하는 실수 / 주의

### 13.1 일반
- 가상의 라이브러리/API 제안 금지 — 실제 존재하는 것만
- 테스트 없이 "완료" 선언 금지
- 존재하지 않는 함수 사용 금지

### 13.2 풀스택 통합
- **Frontend↔Backend 필드명/경로/응답구조 양쪽 코드 대조 후 수정** (가정 금지)
- 환경변수는 `.trim()` 처리 (줄바꿈 가능)
- 상태 전이 시 모든 관련 필드 업데이트 확인
- UI 스타일 작업 전 dark mode 지원 여부 확인

### 13.3 DB
- `models_legacy` 전체 import 시 `Base.metadata` 충돌 주의 (선별 파일 `models_mgmt.py` 사용)
- 시드 스크립트에서 과거 시각 넣지 말 것 (SLA 폭주)
- Confluence 패트와 DB 스키마 불일치 시 코드 우선

### 13.4 Git
- `--no-verify` / `--no-gpg-sign` 사용자 명시 요청 없으면 금지
- force-push to main 절대 금지
- 스쿼시 전 변경 이력 확인

---

## 14. 참고 자료

### 14.1 내부
- [01_PRD.md](./01_PRD.md) — 제품 요구사항
- [02_DESIGN.md](./02_DESIGN.md) — 시스템 설계
- [03_PROCESS.md](./03_PROCESS.md) — 공정 프로세스
- [05_TRAINING.md](./05_TRAINING.md) — 교육 자료
- [06_MANUAL.md](./06_MANUAL.md) — 사용자 매뉴얼
- [`../SETUP.md`](../SETUP.md) — 셋업 가이드
- [`../DEPLOY-phase-a-to-c3.md`](../DEPLOY-phase-a-to-c3.md) — 배포 런북
- [`../../CLAUDE.md`](../../CLAUDE.md) — MoAI 실행 지시
- `.claude/rules/` — 프로젝트 룰

### 14.2 외부
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- Next.js 16: https://nextjs.org/docs
- gRPC Python: https://grpc.io/docs/languages/python/
- ROS2 Jazzy: https://docs.ros.org/en/jazzy/
- PyQt5: https://doc.qt.io/qtforpython-5/

---

## 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | V6 | 초기 작성. 기술 스택 · 환경 셋업 · 테스트 · CI/CD · 디버깅 패턴 정리 |
