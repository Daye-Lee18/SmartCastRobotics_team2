# SPEC-C2: Management TaskManager smartcast v2 스키마 이관 + write 경로 proxy

> 상태: **Iteration 2 (Architect+Critic 반영)** · 작성: 2026-04-20 · 선행: Phase A, B, C-1, D-1, D-2 완료

---

## 1. 배경

V6 canonical 아키텍처 정합 작업의 마지막 단계. Phase C-1 에서 `backend/app/clients/management.py` gRPC 싱글톤과 `/api/management/health` proxy 엔드포인트로 Interface→Management 화살표를 실체화했으나, **실제 write 경로 (StartProduction, ListItems 등) 는 여전히 Interface 가 DB 직접 조작**하고 있다.

canonical 이미지의 Interface↓Management 화살표가 "전체 write 경로 위임" 의미라면, Interface 의 FastAPI 라우트는 업무 로직 없이 gRPC proxy 로만 동작해야 한다. Phase C-2 는 그 요구를 충족한다.

## 2. 문제 진술

### 2.1 스키마 불일치

| 계층 | 파일 | 사용 스키마 | 주요 엔티티 |
|---|---|---|---|
| Interface | `backend/app/routes/production.py:94` `/api/production/start` | smartcast v2 (Confluence 32342045 v59) | `Ord`, `OrdStat`, `Pattern`, `Item`, `EquipTaskTxn` |
| Management | `backend/management/services/task_manager.py` | legacy v47 | `Order`, `WorkOrder`, `OrderDetail` (`cur_stage`) |

Management 의 `task_manager.start_production(order_ids: list[str])` 은 `app.models.models.Order` 를 쿼리하는데, 현 `app.models.models` 에는 `Order` 클래스가 없다 (smartcast 에서는 `Ord`). 실행 시 `ImportError` 가 발생한다 (Phase C-1 smoke test 에서 확인됨).

### 2.2 API 형식 불일치

| 측면 | Interface 현행 | Management 현행 |
|---|---|---|
| 요청 | `POST /api/production/start` body `{"ord_id": 42}` | `StartProductionRequest { repeated string order_ids }` |
| 응답 | `{"ord_id": int, "item_id": int, "equip_task_txn_id": int, "message": str}` | `StartProductionResponse { repeated WorkOrder work_orders }` |
| 트랜잭션 경계 | `OrdStat(MFG) INSERT` + `Item` + `EquipTaskTxn` | `WorkOrder` + `Item[]` |

## 3. 목표와 비목표

### 3.1 목표

1. Management `task_manager.py` 를 smartcast v2 스키마로 재작성한다.
2. proto `StartProductionRequest` 를 ord_id (정수) 기반으로 수정한다.
3. Interface `/api/production/start` 를 Management gRPC 호출로 교체한다.
4. Interface 하위 호환 응답 형식을 유지해 frontend (`src/lib/api.ts`) 를 수정하지 않는다.

### 3.2 비목표

- smartcast v2 스키마 자체 재설계 (v47→v2 재이관 금지 · 이미 완료된 migration)
- 다중 주문 일괄 시작 (현재 UX 는 단건 발주 시작)
- ROS2 publish 통합 (Phase B 에서 분리됨 · Management FMS 시퀀서가 담당)

## 4. 영향 범위

### 4.1 수정 대상 (코드)

| 파일 | 변경 유형 | 설명 |
|---|---|---|
| `backend/management/proto/management.proto` | ❗ BREAKING | `StartProductionRequest` / `StartProductionResponse` 필드 교체 |
| `backend/management/management_pb2*.py` | 재생성 | protoc 재컴파일 |
| `jetson_publisher/generated/management_pb2*.py` | 동기화 | Jetson 측 stub 갱신 (compat 영향 적음 — Jetson 은 WatchConveyorCommands 만 사용) |
| `backend/management/services/task_manager.py` | 전면 재작성 | smartcast ORM 사용 |
| `backend/management/server.py` | 응답 변환 | `_work_order_to_proto` 제거, `_production_start_to_proto` 신설 |
| `backend/app/routes/production.py` | proxy 전환 | `start_production` 핸들러 본문을 `ManagementClient` 호출로 교체 |
| `backend/app/clients/management.py` | API 추가 | `start_production(ord_id: int) -> StartProductionResult` 메서드 |
| `backend/management/services/task_allocator.py` | 제거 또는 갱신 | `allocate(item_id)` 인수 타입이 str 에서 int 로 바뀌면 교정 필요 |
| `backend/management/services/execution_monitor.py` | 재검토 | WatchItems 도 smartcast `Item` 기준으로 이미 동작 — 수정 최소 |

### 4.2 테스트 영향

- `backend/management/tests/` 에 기존 `test_task_manager.py` 가 있다면 smartcast fixture 필요 (현재 없음 확인 요)
- Interface `/api/production/start` 에 대한 integration 테스트 필요 (현재 없음)
- Phase C-1 Health proxy 는 그대로 유지 — 회귀 없음

### 4.3 프론트엔드 영향

- `src/lib/api.ts` 의 `POST /api/orders/{id}/status` · `GET /api/orders/...` 등은 무변경
- `POST /api/production/start` 호출자 (`src/app/admin/...` 페이지) 가 응답 형식 의존 중인지 확인 필요
- 응답 shape 유지 가정 시 프론트엔드 무변경

## 5. 설계안

### 5.1 proto 변경

```proto
// BEFORE (legacy v47 형식)
message StartProductionRequest {
  repeated string order_ids = 1;
}
message StartProductionResponse {
  repeated WorkOrder work_orders = 1;
}

// AFTER (smartcast v2 형식)
message StartProductionRequest {
  int32 ord_id = 1;    // smartcast ord.ord_id (정수 PK)
  // 향후 다중 시작이 필요해지면 repeated 추가 RPC 신설
}

message StartProductionResult {
  int32  ord_id            = 1;
  int32  item_id           = 2;   // 생성된 첫 item
  int32  equip_task_txn_id = 3;   // RA1/MM QUE 트랜잭션 ID
  string message           = 4;   // "Production started: RA1/MM task queued."
}

message StartProductionResponse {
  StartProductionResult result = 1;
}
```

### 5.2 task_manager 재작성

```python
# backend/management/services/task_manager.py (재작성 골격)
from app.database import SessionLocal
from app.models import Ord, OrdStat, Pattern, Item, EquipTaskTxn

class TaskManager:
    def start_production(self, ord_id: int) -> StartProductionResult:
        """smartcast v2: 단일 발주 생산 개시. Interface production.py:94 로직과 동일."""
        with SessionLocal() as db:
            ord_obj = db.get(Ord, ord_id)
            if not ord_obj:
                raise ValueError(f"ord_id={ord_id} not found")
            if not db.get(Pattern, ord_id):
                raise ValueError(f"pattern for ord_id={ord_id} not registered")

            db.add(OrdStat(ord_id=ord_id, ord_stat="MFG"))
            new_item = Item(
                ord_id=ord_id, equip_task_type="MM",
                cur_stat="QUE", cur_res="RA1",
            )
            db.add(new_item)
            db.flush()
            txn = EquipTaskTxn(
                res_id="RA1", task_type="MM", txn_stat="QUE",
                item_id=new_item.item_id,
            )
            db.add(txn)
            db.commit()
            db.refresh(new_item)
            db.refresh(txn)

            return StartProductionResult(
                ord_id=ord_id,
                item_id=new_item.item_id,
                equip_task_txn_id=txn.txn_id,
                message="Production started: RA1/MM task queued.",
            )
```

### 5.3 Interface proxy 전환

```python
# backend/app/routes/production.py
from app.clients.management import ManagementClient, ManagementUnavailable

@router.post("/start")
def start_production(payload: ProductionStartRequest):
    """Management gRPC StartProduction proxy.
    canonical: Interface 는 HTTP↔gRPC 변환만 담당. 비즈니스 로직은 Management."""
    try:
        result = ManagementClient.get().start_production(payload.ord_id)
    except ManagementUnavailable as e:
        raise HTTPException(503, f"Management Service unavailable: {e}")
    except ValueError as e:  # not found / pattern missing
        raise HTTPException(400, str(e))
    return {
        "ord_id": result.ord_id,
        "item_id": result.item_id,
        "equip_task_txn_id": result.equip_task_txn_id,
        "message": result.message,
    }
```

### 5.4 ManagementClient 확장

`backend/app/clients/management.py` 에 추가:
```python
def start_production(self, ord_id: int) -> management_pb2.StartProductionResult:
    self._ensure_channel()
    try:
        resp = self._stub.StartProduction(
            management_pb2.StartProductionRequest(ord_id=ord_id),
            timeout=self._timeout,
        )
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            raise ValueError(e.details()) from e
        raise ManagementUnavailable(
            f"StartProduction failed: {e.code()}",
        ) from e
    return resp.result
```

## 6. 마이그레이션 전략

### 6.1 Feature flag (선택)

`INTERFACE_PROXY_START_PRODUCTION=1` (기본 0) 환경변수로 Interface 에서 proxy vs 직접 DB 경로를 토글 가능하게 한다. 실기 배포 중 Mgmt 장애 시 즉시 롤백 가능.

```python
if os.environ.get("INTERFACE_PROXY_START_PRODUCTION", "0") in ("1", "true"):
    result = ManagementClient.get().start_production(payload.ord_id)
else:
    # legacy 경로 (DB 직접)
    ...
```

### 6.2 롤아웃 순서

1. proto 변경 + 재컴파일 (Jetson 영향 없음 — Jetson 은 WatchConveyorCommands 만 사용)
2. Management `task_manager.py` 재작성 + pytest fixture 추가
3. `ManagementClient.start_production` 메서드 추가
4. Interface 라우트 proxy 전환 (feature flag 뒤)
5. 스테이징 환경에서 feature flag ON 으로 E2E 테스트
6. 운영 rollout + flag default 를 ON 으로 전환
7. 2주 후 legacy 경로 삭제 (feature flag 제거)

### 6.3 롤백 계획

- Feature flag OFF → 즉시 legacy 경로 복귀 (DB 상태 영향 없음)
- Mgmt 서버만 rollback 불가 시 Interface 는 flag OFF 로 운영 지속
- proto 변경은 breaking 이나 Jetson/PyQt 클라이언트는 StartProduction 미사용 → 호환 문제 없음 (PyQt 는 [▶ 생산 시작] 버튼이 FastAPI HTTP 로 호출 중)

## 7. 테스트 계획

### 7.1 단위 테스트

- `tests/test_task_manager_smartcast.py` (신규): `start_production` 의 4가지 케이스
  - 정상: ord 존재 + pattern 등록됨 → OrdStat/Item/EquipTaskTxn 3건 INSERT
  - ord 미존재: ValueError
  - pattern 미등록: ValueError
  - OrdStat 중복 MFG: 허용 (이력 테이블이므로 중복 가능)

### 7.2 통합 테스트

- `tests/test_production_proxy.py` (신규): FastAPI TestClient + in-process Mgmt server
  - `POST /api/production/start {"ord_id": 42}` → 200 + 응답 shape 검증
  - Mgmt 미가동 시 503
  - `ord_id=0` → 400 (INVALID_ARGUMENT from gRPC)

### 7.3 E2E 시나리오

1. 관리자 PC 에서 `POST /api/production/patterns` 패턴 등록
2. `POST /api/production/start {"ord_id": 42}` 호출
3. PyQt 에서 `ListItems` gRPC 로 새 item 확인
4. PyQt 에서 EquipTaskTxn status=QUE 확인 (smartcast schema)

## 8. 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| Management 내 `sys.path.insert(_BACKEND_DIR)` 가 app.\* import 를 보장함에도 `app.database.engine` 초기화 시점 충돌 | Mgmt 기동 실패 | Mgmt 도 동일 DATABASE_URL 사용 + 테스트로 기동 검증 |
| proto breaking 변경이 외부 subscriber 에 전파 | ImagePublisher/PyQt 호환성 | StartProduction 은 내부 proxy 경로만 사용. 외부 클라이언트 이용 없음 확인 |
| Interface FastAPI 응답 shape 변경으로 프론트엔드 회귀 | Admin UI 깨짐 | 응답 dict 키 4개 (`ord_id`, `item_id`, `equip_task_txn_id`, `message`) 유지 — 기존과 완전히 동일 |
| pattern FK 가 Management 프로세스에서 조회 안 될 경우 | 생산 시작 실패 | Phase C-1 과 동일하게 DB connection string 공유 — 스테이징 검증 필수 |
| `db.flush()` 후 `db.refresh()` 타이밍 이슈 | race condition 가능성 | pytest + TestClient 로 반복 실행 검증 |

## 9. 완료 조건 (Definition of Done)

- [ ] proto 재컴파일, Jetson generated/ 동기화
- [ ] Management `task_manager.start_production` 재작성 + 단위 테스트 4개 PASS
- [ ] `ManagementClient.start_production` 메서드 추가 + 예외 변환
- [ ] Interface `POST /api/production/start` proxy 동작 + feature flag
- [ ] 통합 테스트 (TestClient + in-process Mgmt) 통과
- [ ] 스테이징에서 flag ON E2E 성공 (item 1건 생성)
- [ ] 기존 frontend 페이지 회귀 없음 (수동 smoke: 패턴 등록 → 생산 시작 → items 테이블 노출)
- [ ] 운영 rollout 후 2주 유예 + legacy 경로 제거 PR (별도)

## 10. 해결된 결정 사항 (Iteration 2 확정)

1. **단건 vs 다중**: **단건 확정** (`StartProductionRequest { int32 ord_id = 1 }`). 현 Interface UX 와 일치. 다중 필요 시 별도 `StartProductionBatchRequest` 신규 RPC 로 추가 (본 SPEC 범위 외).
2. **`TaskAllocator.allocate`**: **본 SPEC 범위 외**. smartcast 에서 미사용 상태로 유지. 향후 별도 SPEC-C3 에서 다룸.
3. **`WorkOrder` proto 메시지**: **Option B 유지**. 메시지 정의는 남기되 `StartProductionResponse` 에서 사용하지 않음. 향후 다중 발주 concept 복원 시 재사용. BREAKING 변경 최소화.

## 11. Architect/Critic 추가 리스크 반영 (Iteration 2)

### 11.1 SPOF 이동 · 레이턴시 예산 (Principle #4 재서술)

**기존**: "트랜잭션 경계 동일"
**개정**: "트랜잭션 atomic 은 Management 단일 프로세스에서 보장. Interface 는 synchronous gRPC proxy 로 동작하며 latency = HTTP + gRPC + DB commit 을 허용한다."

레이턴시 예산: 기존 `HTTP(50ms) + DB commit(100ms) ≈ 150ms` → 변경 후 `HTTP(50ms) + gRPC(20ms) + DB commit(100ms) ≈ 170ms`. 20ms 증분 허용.

Mgmt 가 느리면 Interface HTTP worker 가 gRPC timeout (기본 3s) 까지 블록 → `MANAGEMENT_GRPC_TIMEOUT` 을 1.5s 로 하향, 상위 504 반환 전략.

### 11.2 Feature flag 다중-worker race 완화

**문제**: uvicorn `--workers N` 시 각 worker 가 env 를 독립 읽음. 라이브 flip 중 worker 별 다른 경로로 분기.

**완화**: flag 를 **모듈 import 시점 상수**로 고정:
```python
# backend/app/routes/production.py
_PROXY_START_PRODUCTION = os.environ.get(
    "INTERFACE_PROXY_START_PRODUCTION", "0"
) in ("1", "true")
```
Flip 하려면 **모든 worker 재시작** (`systemctl restart` 또는 `kill -HUP` on master) 필수. 운영 런북에 기록.

### 11.3 DB connection pool 고갈 완화

**문제**: Management 가 gRPC 요청당 새 `SessionLocal()` 컨텍스트 + 3-INSERT 트랜잭션. 동시 요청 많으면 PG pool (`pool_size=5` 기본) 고갈 가능.

**완화**: `DATABASE_URL` 에 `pool_size=10&max_overflow=20` 옵션 추가 후 부하 테스트로 확인. `services/command_queue` 와 동일 패턴 사용.

### 11.4 ORM 스키마 drift 완화

**문제**: Interface `app/models/models.py` 가 Alembic 마이그레이션 따라 진화. Management 프로세스는 시작 시점 정의를 메모리에 고정. Interface 만 재시작하면 양측 ORM 이 달라짐.

**완화**: `backend/deploy/release.sh` 에 **두 서비스 동시 재시작** 강제. CI 에 ORM 해시 비교 test:
```python
def test_orm_version_pinned():
    import app.models.models as m
    assert hasattr(m, "Ord") and hasattr(m, "EquipTaskTxn")
    # SPEC-C2 생성 시점 기준 tag 고정
    assert m.Ord.__table__.columns.keys() == ["ord_id", "cust_id", "p_id", ...]
```

### 11.5 sys.path hack 중립화

**문제**: Management 가 `sys.path.insert(_BACKEND_DIR)` 로 `app.*` import — 본 SPEC 에서도 존속.

**완화 (현 SPEC 범위 외, 후속 SPEC)**: shared package `backend/common/` 로 `models/`, `database.py` 이관. SPEC-C4 로 기록.

## 12. 확장 테스트 계획 (Iteration 2)

### 12.1 Unit · PG fixture 전략

**채택**: `pytest-postgresql` (ephemeral PG 인스턴스 per test session). SQLite/in-memory 금지 (feedback_db_postgresql_only 2026-04-14 policy).

```toml
# backend/pyproject.toml 또는 conftest.py
pytest-postgresql = ">=6.0"
```

### 12.2 Proto round-trip equality test (신규 · CI 필수)

```python
# backend/management/tests/test_proto_sync.py
def test_proto_stubs_synced():
    """backend/management/ 와 jetson_publisher/generated/ 의 pb2 가 동일 descriptor."""
    import sys
    sys.path.insert(0, str(ROOT / "backend" / "management"))
    sys.path.insert(0, str(ROOT / "jetson_publisher" / "generated"))
    import management_pb2 as b
    sys.path.pop(0); sys.path.pop(0)
    import importlib, jetson_publisher.generated.management_pb2 as j
    assert b.DESCRIPTOR.serialized_pb == j.DESCRIPTOR.serialized_pb
```

### 12.3 Characterization test (legacy 동결)

Phase C-2 착수 직전, 현 Interface `/api/production/start` 응답을 JSON 문자열로 고정:
```python
# backend/tests/test_production_characterization.py
EXPECTED = {
    "ord_id": 42, "item_id": 1, "equip_task_txn_id": 1,
    "message": "Production started: RA1/MM task queued.",
}
def test_legacy_response_shape_pinned(client, seed_ord_and_pattern):
    r = client.post("/api/production/start", json={"ord_id": 42})
    assert r.status_code == 200
    assert set(r.json().keys()) == set(EXPECTED.keys())
```
Proxy 전환 후 동일 key set 반환 보장.

### 12.4 사전-rebuild grep 검증

```bash
# Phase C-2 브랜치 생성 직후 최초 명령
grep -rn "StartProduction\|start_production" monitoring/ jetson_publisher/ --include='*.py'
```
**기대 결과**: `jetson_publisher/command_subscriber.py`(미사용), `jetson_publisher/generated/management_pb2*.py`(자동생성) 외 **0건**. 다른 매치 발견 시 proto 재컴파일 전에 해당 호출처 이관 작업 추가.

### 12.5 통합 테스트 · PG 전략 명세

`tests/test_production_proxy.py`:
- `pytest_postgresql` 플러그인 이 `postgresql_proc` fixture 제공 → ephemeral PG startup
- `FastAPI TestClient` 가 Interface `/api/production/start` 호출
- 별도 스레드에서 `grpc.server(ThreadPoolExecutor(max_workers=1))` 기동, `MinimalManagementServicer` 등록
- Mgmt gRPC stub 이 동일 ephemeral PG `DATABASE_URL` 사용 → 실제 Commit 경로 검증

### 12.6 E2E CI 게이트 (§9 DoD 보강)

| 검증 | 명령 | 기대 |
|---|---|---|
| proto round-trip | `pytest backend/management/tests/test_proto_sync.py` | PASS |
| task_manager 단위 | `pytest backend/management/tests/test_task_manager_smartcast.py -v` | 4 case PASS |
| ManagementClient gRPC 예외 | `pytest backend/tests/test_management_client.py -v` | PASS |
| proxy integration | `pytest backend/tests/test_production_proxy.py -v` | PASS |
| characterization | `pytest backend/tests/test_production_characterization.py -v` | PASS |
| grep clean | `! grep -rn "StartProduction" monitoring/ --include='*.py'` | 0 matches |

## 13. 업데이트된 완료 조건 (Iteration 2)

- [ ] §10 모든 미결정 해결 (Iter 2 에서 확정)
- [ ] proto 재컴파일 + `test_proto_sync` PASS
- [ ] `task_manager.start_production` 재작성 + 단위 테스트 4개 PASS (pytest-postgresql)
- [ ] `ManagementClient.start_production` + gRPC 예외 매핑 단위 테스트
- [ ] Interface proxy + 모듈 import 시점 flag 고정 + 통합 테스트 PASS
- [ ] Characterization 테스트로 응답 shape 동결 증명
- [ ] grep clean (§12.4)
- [ ] ORM 해시 비교 테스트 PASS
- [ ] Connection pool 부하 테스트 통과 (20 concurrent 가동)
- [ ] 스테이징 flag ON E2E 성공 + 운영 런북 작성 (worker 재시작 방법 포함)
- [ ] 2주 유예 + legacy 제거 PR (별도)

---

## 작성자 검토 체크리스트

- [ ] 영향 범위 누락 없음 (`backend/`, `monitoring/`, `jetson_publisher/`, `src/` 모두 확인)
- [ ] 마이그레이션 롤백 계획 실행 가능 (feature flag 검증)
- [ ] Data integrity: 트랜잭션 경계가 Interface 와 Management 에서 동일
- [ ] 운영 배포 시 Mgmt 재시작 지침 (Phase D-1 에서 이미 필요 — 함께 릴리즈 가능)

SPEC 승인 후 → Phase C-2 구현 착수.
