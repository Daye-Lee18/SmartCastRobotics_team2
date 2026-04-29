# 05. 교육 문서 (온보딩)

> **버전**: V6 (2026-04-24)
> **대상 독자**: 신규 입사 개발자, 신규 운영 담당자, 인턴, 방문 엔지니어
> **학습 목표**: 1주일 내 프로젝트 전체 그림 파악 + 담당 영역 첫 PR 작성 가능

---

## 1. 환영 인사

SmartCast Robotics 팀에 오신 것을 환영합니다. 이 프로젝트는 **주조 공장 전체**를 무인·자동화하는 시도입니다. 단순 소프트웨어가 아니라 AMR·로봇팔·컨베이어·비전 시스템이 공장 바닥에서 움직이며, 고객의 주문이 실제 맨홀 뚜껑이 되어 출고되는 end-to-end 시스템입니다.

이 문서는 여러분이 코드베이스와 도메인을 빠르게 이해하고, 개발·운영 업무에 합류할 수 있도록 돕는 학습 가이드입니다.

---

## 2. 첫 주 로드맵

### Day 1 — 환경 셋업 + 전체 그림
- [ ] GitHub 접근, Tailscale 계정(`addineduteam2@`) 연결
- [ ] macOS 개발 환경 셋업 ([04_DEVELOPMENT.md §2](./04_DEVELOPMENT.md))
- [ ] [01_PRD.md](./01_PRD.md) 정독 → 프로젝트 비전·목표·고객 이해
- [ ] [02_DESIGN.md](./02_DESIGN.md) §1~3 → V6 이원화 아키텍처 파악
- [ ] Confluence `addinedute` space overview (homepage 753829) 열람
- [ ] DBeaver 로 로컬 DB (100.107.120.14 / smartcast_robotics) 접속 성공

### Day 2 — 공정 도메인 이해
- [ ] [03_PROCESS.md](./03_PROCESS.md) 전체 읽기
- [ ] 참고 기업 [기남금속](http://www.kinam.co.kr/) 영상/제품 확인
- [ ] 용어집 (§6) 숙지
- [ ] 8단계 공정 다이어그램 (`docs/production_planning_flowchart.html`) 시뮬레이션

### Day 3 — 코드 구조 체크
- [ ] 루트 `AGENTS.md` → 디렉토리 역할
- [ ] `backend/app/` 라우터 5개 읽기
- [ ] `backend/management/server.py` + 핵심 서비스 1개
- [ ] `monitoring/app/main_window.py` (핫 패스)
- [ ] `src/app/` Next.js 라우트 구조
- [ ] firmware/ 의 `conveyor` 펌웨어 1개

### Day 4 — HW 통신 이해
- [ ] [02_DESIGN.md §7](./02_DESIGN.md) HW 아키텍처
- [ ] Jetson SSH 접속 (`ssh jetson-conveyor` → 100.77.62.67)
- [ ] SPEC-AMR-001 Wave 3 Handoff 버튼 경로 이해
- [ ] SPEC-RFID-001 / 바코드 경로 이해

### Day 5 — 첫 PR 작성
- [ ] 담당 영역 결정 (프론트 / 백엔드 / 펌웨어 / 데이터)
- [ ] 작은 이슈 하나 선택 (라벨: `good-first-issue` 또는 문서 오타 수정)
- [ ] 브랜치 생성 → 수정 → 테스트 → PR 생성
- [ ] 코드 리뷰 받기

---

## 3. 시스템 개요 (한 번에 이해하기)

### 3.1 한 문장 요약
> 고객이 Next.js 대시보드에서 맨홀 주문을 넣으면, 관리자가 승인하고, Factory Operator가 PyQt에서 생산을 시작하면, AMR·로봇팔·컨베이어·비전 시스템이 협업해서 주물을 제작·검사·출고하며, 모든 이벤트가 PostgreSQL에 기록됩니다.

### 3.2 주요 등장인물 (서비스)
| 서비스 | 프로세스 | 포트 | 누가 씀 |
|---|---|---|---|
| **Interface** | FastAPI | 8000 (HTTP) | 고객/관리자 (Next.js) |
| **Management** | gRPC | 50051 | 공장 운영자 (PyQt), Jetson |
| **Next.js** | Node | 3000 (dev) | 브라우저 |
| **Monitoring** | PyQt | GUI | 공장 바닥 |
| **Jetson** | Python/ROS2 | - | 공장 컨베이어 옆 |
| **PostgreSQL** | DB | 5432 | 전체 |

### 3.3 왜 Interface와 Management를 분리했나?
**SPOF 제거**. Interface Service는 외부(고객 웹/관리자 웹) 트래픽을 받는데, 장애가 나면 공장도 멈추면 큰일난다. Management는 공장 내부만 책임지므로, Interface가 죽거나 AWS 이관 중이어도 공장은 계속 돌아가야 한다.

### 3.4 DB가 왜 두 개인가?
- **로컬 `smartcast_robotics` (public, v2)**: 평소 개발 대상. 22 테이블. 기존 백엔드 코드가 사용 중
- **AWS RDS `Casting` (ERP, 29 테이블)**: 특별 요청 시만. Confluence 42270744 가이드에 명시
- 두 스키마는 **호환되지 않음** — 코드 재사용 불가

---

## 4. 디렉토리 역할 빠른 지도

```
casting-factory/
├─ src/                # Next.js 16 (Frontend)
│   ├─ app/            # App Router (customer/admin/landing)
│   ├─ components/     # 공용 컴포넌트
│   └─ lib/            # API 클라이언트, 유틸
├─ backend/
│   ├─ app/            # Interface Service (FastAPI :8000)
│   │   ├─ routes/     # REST 엔드포인트
│   │   ├─ models/     # SQLAlchemy ORM
│   │   └─ services/   # 도메인 로직
│   ├─ management/     # Management Service (gRPC :50051)
│   │   ├─ proto/      # management.proto (단일 소스)
│   │   ├─ services/   # Ordering, TaskManager, EventBridge 등
│   │   └─ adapters/   # ROS2, Serial, JetCobot
│   ├─ scripts/        # 시드/마이그레이션 스크립트
│   └─ tests/
├─ monitoring/         # PyQt5 데스크톱 앱
│   └─ app/
│       ├─ main_window.py  # 핫 패스
│       ├─ pages/     # 탭별 뷰
│       ├─ widgets/   # 재사용 위젯
│       └─ workers/   # QThread 작업자
├─ jetson_publisher/   # Jetson Orin NX 퍼블리셔
├─ firmware/           # ESP32 Arduino 펌웨어
├─ tools/              # CLI 유틸 (barcode, serial ingest 등)
├─ scripts/            # 프로젝트 스크립트 (Confluence sync 등)
├─ deploy/             # FastDDS + Tailscale 배포 설정
├─ docs/               # 문서 (MD + HTML)
│   ├─ architecture/   # 12개 컴포넌트 설계
│   ├─ project/        # 이 문서들 (01~06)
│   └─ CONFLUENCE_FACTS.md  # Confluence 전량 수집본
├─ .moai/              # MoAI-ADK 설정 + SPEC
│   ├─ specs/          # 9개 SPEC 디렉터리
│   └─ config/
├─ .claude/            # Claude Code 설정 + 룰
├─ CLAUDE.md           # MoAI 실행 지시
└─ AGENTS.md           # AI 코드베이스 인덱스
```

---

## 5. 공정 상식 (개발자를 위한 주조 101)

### 5.1 용어
Confluence `Terminology` (3407906) 기반. 전체는 §6 용어집 참고.

- **주조 (Casting)**: 금속을 녹여 주형에 부어 형상을 만드는 공정
- **주형 (Mold)**: 주조를 위한 틀
- **주탕 (Pouring)**: 용탕을 주형에 붓는 것
- **용탕 (Molten metal)**: 녹아 있는 금속
- **탈형 (Demolding, DM)**: 냉각된 주물에서 주형을 제거
- **후처리 (Post-Processing, PP)**: 버 제거, 그라인딩 등 표면 마무리
- **검사 (Inspection, INSP)**: 품질 확인
- **AMR (Autonomous Mobile Robot)**: 자율주행 로봇 (여기서는 팔레트/주물 이송용)
- **FMS (Fleet Management System)**: 다수 AMR 관제

### 5.2 맨홀 뚜껑의 특성
- 무게 20~80kg → 사람이 옮기면 허리 나감
- 디자인 다양 → 주형 자주 교체
- 표면 후처리 필요 → 가장 큰 병목
- 불량률 관리 중요 → 검사 자동화 필수

### 5.3 왜 이 순서로 제작되는가
1. 설계 → 2. 주형 → 3. 용탕 → 4. 주입 → 5. 냉각 → 6. 탈형 → 7. 후처리 → 8. 검사 → 9. 분류 → 10. 출고

각 단계마다 **소요 시간 편차**가 있고, **병목**이 생김. 우리 시스템은 이 병목을 감지하고 AMR·로봇팔로 해소.

---

## 6. 용어집 (Glossary)

Confluence `Terminology` (3407906) 기반. 약어 위주.

### 6.1 일반
| 한글 | 영어 | 약어 | 설명 |
|---|---|---|---|
| 관제 | FMS | FMS | 다수 로봇의 작업 할당·경로 제어 |
| 자율주행로봇 | AMR | AMR | 라이다 기반 자율 이동 |
| 로봇팔 | Robot Arm | RA | JetCobot 280 |
| 컨베이어 벨트 | Conveyor | CONV | L298N + JGB37-555 + TOF250 |
| 포토 센서 | Photo Sensor | - | 맨홀 감지 |
| 고유번호 | Identifier | id | |
| 이름 | Name | nm | |
| 상태 | Status | stat | |
| 메시지 | Message | msg | |
| 요청 | Request | req | |
| 주문 | Order | ord | |
| 현재 | Current | cur | |
| 목적지 | Destination | dest | |
| 출발지 | Source | src | |
| 시각 | Date/Time | at | |
| 작업자 | Operator | op | |
| 자원 | Resource | res | |
| 배터리 | Battery | bat | |

### 6.2 공정
| 한글 | 영어 | 약어 | 설명 |
|---|---|---|---|
| 생산 (전체) | Manufacture | mfg | 주조부터 검사까지 |
| 주조 | Casting / cast | - | 금속을 녹여 주형에 |
| 주형제작 | Mold Making | - | 맨홀 틀 제작 |
| 주탕 | Pouring | - | 용탕 주입 |
| 패턴 | Pattern | ptn | 주형용 원형 모델 |
| 냉각 | Cooling | - | 고체화 |
| 탈형 | Demolding | DM | 주형 제거 |
| 후처리 | Post-Processing | pp | 표면 마무리 |
| 검사 | Inspection | INSP | 품질 확인 |
| 작업중 | Processing | proc | |

### 6.3 이송
| 한글 | 영어 | 약어 | 설명 |
|---|---|---|---|
| 이송 (전체) | Transport | trans | AMR 이동 모든 것 |

### 6.4 DB 스키마 약어
- `ord` = 주문 헤더 / `ord_detail` = 상세 / `ord_stat` = 상태 / `ord_log` = 이력
- `item` = 개별 주물 / `pattern` = 패턴
- `res` = 자원 마스터 / `equip` = 장비 / `trans` = 이송 장비 (AMR)
- `*_task_txn` = 작업 트랜잭션 / `*_err_log` = 에러 로그
- `*_location_stat` = 위치 상태 (chg/strg/ship)

---

## 7. 주요 문서 지도

### 7.1 빠른 시작
- [01_PRD.md](./01_PRD.md) — 프로젝트 전체
- [03_PROCESS.md](./03_PROCESS.md) — 공정 흐름
- [../SETUP.md](../SETUP.md) — 로컬 셋업

### 7.2 기술 심화
- [02_DESIGN.md](./02_DESIGN.md) — 설계
- [04_DEVELOPMENT.md](./04_DEVELOPMENT.md) — 개발 가이드
- [../architecture/](../architecture/) — 컴포넌트 설계 (12개)
- [../CONFLUENCE_FACTS.md](../CONFLUENCE_FACTS.md) — Confluence 원문 (필요 섹션만 Grep)

### 7.3 운영 / 배포
- [06_MANUAL.md](./06_MANUAL.md) — 사용자 매뉴얼
- [../DEPLOY-phase-a-to-c3.md](../DEPLOY-phase-a-to-c3.md) — 배포 런북
- [../barcode_jetson_ready.md](../barcode_jetson_ready.md) — Jetson 배포

### 7.4 SPEC
- `.moai/specs/SPEC-AMR-001/` — AMR 제어
- `.moai/specs/SPEC-RFID-001/` — RFID
- `.moai/specs/SPEC-RC522-001/` — RC522 안정성
- `.moai/specs/SPEC-ORD-001/` — 주문
- `.moai/specs/SPEC-CASTING-001.md` — 주조

### 7.5 HTML 다이어그램 (브라우저에서 열어보기)
```bash
open docs/system_overview.html
open docs/component_relationship_clear.html
open docs/event_bridge_flows.html
open docs/manhole_state_diagram.html
open docs/production_planning_flowchart.html
```

---

## 8. 자주 마주치는 문제 + 해결법

### 8.1 Tailscale 접속 실패
```bash
# 상태 확인
/Applications/Tailscale.app/Contents/MacOS/Tailscale status

# DB 서버 reachable 확인
nc -zv 100.107.120.14 5432
```
증상: `unreachable` 일시적. 재시도하면 보통 해결.

### 8.2 DB 접속 실패
```bash
PGPASSWORD='Addteam2!' psql -h 100.107.120.14 -p 5432 -U team2 -d smartcast_robotics -c "SELECT 1;"
```
실패 시:
- Tailscale 확인
- DB 서버 재시작 (yejin-laptop 소유자 문의)
- 로컬 PG 구버전 잔존 여부 (`brew services list | grep postgres`)

### 8.3 gRPC VersionError (Jetson)
- 원인: protoc 버전 mismatch
- 해결: Jetson 에서 `pip install grpcio-tools==1.59.5` 후 `management.proto` 재생성

### 8.4 PyQt 창 종료 시 크래시 (exit 134)
- 원인: QThread 정리 누락
- 해결: `closeEvent` 에서 모든 thread `requestInterruption()` + `wait()`

### 8.5 Next.js 16 LAN 접근 실패
- 원인: `allowedDevOrigins` 미설정
- 해결: `next.config.ts` 에 LAN IP 추가

### 8.6 DBeaver 드라이버 다운로드 실패
- 수동 JAR 배치: `~/Downloads/dbeaver-drivers/postgresql-42.7.4.jar`
- DBeaver Driver Manager → PostgreSQL → Libraries → Add File
- AWS RDS 연결 시 SSL verify-full + global-bundle.pem 경로 필수

### 8.7 Arduino CLI ESP32 업로드 실패
- FQBN 확인: `esp32:esp32:esp32s3`
- USB 포트: `ls /dev/cu.usbserial*`
- 드라이버 설치: CP2102 / CH34x

### 8.8 Confluence API 403
- Keychain 토큰 만료: `security find-generic-password -s casting-factory-atlassian -w`
- 갱신: Atlassian Account Settings → Security → API tokens

---

## 9. 디버깅 패턴 (경험 축적)

### 9.1 API 연동 불일치 (Frontend ↔ Backend)
**증상**: 필드 undefined, 응답 구조 다름
**대응**:
1. 프론트엔드 요청 payload 확인 (Network 탭)
2. 백엔드 Pydantic 스키마 대조
3. FastAPI auto-docs (`/docs`) 활용
4. **양쪽 코드 동시 열고 대조**

### 9.2 DB 시드 후 이상 동작
**증상**: ExecutionMonitor SLA 폭주, PyQt CPU 100%
**원인**: `items.mfg_at` 에 과거 시각
**해결**: `now() ±30초` 범위만 사용

### 9.3 MQTT 잔존 (레거시)
V6 Phase D에서 MQTT 제거. 코드에서 `mosquitto`, `paho-mqtt`, `broker` 검색 시 나오면 → 레거시 → 제거 후 gRPC로.

### 9.4 모터 테스트 시 Mac USB 끊김
- 증상: L298N 기동 전류로 Mac USB 전원 브라운아웃
- 해결: Jetson 직결 또는 외부 12V (절대 Mac USB 에 모터 전원 연결 금지)

---

## 10. 도메인 심화 학습 자료

### 10.1 주조 공정 일반
- 기남금속 홈페이지: http://www.kinam.co.kr/
- Confluence `Casting` (3375162) — 제품 특성, 최적화 목표
- Confluence `Logistics` (3637320) — VDA 5050 (참고, 미채택)

### 10.2 AMR / FMS
- ROS2 Jazzy 문서
- Nav2 (Navigation 2) 공식 가이드
- Confluence `관제 기술조사` (20774933)
- `project_fleet_traffic_design.md` 메모리 (1m×2m 맵, 3 AMR)

### 10.3 비전 검사
- Jetson Orin NX 공식 문서
- OpenCV / Ultralytics 튜토리얼
- Confluence `Vision` (7405777)

### 10.4 RFID / 바코드
- RC522 데이터시트
- Confluence `[개요]RFID 태그 기반 식별 시스템 개요` (30179373)
- Confluence `[실험]RFID / 바코드 통신 및 UID 추출 실험` (30539816)
- `feedback_barcode_module_width.md` (module_width 0.4mm 필수)

### 10.5 MoAI-ADK
- `~/.moai/CLAUDE.md` — MoAI 지시
- `.claude/rules/moai/` — 프로젝트 룰
- `/moai` 슬래시 커맨드 사용법

---

## 11. 첫 PR 체크리스트

### 11.1 전
- [ ] 담당 이슈/SPEC 이해
- [ ] 최신 main 에서 브랜치 생성
- [ ] 테스트 실행 (실패 없음 확인)

### 11.2 작업 중
- [ ] 코드 컨벤션 준수 (TypeScript strict, ruff, black)
- [ ] 커밋 메시지 Conventional
- [ ] 관련 테스트 추가/업데이트
- [ ] 로컬 lint + typecheck 통과

### 11.3 PR 전
- [ ] 자가 코드 리뷰 (diff 다시 보기)
- [ ] CLAUDE.md 업데이트 필요 여부 확인
- [ ] AGENTS.md 갱신 필요 여부 확인
- [ ] 스크린샷/로그 준비 (UI/HW 변경 시)

### 11.4 PR 생성
- [ ] 제목: 70자 이내, Conventional
- [ ] 본문: Summary + Test plan + 검증 방법
- [ ] Co-Authored-By: Claude Opus 4.7 (해당 시)
- [ ] 관련 이슈/SPEC 링크

---

## 12. 외부 소통 프로토콜

### 12.1 Confluence
- **READ-ONLY**: 사용자 명시 허락 없이 수정/생성/삭제 **금지**
- 특정 페이지 수정 승인: 세션 로그에 명시적 기록
- 자동 동기화는 GET 요청만 수행

### 12.2 DB (로컬)
- DDL 작업은 postgres 슈퍼유저 (`Addteam2!`)
- 파괴적 쿼리 (DROP, TRUNCATE) 전 백업 필수
- 테이블 이름 변경 시 `ALTER TABLE SET SCHEMA` 로 안전 이동

### 12.3 AWS RDS
- 접속: SSL verify-full + RDS CA (`~/Downloads/dbeaver-drivers/global-bundle.pem`)
- 비용 발생 주의 (특히 대량 쿼리)
- 프로덕션 데이터 가정 (신중)

---

## 13. 연락처 / 지원

### 13.1 주요 담당 (2026-04-24 기준)
- **프로젝트 리드**: ibkim (kiminbean@gmail.com) — Atlassian / Mac / 전반
- **DB 서버 운영**: yejin-laptop 소유자
- **Jetson / 펌웨어**: 공장 운영팀

### 13.2 채널
- **슬랙 (예정)**: `#smartcast-robotics`
- **이슈 트래커**: GitHub Issues
- **문서 업데이트**: 이 문서(`docs/project/05_TRAINING.md`) 직접 PR

### 13.3 긴급 복구
- Confluence 자동 동기화 실패: `tail -f logs/confluence_sync.log`
- launchd 재적재: `launchctl unload/load ~/Library/LaunchAgents/com.casting-factory.confluence-sync.plist`
- DBeaver 설정 깨짐: `~/Library/DBeaverData/workspace6/General/.dbeaver/data-sources.json.bak-*` 에서 복구
- Claude Code UTF-8 크래시: `~/.claude/todos/*.json` → `todos_backup/`

---

## 14. 체크인 질문 (학습 검증)

한 주 마무리 때 스스로 답해보세요:

1. **V6 이원화의 이유를 한 문장으로 설명할 수 있나?**
2. **Interface와 Management가 어떤 DB/스키마를 쓰는지 말할 수 있나?**
3. **평소 개발 DB와 특별 요청 DB가 뭐고 차이가 뭔지?**
4. **AMR Handoff Button 이벤트가 ESP32 → DB까지 어떤 경로로 흐르나?**
5. **주문 상태 전이 (RCVD → APPR → MFG → DONE → SHIP → COMP) 를 그려 볼 수 있나?**
6. **의사결정 규칙 A/B/C 가 뭔가?**
7. **MoAI-ADK 의 `plan/run/sync` 가 무엇을 하는가?**
8. **Confluence 문서는 어떻게 동기화되는가?**
9. **gRPC protobuf 버전 mismatch 발생 시 어떻게 해결하나?**
10. **로컬 DB에 `public`과 `smartcast` 두 스키마가 있는 이유는?**

답이 애매하면 해당 섹션 다시 읽기.

---

## 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | V6 | 초기 작성. 1주 로드맵 + 디렉토리 지도 + 용어집 + 디버깅 패턴 + 체크인 질문 |
