# smart_cast_db

SmartCast FMS의 DB 스키마, 시드 데이터, ORM 모델, 그리고 DB 검증 스크립트를 담는 패키지입니다.

---

## 폴더 구조

```
smart_cast_db/
├── models/             ← SQLAlchemy ORM 모델 (DB 스키마의 단일 진실 공급원)
├── schema/             ← DDL SQL (ORM 모델 기반으로 작성된 CREATE TABLE 문)
├── seed/               ← 마스터 데이터 시드 SQL
├── scripts/            ← DB 연결 확인 및 FMS 시나리오 테스트용 Python CLI
├── migrations/         ← Alembic 마이그레이션 파일 (미래 사용)
├── tests/              ← DB 컨트랙트 테스트
├── .env.example        ← DB 접속 정보 템플릿
├── requirements.txt    ← scripts/ 실행에 필요한 의존성 (psycopg3, python-dotenv)
└── database.py         ← SQLAlchemy 엔진/세션 팩토리 (main_service 등에서 import)
```

---

## 각 폴더 설명

### `models/`

SQLAlchemy ORM 클래스 정의. 이 파일들이 **DB 스키마의 단일 진실 공급원**입니다.

스키마를 변경할 때는 모델을 먼저 수정하고, 그에 맞춰 `schema/create_tables.sql`과 `seed/seed_master.sql`을 함께 갱신합니다.

| 파일 | 담당 테이블 |
|---|---|
| `_base.py` | SQLAlchemy Base, 공통 import |
| `user.py` | `user_account` |
| `master.py` | `category`, `product`, `product_option`, `pp_options`, `pattern_master`, `zone`, `res`, `equip`, `equip_load_spec`, `trans`, `trans_task_bat_threshold`, `ra_motion_step`, `ai_model` |
| `order.py` | `ord`, `ord_detail`, `ord_pp_map`, `ord_pattern`, `ord_txn`, `ord_stat`, `ord_log` |
| `item.py` | `item` |
| `equipment.py` | `equip_task_txn`, `equip_stat`, `pp_task_txn`, `log_err_equip`, `log_data_equip` |
| `transport.py` | `trans_task_txn`, `trans_stat`, `log_err_trans`, `transport_tasks`, `handoff_acks`, `tat_nav_pose_master` |
| `alert.py` | `alerts` |
| `rfid.py` | `rfid_scan_log` |
| `inspection.py` | `insp_task_txn`, `ai_inference_txn`, `insp_stat` |

### `schema/`

`create_tables.sql` — ORM 모델을 기반으로 작성된 DDL. 새 DB에 스키마를 만들거나 초기화할 때 사용합니다.

> `CREATE TABLE IF NOT EXISTS`가 아니라 `CREATE TABLE`이므로, 기존 DB에 실행하면 오류가 납니다. 완전 초기화 시에는 아래 **DB 초기화** 절차를 따르세요.

### `seed/`

`seed_master.sql` — 시나리오 실행 전에 채워야 할 마스터 데이터. `ON CONFLICT DO UPDATE`이므로 중복 실행해도 안전합니다.

채워지는 테이블:

| 테이블 | 내용 |
|---|---|
| `user_account` | admin, operator, fms, 고객 2명 |
| `product` / `product_option` | 원형·사각·타원형 맨홀뚜껑 9종 |
| `pp_options` | 표면연마, 방청코팅, 아연도금, 로고삽입 |
| `pattern_master` | MM 모션 패턴 1~3 |
| `zone` / `res` / `equip` | 공정 구역 및 로봇 장비 |
| `chg_location_stat` | 충전 슬롯 3개 |
| `strg_location_stat` | 보관 슬롯 18개 (3행×6열) |
| `ship_location_stat` | 출하 슬롯 5개 |
| `trans` / `trans_task_bat_threshold` | AMR 정의 및 배터리 임계값 |
| `tat_nav_pose_master` | TAT 네비게이션 목적지 포즈 |
| `ra_motion_step` | RA 모션 시퀀스 (PAT/MAT 공통, `tool_type`으로 구분) |
| `ai_model` | YOLO/PatchCore 모델 |

> `pattern_master`는 MM 모션 패턴 정의 테이블이고, `ord_pattern`은 주문(`ord`)과 패턴을 1:1로 연결하는 테이블입니다. `ptn_id`는 1~3 중 하나를 뜻합니다.
> `ra_motion_step.pattern_no`도 같은 `pattern_master.ptn_id`를 참조합니다.
> `ra_motion_step.tool_type`은 `MAT` 또는 `PAT`를 의미합니다. MM/POUR/DM은 `MAT`, PA_GP/PA_DP/PICK/SHIP은 `PAT`로 기록합니다.
> `tat_nav_pose_master`는 실제 운용하는 TAT 목적지 포즈만 저장합니다. `*_WAIT`는 nav2 설정 파일에만 두고 DB에는 넣지 않습니다.

### `scripts/`

psycopg3 기반 CLI 스크립트. FMS 시나리오를 DB에 직접 재현해 백엔드/웹 없이도 흐름을 검증합니다.

| 스크립트 | 설명 |
|---|---|
| `_db.py` | 공통 DB 연결 헬퍼 (직접 실행 X) |
| `00_check_connection.py` | Phase 0: DB 연결 확인 + 마스터 테이블 건수 출력 |
| `01_create_tables.py` | Phase 0-1: 스키마 생성 + DDL 실행 (처음 한 번만) |
| `02_seed_master.py` | Phase 0-2: 마스터 데이터 시드 (처음 한 번만) |
| `03_create_customer_order.py` | Phase 1-1: 고객 주문 생성 (웹 UI 대체, ord_pattern 생성 포함) |
| `04_admin_approve_order.py` | Phase 1-2: 관리자 주문 승인 RCVD→APPR (웹 UI 대체) |
| `05_operator_start_production.py` | Phase 2: 생산 시작 APPR→MFG + item 생성 |
| `06_query_order_and_items.py` | 조회: 주문 헤더·이력·아이템 전체 출력 |

### `migrations/`

Alembic 마이그레이션 파일 보관 위치 (현재 미사용). 스키마 변경 이력 관리가 필요할 때 Alembic을 도입하세요.

### `tests/`

DB 컨트랙트 테스트. ORM 모델이 실제 DB 구조와 일치하는지 검증합니다.

---

## 처음 실행하는 경우 — 전체 순서

### Step 1. 환경 설정

```bash
cd SmartCastRobotics_team2/server/smart_cast_db

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### Step 2. .env 파일 작성

```bash
cp .env.example .env
```

`.env` 파일을 열어 실제 DB 접속 정보를 입력합니다.

```
DATABASE_URL=postgresql://유저:비밀번호@호스트:5432/DB이름
DB_SCHEMA=smartcast
```

> `SSL_CERT`는 비워두면 프로젝트 루트의 `global-bundle.pem`을 자동으로 탐색합니다.

### Step 3. 테이블 생성 (처음 한 번만)

```bash
python scripts/01_create_tables.py
```

### Step 4. 마스터 데이터 시드 (처음 한 번만)

```bash
python scripts/02_seed_master.py
```

### Step 5. DB 연결 확인

```bash
python scripts/00_check_connection.py
```

정상 출력 예시:

```
SmartCast DB connection OK
  user_account: 5
  category: 3
  product: 9
  ...
```

---

## 시나리오 실행 순서

> 각 단계는 이전 단계의 결과(ord_id)를 다음 단계 입력으로 사용합니다.

### Phase 1-1. 고객 주문 생성 — Web UI 사용 (권장)

백엔드와 웹을 실행합니다.

```bash
cd SmartCastRobotics_team2
./scripts/run-backend.sh
./scripts/run-web.sh
```

SSH 원격 접속 중인 경우 로컬 포트포워딩 먼저 설정합니다.

```bash
ssh -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@{ip주소} -N
```

브라우저에서 `http://localhost:3001` 접속 후 고객 계정으로 로그인합니다.

| 계정 | 이메일 | 비밀번호 |
|---|---|---|
| 이민준 (TechBuild Inc.) | `minjun@techbuild.co` | `customer1234` |
| 정수연 (BuildWorld Co.) | `sooyeon@buildworld.kr` | `customer1234` |

5단계 주문 마법사를 완료하면 `ord_id`가 발급됩니다.

> 웹 없이 빠르게 테스트하려면 스크립트로 대체할 수 있습니다.
> ```bash
> python scripts/03_create_customer_order.py
> ```

> 기본 실행 시 주문과 함께 `ord_pattern(ord_id, ptn_id=1)`도 생성됩니다. 다른 패턴을 쓰려면 `--ptn-id 2` 또는 `--ptn-id 3`을 넘기면 됩니다.

### Phase 1-2. Admin 주문 승인

```bash
python scripts/04_admin_approve_order.py --ord-id <ord_id>
```

### Phase 2. Operator 생산 시작

```bash
python scripts/05_operator_start_production.py --ord-id <ord_id>
```

### 언제든지 — 현재 상태 조회

```bash
python scripts/06_query_order_and_items.py --ord-id <ord_id>
```

---

## 전체 실행 예시 (복붙용)

```bash
cd SmartCastRobotics_team2/server/smart_cast_db
source .venv/bin/activate

# Phase 0: DB 연결 확인
python scripts/00_check_connection.py

# Phase 1-1: Web UI에서 고객 주문 생성 후 ord_id 확인
python scripts/06_query_order_and_items.py --ord-id <ord_id>

# Phase 1-2: Admin 승인
python scripts/04_admin_approve_order.py --ord-id <ord_id>

# Phase 2: 생산 시작
python scripts/05_operator_start_production.py --ord-id <ord_id>

# 언제든지: 현재 상태 조회
python scripts/06_query_order_and_items.py --ord-id <ord_id>
```

---

## Web/PyQt 연동 확인

DB 상태를 만든 뒤 backend, web, PyQt를 실행해서 화면을 확인합니다.

```bash
cd SmartCastRobotics_team2
./scripts/run-all.sh
```

> **주의:** `server/main_service/.env.local`의 `DATABASE_URL`이 `server/smart_cast_db/.env`와 동일한 DB를 가리켜야 Web/PyQt에서 결과를 확인할 수 있습니다.

---

## DB 초기화 (처음부터 다시)

### 방법 1 — Python 스크립트

```bash
cd SmartCastRobotics_team2/server/smart_cast_db
source .venv/bin/activate

python scripts/01_create_tables.py
python scripts/02_seed_master.py
```

> `01_create_tables.py`는 `CREATE SCHEMA IF NOT EXISTS`를 사용하므로, 기존 테이블이 있으면 오류가 납니다.
> 완전 초기화가 필요하면 방법 2를 사용하세요.

### 방법 2 — psql 직접

```bash
sudo -i -u postgres
psql -d <db_name> \
  -c "DROP SCHEMA IF EXISTS smartcast CASCADE;" \
  -c "CREATE SCHEMA smartcast;" \
  -c "SET search_path = smartcast;" \
  -f /home/addinedu/dev_ws/SmartCastRobotics_team2/server/smart_cast_db/schema/create_tables.sql \
  -c "SET search_path = smartcast;" \
  -f /home/addinedu/dev_ws/SmartCastRobotics_team2/server/smart_cast_db/seed/seed_master.sql
```

또는 psql 셸 안에서:

```sql
\c <db_name>
DROP SCHEMA IF EXISTS smartcast CASCADE;
CREATE SCHEMA smartcast;
SET search_path = smartcast;
\i /home/addinedu/dev_ws/SmartCastRobotics_team2/server/smart_cast_db/schema/create_tables.sql
\i /home/addinedu/dev_ws/SmartCastRobotics_team2/server/smart_cast_db/seed/seed_master.sql
```
