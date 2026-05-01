# FMS Scenario Plan

## Phase 0. DB baseline

1. `01_create_tables_v22.sql`
2. `02_seed_master_v22.sql`
3. `00_db_connection_check.py`

## Phase 1. Order control

1. `03_create_customer_order.py`
   - customer/user input을 받아 주문 생성
   - `ord`, `ord_detail`, `ord_pp_map`, `ord_txn`, `ord_stat`, `ord_log` 확인
2. `04_admin_approve_order.py`
   - admin이 `RCVD` 주문을 `APPR`로 승인
   - `ord_stat`, `ord_txn`, `ord_log` 변경 확인

## Phase 2. Operator production start

1. `05_operator_start_production.py`
   - operator가 `APPR` 주문 생산 시작
   - `ord_stat = MFG`
   - `item_stat`를 수량만큼 생성
   - 초기 `equip_task_txn` 또는 `item_txn` 생성 여부 검증

## Phase 3. State manager

1. item flow transition 테스트
2. equipment task status transition 테스트
3. transport task status transition 테스트
4. Web/PyQt 화면 반영 확인

## Test policy

- 각 단계는 이전 단계의 output을 다음 단계 input으로 사용합니다.
- 각 파일은 실행 후 사람이 읽을 수 있는 summary를 출력합니다.
- 실패 시 DB transaction은 rollback합니다.
- 같은 테스트를 반복해야 할 때는 새 DB를 만들고 01, 02부터 다시 실행합니다.

