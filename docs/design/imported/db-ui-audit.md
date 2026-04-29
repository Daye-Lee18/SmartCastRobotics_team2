> **2026-04-14 추가**: 본 감사는 기존 FastAPI 단일 서버 기준이다. V6 아키텍처 전환 후에는
> Management Service(gRPC :50051) 가 대부분의 쓰기 경로를 담당한다. 스키마 자체는 공유 DB 를
>유지하므로 감사 결과(삭제 후보 0건)는 그대로 유효. 설계: `docs/management_service_design.md`.

# DB ↔ UI 정합성 감사 (2026-04-14)

> 기준: UI(PyQt monitoring + Next.js web)에 노출되지 않는 컬럼은 삭제 후보.
> 단, backend routes/schemas/WebSocket payload/FK/seed 에서 **내부 사용**되는 컬럼은 유지.
> 본 문서는 **dry-run**. 실제 DROP/ALTER 는 사용자 별도 승인 시에만 실행.

---

## 1. 요약

| 항목 | 값 |
|---|---|
| DB 테이블 수 | **15** |
| 총 컬럼 수 (추정) | 약 130 |
| UI 직접 표시 컬럼 | 약 52 |
| 내부 사용(INTERNAL) | 약 70 |
| 삭제 후보(ORPHAN) | **0** (재검증 결과: 모든 테이블이 UI 또는 내부에서 사용 중) |
| 운영 PG 반영 권장 | 조건부 — 본 감사 결과 0건이므로 작업 없음 (2026-04-14 SQLite 폴백 제거됨) |

결론: "UI에 없으면 전부 삭제"를 **단순 적용하면 안 됩니다**. 대부분의 비표시 컬럼은 route 응답, WS payload, seed, FK 제약, 가격/상태 계산 등 내부 로직에서 사용됩니다. 진짜 orphan 은 제한적입니다.

---

## 2. 방법론

### 2.1 UI 수집 범위

- **PyQt**: `monitoring/app/pages/*.py` 6개 페이지의 `QTableWidget` 헤더, `QLabel` 바인딩, 게이지/차트 입력
- **Next.js**: `src/app/**/page.tsx` (admin, customer, orders, production, quality)
- `monitoring/app/api_client.py` 의 `normalize_*` 함수가 **드롭**하는 필드는 UI 미사용으로 간주

### 2.2 내부 사용 판단 기준

| 신호 | 의미 |
|---|---|
| FK 참조 | 삭제 불가 (데이터 무결성) |
| backend route response | API 응답 스키마에 포함 → 삭제 시 API 계약 깨짐 |
| seed.py | 초기 데이터 구조에 포함 |
| websocket.py | 실시간 broadcast payload |
| 계산/집계 로직 | group_by, filter, sum 등에 사용 |

### 2.3 분류 체계

- **DISPLAYED** — 최소 1개 UI에서 직접 표시
- **INTERNAL** — UI 미표시지만 backend 또는 데이터 무결성에 필요
- **ORPHAN** — UI·내부 모두 미사용 → **삭제 후보**

---

## 3. UI 컬럼 매핑 (Top-level)

### 3.1 PyQt Table 헤더 전체

| 페이지 | 테이블 | 헤더 |
|---|---|---|
| dashboard | 최근 주문 | 고객사, 금액, 납기, 상태 |
| production | 공정 단계 | 단계, 상태, 담당 설비 |
| production | 주문별 제품 실시간 위치 | 주문, 제품, Item, 대기, 주탕, 탈형, 후처리, 검사, 적재 |
| production | 공정 파라미터 이력 | 시각, 공정, 온도, 압력, 각도, 출력, 냉각률, 진행률 |
| schedule | 주문 리스트 | 주문 ID, 회사명, 납기, 금액, 상태 |
| schedule | 우선순위 결과 | 순위, 주문 ID, 회사명, 총점, 지연위험, 착수 |
| quality | 검사 기록 | 이미지, 검사 시각, 제품, 결과, 불량 유형, 담당자, 비고 |
| logistics | 이송 작업 | 우선순위, 작업 ID, 경로, 화물, 담당 AMR, 상태 |
| logistics | 출고 주문 | 주문 ID, 제품, 수량, 납품처, 정책, 상태 |

### 3.2 Next.js 주요 표시 필드

| 섹션 | 주요 필드 |
|---|---|
| customer/lookup | order.id, contact, 제품명, 수량, material, spec |
| customer/orders | 제품 카탈로그 (products.name, spec, base_price, material) |
| admin | orders 전체, products 관리 (logo_data 포함) |
| production | 공정 단계/파라미터 (PyQt 와 동일 API) |
| quality | inspection 결과, inspection_standards.threshold |

---

## 4. 테이블별 컬럼 분석

범례: 🟢 DISPLAYED · 🟡 INTERNAL · 🔴 ORPHAN

### 4.1 `orders`

| 컬럼 | UI 표시 | 내부 사용 | 분류 | 비고 |
|---|---|---|---|---|
| id | ✅ PyQt+Next | - | 🟢 | PK |
| customer_id | - | Next admin FK | 🟡 | |
| customer_name | ✅ dashboard 고객사 | - | 🟢 | |
| company_name | ✅ schedule 회사명 | - | 🟢 | |
| contact | ✅ customer/lookup | - | 🟢 | |
| shipping_address | - | orders route response | 🟡 | 상세 뷰에서 필요 |
| total_amount | ✅ 금액 | - | 🟢 | |
| status | ✅ 상태 | - | 🟢 | |
| requested_delivery | ✅ 납기 | - | 🟢 | |
| confirmed_delivery | - | orders route response | 🟡 | |
| created_at | - | 정렬/집계 | 🟡 | |
| updated_at | - | 캐시 무효화 | 🟡 | |
| notes | - | orders route response | 🟡 | 비고 필드 |

**DROP 후보: 없음**

### 4.2 `products`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, name, category, base_price | ✅ customer/orders | - | 🟢 |
| option_pricing_json | ✅ customer (옵션 가격) | - | 🟢 |
| design_image_url | ✅ customer 카탈로그 이미지 | - | 🟢 |
| model_3d_path | ✅ customer 3D 뷰어 | - | 🟢 |

**DROP 후보: 없음**

### 4.3 `process_stages` ⚠️ 주의

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, stage, label, status, equipment_id | ✅ 공정 단계 | - | 🟢 |
| temperature, pressure, pour_angle, heating_power, cooling_progress | ✅ **공정 파라미터 이력 / 게이지** | - | 🟢 |
| target_temperature | - | routes/production.py 계산 (`delta = (target - current) * 0.05`) | 🟡 |
| progress | - | WebSocket process_stage_update payload | 🟡 |
| start_time | - | 정렬/집계 | 🟡 |
| estimated_end | - | route response | 🟡 |
| order_id, job_id | - | FK / 연결 키 | 🟡 |

> **경고**: 오늘 UI(`공정 단계 테이블`)에서 **표시** 컬럼만 `progress/start_time` 제거했습니다. 해당 DB 컬럼은 **WS/계산 로직이 계속 사용** 중이므로 **DROP 금지**. API 응답에서만 숨기고 싶으면 routes/production.py 에서 필드 제거 가능.

**DROP 후보: 없음**

### 4.4 `equipment`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, name, type, status | ✅ 설비 목록 / 공정 단계 | - | 🟢 |
| pos_x, pos_y, pos_z | ✅ map 3D | - | 🟢 |
| battery, speed | ✅ AMR 카드 | - | 🟢 |
| last_maintenance | ✅ dashboard last_checked | - | 🟢 |
| comm_id | - | MQTT/시리얼 연결 식별자 | 🟡 |
| install_location | - | equipment route response | 🟡 |
| last_update | - | 센서 업데이트 tracking | 🟡 |
| operating_hours | - | 정비 스케줄 계산 | 🟡 |
| error_count | - | alerts 집계 | 🟡 |

**DROP 후보: 없음**

### 4.5 `alerts`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, type, severity, message, timestamp | ✅ 알림 토스트 | - | 🟢 |
| equipment_id | - | FK | 🟡 |
| error_code | - | route response | 🟡 |
| abnormal_value | - | route response | 🟡 |
| zone | - | route response | 🟡 |
| resolved_at | - | 해결 시각 | 🟡 |
| acknowledged | - | 필터 `WHERE acknowledged=False` | 🟡 |

**DROP 후보: 없음**

### 4.6 `inspection_records`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, inspected_at, result, defect_type | ✅ quality 테이블 | - | 🟢 |
| product_id, casting_id | ✅ 제품 | - | 🟢 |
| inspector_id | - | 집계 `inspector_stats` | 🟡 |
| defect_type_code | - | 집계 `defect_type_codes` | 🟡 |
| confidence | - | 임계값 판정 | 🟡 |
| image_id | - | 이미지 참조 | 🟡 |
| order_id | - | FK/조인 | 🟡 |
| defect_detail | - | route response | 🟡 |

**DROP 후보: 없음**

### 4.7 `inspection_standards`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, product_id, product_name, threshold | ✅ Next.js 검사 기준 | - | 🟢 |
| tolerance_range, target_dimension | - | route response (상세 조회 가능성) | 🟡 |

**DROP 후보: 없음 (상세 조회 UI 추가 가능성 고려)**

### 4.8 `sorter_logs` 🟢 (정정 2026-04-14)

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id | - | PK | 🟡 |
| inspection_id | ✅ Next.js `/quality` 검사 ID 라벨 | - | 🟢 |
| sort_direction | ✅ Next.js `/quality` pass/fail 표시 | - | 🟢 |
| sorter_angle | ✅ Next.js `/quality` 분류기 각도 회전 애니메이션 | - | 🟢 |
| success | ✅ Next.js `/quality` 성공/실패 상태 | - | 🟢 |

> **정정**: 초안에서 ORPHAN 으로 분류했던 부분은 PyQt 만 검색한 오류였습니다. `src/app/quality/page.tsx` 의 372~427 라인에서 `latestSorter.sorterAngle`, `sortDirection`, `success`, `inspectionId` 를 시각적으로 렌더링합니다. **유지**.

**DROP 후보: 없음**

### 4.9 `transport_tasks`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, priority, status | ✅ logistics 테이블 | - | 🟢 |
| from_name, to_name | ✅ 경로 | - | 🟢 |
| item_name, quantity | ✅ 화물 | - | 🟢 |
| assigned_robot_id | ✅ 담당 AMR | - | 🟢 |
| from_coord, to_coord | - | map 시각화 | 🟡 |
| item_id | - | FK | 🟡 |
| requested_at, completed_at | - | 집계 | 🟡 |

**DROP 후보: 없음**

### 4.10 `warehouse_racks`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, zone, status, item_name, quantity | ✅ logistics 창고 | - | 🟢 |
| rack_number, row, col | ✅ 랙 좌표 | - | 🟢 |
| item_id | - | FK | 🟡 |
| last_inbound_at | - | 정렬 | 🟡 |

**DROP 후보: 없음**

### 4.11 `outbound_orders`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, product_name, quantity, destination, policy | ✅ logistics 출고 | - | 🟢 |
| product_id | - | FK | 🟡 |
| completed | - | 필터 | 🟡 |
| created_at | - | 정렬 | 🟡 |

**DROP 후보: 없음**

### 4.12 `production_metrics`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| date, production, defects, defect_rate | ✅ dashboard/production 차트 | - | 🟢 |

**DROP 후보: 없음**

### 4.13 `priority_change_logs` 🔴

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| order_id, old_rank, new_rank, reason, changed_by, changed_at | - | schedule.py 기록만, UI 표시 없음 | 🟡 |

> 감사 로그 성격. UI 미표시지만 "왜 우선순위가 바뀌었는지" 추적에 필요. **유지 권장**. UI 추가 전 삭제는 보수적으로 금지.

**DROP 후보: 없음 (내부 감사용)**

### 4.14 `order_details`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| order_id, product_name, quantity | ✅ Next.js 주문 상세 | - | 🟢 |
| spec, material | ✅ Next.js customer | - | 🟢 |
| post_processing, logo_data | ✅ admin 주문 상세 | - | 🟢 |
| unit_price, subtotal | ✅ 금액 계산 | - | 🟢 |
| product_id | - | FK | 🟡 |

**DROP 후보: 없음**

### 4.15 `production_jobs`

| 컬럼 | UI | 내부 | 분류 |
|---|---|---|---|
| id, order_id | - | FK / job tracking | 🟡 |
| priority_score, priority_rank | ✅ schedule 순위/총점 | - | 🟢 |
| assigned_stage | - | schedule 할당 계산 | 🟡 |
| status | - | 필터 | 🟡 |
| estimated_completion | - | 지연위험 계산 | 🟡 |
| started_at, completed_at, created_at | - | 시간 추적 | 🟡 |

**DROP 후보: 없음**

---

## 5. 통합 삭제 계획 (dry-run)

### 5.1 안전 삭제 (UI·내부 모두 미사용) — **0건 (정정)**

재검증 결과 `sorter_logs` 는 Next.js `/quality` 페이지에서 실제 렌더링되어 삭제 대상 아님. 현 시점 안전 drop 후보 없음.

### 5.2 검토 필요 (UI엔 없지만 내부 사용)

아래는 **UI에 안 나오지만 route 응답/계산에 포함**. 제거하려면 route 응답 필드도 동시 제거 필요.

```sql
-- ❗ 다음 모두 backend 참조 있음. 실행 시 routes/*.py 함께 수정.
-- ALTER TABLE orders DROP COLUMN shipping_address;     -- orders 상세 응답
-- ALTER TABLE orders DROP COLUMN confirmed_delivery;    -- orders 응답
-- ALTER TABLE orders DROP COLUMN notes;                 -- orders 응답
-- ALTER TABLE equipment DROP COLUMN comm_id;            -- 하드웨어 연결 ID
-- ALTER TABLE equipment DROP COLUMN install_location;   -- equipment 응답
-- ALTER TABLE inspection_standards DROP COLUMN tolerance_range;
-- ALTER TABLE inspection_standards DROP COLUMN target_dimension;
```

→ **권장**: 당장 drop 금지. UI가 "상세 보기/편집" 뷰를 추가할 가능성 높음.

### 5.3 유지 (내부 핵심)

- `process_stages.progress/start_time/target_temperature/pressure/heating_power/cooling_progress/pour_angle` — 공정 파라미터 이력 UI 및 routes/production.py 계산 로직에서 사용
- `priority_change_logs.*` — 감사 로그
- 모든 FK 컬럼 (customer_id, order_id, product_id, equipment_id, item_id, inspection_id)
- 모든 `*_at` timestamp — 정렬·집계에 필요

---

## 6. 실행 순서 권장안

### Step 1 — `sorter_logs` 실제 미참조 재확인 (5분)

```bash
grep -rn "sorter_log\|SorterLog\|sort_direction\|sorter_angle" \
  backend/ src/ monitoring/ --include="*.py" --include="*.tsx" --include="*.ts"
```

참조가 나오면 유지, 없으면 Step 2 진행.

### Step 2 — backend 코드 정리

1. `backend/app/models/models.py` — `SorterLog` 클래스 제거
2. `backend/app/schemas/schemas.py` — 관련 Pydantic 제거
3. `backend/app/seed.py` — 시드 블록 제거
4. `backend/app/routes/quality.py` — import/쿼리 제거

### Step 3 — PostgreSQL DB 적용 (SQLite 단계 폐지)

```bash
cd backend
source venv/bin/activate
# 백업 (운영 PG)
pg_dump $DATABASE_URL -t sorter_logs -F c -f /tmp/sorter_logs.dump
# 드롭
psql $DATABASE_URL -c "DROP TABLE IF EXISTS sorter_logs;"
# 회귀 검증
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
curl -s http://localhost:8000/docs -o /dev/null -w "%{http_code}\n"  # 200 확인
# PyQt 기동 확인
cd ../monitoring && CASTING_API_HOST=localhost python main.py
```

### Step 4 — Next.js 빌드 회귀

```bash
cd /Users/ibkim/Project/casting-factory
npm run build
```

### Step 5 — 운영 PostgreSQL 반영 (별도 승인 필요)

운영 DB @ `100.107.120.14` 반영 전:

1. `DATABASE_URL=postgresql+psycopg://...` 환경에서 dev 테스트 통과
2. PG 백업: `pg_dump -h 100.107.120.14 -U team2 smartcast_robotics > backup-YYYYMMDD.sql`
3. TimescaleDB hypertable 여부 확인
   ```sql
   SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name='sorter_logs';
   ```
4. hypertable 이면 `SELECT drop_hypertable('sorter_logs');` 또는 일반 `DROP TABLE` 사용
5. 사용자 승인 후 실행

---

## 7. 운영 PG 반영 시 추가 체크

| 체크 항목 | 명령 |
|---|---|
| 현재 데이터 백업 | `pg_dump -h 100.107.120.14 -U team2 -d smartcast_robotics -t sorter_logs -F c -f sorter_logs.dump` |
| hypertable 여부 | `SELECT * FROM timescaledb_information.hypertables;` |
| 사용자 권한 | `team2` 역할이 DROP 권한 보유 확인 |
| 실제 데이터 건수 | `SELECT count(*) FROM sorter_logs;` — 0 이면 안심 |
| 복구 절차 | 백업 dump 로 `pg_restore` 로 복원 가능 확인 |

---

## 8. 부록: PyQt `api_client.py` 에서 드롭되는 원본 필드

아래 필드는 API 응답에는 있지만 PyQt 가 normalize 에서 버리므로 **PyQt UI 에 결코 표시되지 않음** (단, Next.js 는 원본을 직접 쓸 수 있음).

- equipment 응답의 `pos_x/y/z`, `battery`, `speed` 일부 → PyQt 테이블 미사용이나 map 페이지에서 사용
- inspection 응답의 `confidence`, `image_id` → PyQt 미표시

→ 이런 경우는 "UI 전체"가 아닌 "특정 UI"가 미표시인 것이므로 drop 대상 아님.

---

## 9. 결론

**"UI 미표시 = DB drop" 규칙을 문자 그대로 적용하면 backend API 응답, WS broadcast, 계산 로직, FK 가 붕괴**합니다.

재검증(2026-04-14) 결과 **안전 삭제 후보 0건**. 15개 테이블 모두 PyQt 또는 Next.js UI 중 최소 한쪽에서 사용됩니다.

**향후 삭제 검토 시 체크리스트**
- [ ] PyQt `pages/*.py` 의 `QTableWidget` / `QLabel` / 게이지 바인딩
- [ ] Next.js `src/app/**/page.tsx` 의 JSX 렌더링 (필드명은 camelCase 로 매핑됨)
- [ ] `src/lib/api.ts` 의 fetch 함수
- [ ] `src/lib/types.ts` 의 interface
- [ ] backend `routes/*.py` 응답, `websocket.py` broadcast, `schemas.py` Pydantic
- [ ] `seed.py` 의 초기 데이터
