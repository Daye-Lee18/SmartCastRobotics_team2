# Approval -> Production Start Verification

`smart_cast_db` 기준으로 관리자 웹 승인 후 PyQt 생산 시작까지 이어지는지 확인하는 절차.

## 0. Port forwarding

로컬 PC에서 `8000` 포트는 한 프로세스만 바인딩할 수 있다.

아래 둘을 **동시에 별도 터널로 띄우면 충돌**할 수 있다.

```bash
ssh -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@192.168.1.24 -N
ssh -X -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@192.168.1.24 -N
```

권장 방법:

1. 웹과 PyQt를 **같은 SSH 세션**에서 함께 쓰기
2. 또는 한쪽은 `8000`, 다른 한쪽은 다른 로컬 포트로 변경하기

PyQt GUI를 원격 화면에 띄워야 하면 `-X` 를 붙인다.

```bash
ssh -X -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@192.168.1.24 -N
```

웹만 보면 되면 `-X` 없이 `-L` 만 써도 된다.

## 1. Start interface service

원격 서버에서:

```bash
cd /home/addinedu/dev_ws/SmartCastRobotics_team2/server/main_service/src/interface_service
uvicorn app.main:app --reload --port 8000
```

health check:

```bash
curl http://127.0.0.1:8000/health
```

expected:

```json
{"status":"ok","service":"casting-factory-api"}
```

## 2. Create an order

웹에서 고객 주문을 먼저 생성한다.

필수:

- 주문 생성 완료
- `ord_id` 확보
- 패턴 등록 완료

즉, `OrdPattern` 이 있어야 생산 시작 가능하다.

## 3. Admin approval

관리자 웹에서 승인 버튼을 누른다.

이 단계의 의미:

- `ord_stat` 를 `APPR` 또는 `MFG` 로 올린다
- 생산 대기열에 들어갈 수 있는 상태가 된다

검증용 API 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/production/schedule/start \
  -H 'Content-Type: application/json' \
  -d '{"order_ids":[1]}'
```

이 요청이 성공하면 주문 상태가 `MFG` 로 올라간다.

## 4. Production start in PyQt

PyQt의 생산 시작 버튼에서 실제 라인 투입을 실행한다.

이 단계에서:

- `ord_stat` 가 `APPR` 또는 `MFG` 여야 한다
- `OrdPattern` 이 있어야 한다
- 그 다음에야 `Item` + `EquipTaskTxn` 이 생성된다

검증용 API 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/production/start \
  -H 'Content-Type: application/json' \
  -d '{"ord_id": 1}'
```

기대 응답 예시:

```json
{"ord_id":1,"item_id":1,"equip_task_txn_id":1,"message":"Production started: PAT/MM task queued."}
```

## 5. Expected flow

정상 흐름은 아래 순서다.

1. 주문 생성
2. 패턴 등록
3. 관리자 승인
4. PyQt 생산 시작
5. `Item` / `EquipTaskTxn` 생성

## 6. Cleanup

확인 끝나면 이 파일을 삭제한다.

`VERIFY_APPROVAL_START.md`
