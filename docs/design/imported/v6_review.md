# V6 코드 리뷰 보고서

> 작성: 2026-04-14 · 범위: V6 마이그레이션 8단계 신규 모듈 (1855 LOC, 14 파일)
> 관점: Security · Performance · Quality · UX

---

## 0. 한 줄 요약

| 등급 | 건수 | 의미 |
|---|---|---|
| 🔴 Critical | 1 | 운영 배포 전 반드시 해결 |
| 🟡 Warning | 6 | 가까운 시일 내 보완 권장 |
| 🟢 Suggestion | 5 | 점진 개선 |

V6 코드는 **기능적으로 완성도 높음** (8단계 모두 동작). 보안·운영 관점에서 1건의 critical 이슈와 인프라 보강이 필요.

---

## 1. 🔴 Critical (1건)

### S-001: gRPC insecure_channel — 운영 환경에서 mTLS 필수 ✅ 완료 (2026-04-14)

**조치**: `MGMT_GRPC_TLS_ENABLED=1` 환경변수로 mTLS 활성화 가능.
- 자체 CA + server/client cert 발급 스크립트 (`backend/management/scripts/gen_certs.sh`)
- 서버: `_load_tls_credentials()` 가 환경변수 보고 `add_secure_port` 분기
- 클라이언트: `ManagementClient._build_channel()` 가 동일 환경변수로 `secure_channel` 분기
- 검증: TLS ON 시 insecure 클라이언트 거부 (UNAVAILABLE), mTLS 클라이언트 정상

**원본 이슈**:

- **위치**: `monitoring/app/management_client.py:79`, `backend/management/server.py:233`
  ```python
  self._channel = grpc.insecure_channel(f"{host}:{port}")  # client
  server.add_insecure_port(bind_addr)                        # server
  ```
- **위협**: 공장 내부망이라 해도 평문 gRPC. 패킷 캡처 시 ProductionJob/Item id, robot_id, 명령 페이로드 모두 노출. 누군가 동일 네트워크에서 가짜 ManagementClient 로 위조 명령 전송 가능.
- **해결**:
  ```python
  # 서버
  with open("server.key") as f: key = f.read()
  with open("server.crt") as f: crt = f.read()
  creds = grpc.ssl_server_credentials([(key, crt)])
  server.add_secure_port(bind_addr, creds)
  # 클라이언트
  with open("ca.crt") as f: ca = f.read()
  creds = grpc.ssl_channel_credentials(root_certificates=ca)
  channel = grpc.secure_channel(target, creds)
  ```
- **mTLS 도입 방안**: 자체 CA + (Mgmt 서버 + PyQt 클라이언트) cert 발급, ACME/cert-manager 도입은 과함
- **우선순위**: 운영 PG 배포 전. 개발 dev 환경 유지 가능
- **참고**: design.md §9 보안 표 "현 시점 insecure channel" 명시됨

---

## 2. 🟡 Warning (6건)

### S-002: MQTT 브로커 인증 부재 ✅ 완료 (2026-04-14)

**조치**: `MGMT_MQTT_USER` / `MGMT_MQTT_PASS` 환경변수 시 `username_pw_set()` 호출.
- mosquitto 설정 자동화: `scripts/setup_mosquitto_auth.sh` (allow_anonymous false + password_file)
- 검증: 익명 publish 거부 (`Connection Refused: not authorised`), 인증 publish 정상

**원본 이슈**:

- **위치**: `services/adapters/mqtt_adapter.py:62-71` — `client.connect()` 호출 전 `username_pw_set()` 없음
- **위협**: mosquitto 1883 에 익명 접속 허용. 같은 네트워크의 어떤 호스트라도 `casting/esp/+/cmd` 토픽 publish 가능 → ESP32 가짜 명령 수행
- **해결**:
  ```python
  client.username_pw_set(
      os.environ.get("MGMT_MQTT_USER"),
      os.environ.get("MGMT_MQTT_PASS"),
  )
  ```
  + mosquitto.conf 에 `allow_anonymous false` + `password_file` 설정
- **우선순위**: ESP32 배포 시점

### S-003: PG 비밀번호 평문 .env.local

- **위치**: `backend/.env.local` (gitignored) — `Addteam2!` 평문 노출
- **위협**: 노트북 분실/공유 시 PG 전체 권한. 단일 user 계정으로 모든 서비스가 접속.
- **해결**: macOS Keychain (`security find-generic-password`) 또는 1Password CLI (`op read`) 또는 dev 와 prod 계정 분리. 운영은 IAM 또는 vault 권장
- **우선순위**: 운영 환경 배포 시

### P-001: ExecutionMonitor 매 polling 시 모든 items SELECT ✅ 부분 완료 (2026-04-14)

**조치 (Phase 1)**: Adaptive polling interval 도입 — 변경 없는 사이클이 누적되면 점진적으로 polling 간격을 늘려 DB 부담 감소. 이벤트 발생 시 즉시 base interval 로 복귀.

- `MGMT_ADAPTIVE_POLLING=1` (기본 활성)
- `MGMT_POLL_QUIET_CYCLES=5` 누적 시 `BACKOFF_FACTOR=2` 적용
- 상한: `MGMT_MAX_POLL_INTERVAL_SEC=8` 또는 SLA 최단값/2 중 작은 값 (감지 정확도 보호)
- 운영 기본 동작: 1s → 2s → 4s → 8s (cap), 변경 발생 시 즉시 1s

**남은 작업 (Phase 2)**: items 테이블에 `updated_at` 컬럼 + 인덱스 추가 후 incremental polling. 또는 PostgreSQL LISTEN/NOTIFY. 운영 데이터 1만건 누적 후 측정 기반 결정.

**원본 이슈**:

- **위치**: `services/execution_monitor.py:204-212` — `select(Item.id, ...)` 전체 행 스캔, 1초 간격
- **현재 영향**: items 200건 정도면 무시할 수준. **10,000건+ 누적 시** PG CPU 부담
- **해결책**:
  - PostgreSQL LISTEN/NOTIFY (item.cur_stage 변경 trigger) — 가장 우아
  - 또는 `WHERE updated_at > last_poll` 조건 + `updated_at` 인덱스 추가 필요
  - 또는 polling 간격을 stage 변경 빈도에 적응 (이벤트 없으면 5초로 늘림)
- **우선순위**: 운영 데이터 누적 후 측정 기반 결정

### P-002: gRPC 채널을 매 호출마다 생성 (PyQt schedule.py)

- **위치**: `monitoring/app/pages/schedule.py:_do_start` — `client = ManagementClient()` 매 클릭 시 신규 channel
  ```python
  client = ManagementClient()
  wos = client.start_production(order_ids)
  client.close()
  ```
- **현재 영향**: 사용자 클릭 빈도 낮아 무시 가능. **연속 자동 호출** 시 TCP handshake 오버헤드
- **해결**: MainWindow 에 `_mgmt_client` 싱글톤 보관, 페이지에서 공유. 단 동시성 제어 (gRPC channel 은 thread-safe 하지만 stub 객체 재사용 주의)
- **우선순위**: 향후 자동 dispatch 도입 시

### Q-001: 광역 `except Exception` (BLE001) — 4 건

- **위치**: `services/execution_monitor.py:118, 135, 189, 284`
  ```python
  except Exception as exc:  # noqa: BLE001
      logger.exception(...)
  ```
- **문제**: KeyboardInterrupt, SystemExit 도 잡힘. polling 루프가 의도적이지만, 구체 예외(`SQLAlchemyError`, `psycopg.Error`, `OperationalError`) 로 좁히면 디버깅 용이
- **해결**:
  ```python
  except (sqlalchemy.exc.OperationalError, psycopg.errors.Error) as exc:
      logger.warning("DB transient: %s", exc)  # 재시도 가능
  except Exception as exc:  # 진짜 미지의 케이스만
      logger.exception(...)
      raise
  ```
- **우선순위**: 다음 리팩토링

### Q-002: PyQt 메인 스레드에서 gRPC 동기 호출 (schedule.py)

- **위치**: `schedule.py:_do_start` — `client.start_production(order_ids)` 가 메인 GUI 스레드에서 실행
- **문제**: gRPC RPC 동안 UI 프리즈. 현재 5초 timeout 이지만 mgmt 응답 지연 시 사용자가 "버튼 멈춤" 으로 인식
- **해결**: `QtConcurrent.run` 또는 `QThreadPool + QRunnable` 로 워커 분리. 기존 `ItemStreamWorker` 패턴 재사용 가능
- **우선순위**: timeout 늘리기 전 필수

### UX-001: AlertStreamWorker 가 critical 도 토스트만 표시

- **위치**: `monitoring/app/main_window.py:_on_alert_event` (이미 @MX:WARN 부착)
- **문제**: SLA 경고와 critical equipment 에러가 동일 5초 자동 사라짐 토스트. critical 은 사용자 ack 필요
- **해결**: severity 기반 분기
  ```python
  if severity == "critical":
      QMessageBox.critical(self, "긴급 알림", message)  # 모달
  else:
      self.show_toast(severity, ...)
  ```
- **우선순위**: 운영 전

---

## 3. 🟢 Suggestion (5건)

### Q-003: TaskAllocator 가 NotImplementedError 만 던짐

- 미구현 모듈을 production 코드에 그대로 둠. `pyproject.toml` 의 coverage 보고에서 이 라인이 누락되도록 `# pragma: no cover` 부착 권장
- 또는 RPC 자체를 proto 에서 임시 제거하여 명확한 미지원 표시

### Q-004: server.py `ImagePublisherServicer` 클래스가 server.py 안에 정의됨

- 다른 servicer 는 이미 `services/` 분리됨. ImagePublisher 도 `services/image_publisher.py` 로 분리 권장 (테스트 편의)

### Q-005: traffic_manager Waypoint 그래프 hardcoded

- 1m × 2m 맵 + 8 노드는 시연용 픽스처. YAML/DB 로 외부화 시 공장 layout 변경 시 코드 수정 불필요. 이미 `@MX:NOTE` 명시됨

### P-003: ItemStreamWorker / AlertStreamWorker 가 클라이언트별 polling

- 현재는 PyQt 1대만 가정. 다중 PyQt 동시 사용 시 server-side load 선형 증가
- 해결: server-side 단일 polling + pub/sub fan-out (ExecutionMonitor 이미 가지고 있는 _bg_loop 와 통합)
- 우선순위 낮음 — 운영 PyQt 5대 미만에서는 무시 가능

### UX-002: PyQt management_client 의 endpoint 변경 시 hardcoded host 표시

- `_on_alert_event` 에러 메시지에 `client.endpoint` 표기되어 사용자에게 `localhost:50051` 노출. 운영 IP 에서는 의도된 정보 노출이 아닌지 점검 필요

---

## 4. 우수 사항 (긍정적 발견)

| 항목 | 평가 |
|---|---|
| @MX 태그 분포 | NOTE 13 + ANCHOR 7 + WARN 8 + REASON 7 — 차세대 작업자에게 컨텍스트 명료 |
| 어댑터 패턴 (V6 통신 라우팅) | `select_adapter()` 단일 진실, 새 채널 추가가 한 줄 |
| Phase 마다 commit + push | 8개 phase 모두 단위 commit, rollback 용이 |
| traffic_manager 단위 테스트 97% | Phase 6 알고리즘이 회귀 보호 받음 |
| Backtrack Yield 의 priority 비교 | 작은 숫자=우선 규약이 일관성 있게 적용 |
| `CASTING_WS_ENABLED=0` 기본값 | V6 정책 (Interface SPOF 제거) 가 코드 default 로 강제됨 |

---

## 5. 종합 평가

| 영역 | 점수 | 근거 |
|---|---|---|
| 🔒 Security | **C+** | gRPC TLS 미사용 1건 + MQTT 인증 부재. dev 환경 OK, **운영 전 수정 필수** |
| ⚡ Performance | **B+** | 알고리즘은 합리적, polling 부담은 데이터 누적 후 측정 필요 |
| 🛠 Quality | **A-** | 어댑터 패턴 + @MX 풍부 + 일부 광역 except (개선 가능) |
| 🎨 UX | **B** | 토스트/단축키 작동, critical alert 모달 분기 부재 |

**총평**: V6 마이그레이션은 **설계 완성도 높음**. 운영 배포 직전에 mTLS·MQTT 인증·critical alert 모달 3건 보강 시 production-ready.

---

## 6. 조치 권장 순위

| Phase | 항목 | 예상 시간 |
|---|---|---|
| ① 가장 먼저 | UX-001: critical alert 모달 분기 | 30분 |
| ② 중기 | Q-002: PyQt schedule._do_start 비동기화 | 1시간 |
| ③ 운영 직전 | S-001: gRPC mTLS | 2시간 (cert 발급 포함) |
| ④ 운영 직전 | S-002: MQTT 인증 | 1시간 |
| ⑤ 운영 직전 | S-003: PG 비밀번호 vault화 | 2시간 |
| ⑥ 데이터 누적 후 | P-001: LISTEN/NOTIFY 또는 incremental polling | 4시간 |

총 약 10시간 예상.
