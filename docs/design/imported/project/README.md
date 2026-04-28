# SmartCast Robotics 프로젝트 문서 세트

> **최초 작성**: 2026-04-24
> **언어**: 한국어 (기술 용어 영문 병기)
> **대상**: SmartCast Robotics 내부 팀
> **원천**: Confluence `addinedute` (homepage 753829) + `docs/CONFLUENCE_FACTS.md` + `.moai/specs/`

---

## 문서 구성

| 번호 | 문서 | 대상 독자 | 주요 내용 |
|---|---|---|---|
| 01 | [PRD](./01_PRD.md) | 기획·전략·전체 팀 | 비전·목표·고객·기능 요구사항·NFR·성공 지표·MVP·로드맵 |
| 02 | [DESIGN](./02_DESIGN.md) | 개발자·아키텍트 | V6 이원화 아키텍처·서비스 구조·데이터 모델·API·HW·배포 |
| 03 | [PROCESS](./03_PROCESS.md) | 공정 기획·운영자·개발자 | 8단계 주조 공정·주문 FSM·AMR·검사·에러 복구·HW 이벤트 |
| 04 | [DEVELOPMENT](./04_DEVELOPMENT.md) | 개발자 | 기술 스택·환경 셋업·테스트·CI/CD·코드 컨벤션·디버깅 |
| 05 | [TRAINING](./05_TRAINING.md) | 신규 입사자·온보딩 | 1주 로드맵·디렉토리 지도·용어집·자주 겪는 문제 |
| 06 | [MANUAL](./06_MANUAL.md) | 고객·관리자·공장 운영자 | 웹 UI·PyQt 사용법·일상 플로우·문제 대응·지원 채널 |

**총 2,385 줄** (요약 기반, 상세는 기존 `docs/`, `docs/architecture/`, `.moai/specs/` 와 cross-reference)

---

## 읽는 순서 권장

### 신규 입사자
[05_TRAINING](./05_TRAINING.md) → [01_PRD](./01_PRD.md) → [03_PROCESS](./03_PROCESS.md) → [02_DESIGN](./02_DESIGN.md) → [04_DEVELOPMENT](./04_DEVELOPMENT.md) → [06_MANUAL](./06_MANUAL.md)

### 개발자 (담당 영역 파악)
[02_DESIGN](./02_DESIGN.md) → [04_DEVELOPMENT](./04_DEVELOPMENT.md) → 해당 영역 SPEC (`.moai/specs/`) → 아키텍처 상세 (`docs/architecture/`)

### 운영자 / 관리자
[06_MANUAL](./06_MANUAL.md) → [03_PROCESS](./03_PROCESS.md)

### 고객 (참조용)
[06_MANUAL §2](./06_MANUAL.md#2-고객-매뉴얼-customer)

---

## 연관 문서 (외부)

### 프로젝트 최상위
- [`../../CLAUDE.md`](../../CLAUDE.md) — MoAI 실행 지시 + V6 아키텍처 요약 + DB 정책
- [`../../AGENTS.md`](../../AGENTS.md) — AI 코드베이스 인덱스 (루트)

### 기존 문서 (`docs/`)
- [`../CONFLUENCE_FACTS.md`](../CONFLUENCE_FACTS.md) — Confluence 22 페이지 전량 수집 (23K 줄, 매일 자동 동기화)
- [`../SETUP.md`](../SETUP.md) — 로컬 셋업
- [`../DEPLOY-phase-a-to-c3.md`](../DEPLOY-phase-a-to-c3.md) — 배포 런북
- [`../management_service_design.md`](../management_service_design.md) — Management 상세 설계
- [`../barcode_jetson_ready.md`](../barcode_jetson_ready.md) — Jetson 바코드 배포
- [`../architecture/`](../architecture/) — 컴포넌트 설계 12개

### HTML 다이어그램
- `docs/system_overview.html`
- `docs/component_relationship_clear.html`
- `docs/event_bridge_flows.html`
- `docs/fleet_traffic_management.html`
- `docs/manhole_state_diagram.html`
- `docs/production_planning_flowchart.html`
- `docs/interface_service_audit.html`
- `docs/interface_internal_structure_explained.html`

### SPEC (`.moai/specs/`)
- SPEC-AMR-001 (AMR + Handoff)
- SPEC-RFID-001 (RFID)
- SPEC-RC522-001 (RC522 안정성)
- SPEC-ORD-001 (주문)
- SPEC-CASTING-001 (주조)
- SPEC-API-001 / 002
- SPEC-CTL-001
- SPEC-DB-V2-MIGRATION

### Confluence (참조)
- `addinedute` space homepage: 753829
- 주요 페이지 ID:
  - `3375131` System Architecture
  - `3375120` User Requirements
  - `6258774` System Requirements v3
  - `3375162` Casting 도메인
  - `6651919` Detailed Design
  - `22806540` Interface Specification v46
  - `3407906` Terminology (용어집)
  - `42270744` DB 연결 가이드 (AWS RDS)
  - `20217883` GitHub 폴더 구조 초안

⚠ Confluence 원본은 **READ-ONLY** — 수정/생성/삭제는 사용자 명시 허락 필수.

---

## 문서 유지보수 원칙

### 업데이트 주기
- **주 1회** 또는 **주요 변경 시**: 해당 문서 수정 + Git commit
- Confluence 팩트 변경은 launchd 자동 동기화 (`docs/CONFLUENCE_FACTS.md` 에 반영)
- SPEC 변경은 `.moai/specs/` 원본을 우선 업데이트 후 본 문서에 요약 반영

### 변경 이력
각 문서 말미의 변경 이력 표를 **반드시** 갱신.

### cross-reference
- 본 문서에서 상세는 기존 `docs/*` 로 링크 (중복 내용 최소화)
- 기존 문서 업데이트 시 본 문서의 링크 유효성 확인

### 용어 통일
- Confluence `Terminology` (3407906) 공식 약어 준수
- 영문 기술 용어는 첫 등장 시 한글과 병기

### PR 체크
- 본 문서 수정 PR 은 기획/개발 최소 1명 리뷰
- 코드와 문서가 함께 변경된 경우 동일 PR 에 포함

---

## 버전 관리

| 버전 | 일자 | 주요 변경 |
|---|---|---|
| V6 초판 | 2026-04-24 | 6개 문서 + README 생성. Confluence 22 페이지 + `.moai/specs/` 9건 + 기존 40+ docs 를 상위 레이어로 재구성 |

---

## 피드백

문서 오류·개선 제안:
- GitHub Issues (내부 저장소)
- Pull Request 직접 수정 (오타·링크 수정은 대환영)
- 프로젝트 리드 ibkim (kiminbean@gmail.com)
