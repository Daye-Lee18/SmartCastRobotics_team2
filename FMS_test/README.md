# FMS Test

FMS 관제 시나리오를 팀원들이 같은 순서로 재현하기 위한 테스트 폴더입니다.

목표는 Web/PyQt 화면만 보는 것이 아니라, DB에 직접 `insert/update/read`를 수행하면서 다음 흐름이 실제로 동작하는지 검증하는 것입니다.

```
고객 발주 생성 → admin 승인 → operator 생산 시작 → item/task/state 변경 → Web/PyQt 확인
```

---

## 폴더 구조

```
FMS_test/
├── README.md
├── .env.example          ← DB 접속 정보 템플릿
├── requirements.txt
├── sql/
│   ├── 01_create_tables_v22.sql
│   └── 02_seed_master_v22.sql
├── python/
│   ├── _db.py                          ← DB 연결 공통 모듈 (직접 실행 X)
│   ├── 00_db_connection_check.py       ← Phase 0: 연결 확인
│   ├── 01_create_tables.py             ← Phase 0-1: 테이블 생성 (처음 한 번만)
│   ├── 02_seed_master.py               ← Phase 0-2: 마스터 데이터 시드 (처음 한 번만)
│   ├── 03_create_customer_order.py     ← Phase 1-1: 주문 생성
│   ├── 04_admin_approve_order.py       ← Phase 1-2: 주문 승인
│   ├── 05_operator_start_production.py ← Phase 2: 생산 시작
│   └── 06_query_order_and_items.py     ← 조회: 주문 + 아이템 상태 확인
└── docs/
    └── scenario_plan.md
```

---

## 처음 실행하는 경우 — 전체 순서

### Step 1. 환경 설정

```bash
cd SmartCastRobotics_team2/FMS_test

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

> `SSL_CERT`는 비워두면 자동으로 프로젝트 루트의 `global-bundle.pem`을 찾아 사용합니다.  
> `DB_SCHEMA`는 비워두면 기본값 `smartcast`를 사용합니다.

### Step 2-1. 테이블 생성 (처음 한 번만)

스키마와 테이블이 아직 없는 경우 실행합니다.

```bash
python python/01_create_tables.py
```

### Step 2-2. 마스터 데이터 시드 (테이블 생성 후 한 번만)

user, product, zone, res, equip 등 기본 마스터 데이터를 넣습니다.  
테이블은 이미 있고 데이터만 없을 때 이 단계만 따로 실행하면 됩니다.

```bash
python python/02_seed_master.py
```

시드 후 아래 항목들이 채워집니다:

| 테이블 | 내용 |
|---|---|
| `user_account` | admin, operator, fms, 고객 2명 |
| `product` / `product_option` | 원형·사각·타원형 맨홀뚜껑 9종 |
| `pp_options` | 표면연마, 방청코팅, 아연도금, 로고삽입 |
| `zone` / `res` / `equip` | 공정 구역 및 로봇 장비 |
| `strg_loc_stat` / `ship_loc_stat` | 보관·출하 슬롯 초기화 |
| `ra_motion_step` | RA 모션 시퀀스 |

### Step 3. DB 연결 확인

```bash
python python/00_db_connection_check.py
```

아래처럼 출력되면 정상입니다.

```
FMS_test DB connection OK
  user_account: 5
  category: 3
  product: 9
  ...
```

---

## 시나리오 실행 순서

> 각 단계는 이전 단계의 결과(ord_id)를 다음 단계 입력으로 사용합니다.

### Phase 1-1. 고객 주문 생성 — Web UI 사용

백엔드와 웹을 실행한 뒤 고객 계정으로 로그인해서 주문을 생성합니다.

```bash
cd SmartCastRobotics_team2
./scripts/run-backend.sh
./scripts/run-web.sh
```

1. 브라우저에서 고객 계정으로 로그인
   - 이민준: `minjun@techbuild.co` / `customer1234`
   - 정수연: `sooyeon@buildworld.kr` / `customer1234`
2. 제품 선택 → 수량·납기일·배송지·후처리 옵션 입력 → 주문 제출
3. 주문 후 DB에 반영됐는지 조회로 확인

```bash
# 가장 최근에 생성된 ord_id 확인
# ord_{num} 이 num을 아래 <생성된 ord_id> 에 넣어주면 됨.  
python python/06_query_order_and_items.py --ord-id <생성된 ord_id>
```

> Web UI가 없거나 빠르게 DB만 테스트하고 싶으면 스크립트로 대체 가능합니다.
> ```bash
> python python/03_create_customer_order.py
> ```

### Phase 1-2. Admin 주문 승인

`--ord-id`에 위에서 만든 ord_id를 넣습니다.

```bash
python python/04_admin_approve_order.py --ord-id 1
```

출력 예시:

```
주문 승인 완료
  ord_id   : 1
  상태     : RCVD  ->  APPR
  다음 단계: python 05_operator_start_production.py --ord-id 1 --operator-id 2
```

### Phase 2. Operator 생산 시작

```bash
python python/05_operator_start_production.py --ord-id 1
```

출력 예시:

```
생산 시작 완료
  ord_id       : 1
  수량          : 3
  상태          : APPR  ->  MFG
  생성된 item_stat (3개):
    item #1: item_stat_id=1  flow_stat=CREATED
    item #2: item_stat_id=2  flow_stat=CREATED
    item #3: item_stat_id=3  flow_stat=CREATED
```

### 언제든지 — 현재 상태 조회

```bash
python python/06_query_order_and_items.py --ord-id 1
```

주문 헤더, 상태 이력, 아이템 전체를 한 번에 출력합니다.

---

## 전체 실행 예시 (복붙용)

```bash
cd SmartCastRobotics_team2/FMS_test
source .venv/bin/activate   # 또는 source /home/addinedu/venv/test_venv/bin/activate

# Phase 0: DB 연결 확인
python python/00_db_connection_check.py

# Phase 1-1: Web UI에서 고객 주문 생성 후 ord_id 확인
python python/06_query_order_and_items.py --ord-id <ord_id>

# Phase 1-2: Admin 승인
python python/04_admin_approve_order.py --ord-id <ord_id>

# Phase 2: 생산 시작
python python/05_operator_start_production.py --ord-id <ord_id>

# 언제든지: 현재 상태 조회
python python/06_query_order_and_items.py --ord-id <ord_id>
```

---

## Web/PyQt 연동 확인

FMS_test에서 DB 상태를 만든 뒤 backend, web, PyQt를 실행해서 화면을 확인합니다.

```bash
cd SmartCastRobotics_team2
./scripts/run-all.sh
```

또는 개별 실행:

```bash
./scripts/run-backend.sh
./scripts/run-web.sh
./scripts/run-pyqt.sh
```

> **주의:** `server/main_service/.env.local`의 `DATABASE_URL`이 FMS_test의 `.env`와 동일한 DB를 가리켜야 Web/PyQt에서 결과를 확인할 수 있습니다.

---

## 테스트 정책

- 각 단계는 이전 단계의 output을 다음 단계 input으로 사용합니다.
- 실패 시 DB transaction은 rollback됩니다.
- 테스트를 처음부터 다시 하려면 DB를 초기화한 뒤 새로운 주문부터 다시 만드세요.
- 각 스크립트는 `--help`로 옵션을 확인할 수 있습니다.

```bash
python python/03_create_customer_order.py --help
```
