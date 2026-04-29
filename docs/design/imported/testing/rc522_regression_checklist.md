# RC522 안정성 회귀 테스트 체크리스트

**SPEC**: [SPEC-RC522-001](.moai/specs/SPEC-RC522-001/spec.md) v0.1.0
**Acceptance**: [acceptance.md](.moai/specs/SPEC-RC522-001/acceptance.md)
**목적**: v1.5.1 커밋 `dd4c4eb` 에서 수정된 RC522 healthcheck 간섭 버그의 재발을 방지한다.
**소요 시간**: 10분 이내 (100탭 기준)

---

## 1. 개요

이 체크리스트는 `conveyor_v5_serial.ino` v1.5.1 펌웨어의 RFID 서브시스템을
Jetson `jetson-conveyor` 에서 연속 100탭을 통해 자동 검증하는 절차다.

핵심 검증 기준:
- UID 감지 성공률 ≥ 99% (100탭 롤링 윈도우)
- NDEF Text 파싱 성공률 ≥ 95% (NDEF 카드 사용 시)
- 테스트 중 펌웨어 크래시 0건

**주의**: Mac 호스트에서는 L298N inrush 로 USB 전원이 떨어질 수 있다.
모터 동반 테스트는 **반드시 Jetson 또는 외부 12V 에서 수행**한다.
(근거: 메모리 `feedback_motor_brownout_mac_usb`)

---

## 2. 사전 준비

### 2.1 테스트 카드 확인

- [ ] 메인 NDEF 카드 준비 (`order_1_item_20260417_2` 유형 1종)
- **AC-E2** (no-NDEF 카드) / **AC-E3** (UTF-8 손상 카드) 시나리오는 **Deferred** —
  해당 카드를 확보한 후 별도 수행. 현재 체크리스트는 메인 카드 기준.

### 2.2 Jetson SSH 접속

```bash
ssh jetson-conveyor
```

> Tailscale IP: `100.77.62.67`. SSH 키: `~/.ssh/jetson_orin`.

### 2.3 jetson_publisher / esp_bridge 프로세스 중지

하네스와 포트를 공유하면 `/dev/ttyUSB0` 가 이미 열려 있어 하네스가 exit 2 로 실패한다.

```bash
# 1) 실행 중인 프로세스 확인
pgrep -af jetson_publisher
pgrep -af esp_bridge

# 2) 있으면 kill
pkill -f jetson_publisher || true
pkill -f esp_bridge || true

# (미래 대비) systemd 유닛 존재 여부 확인
systemctl list-units 'jetson*' --no-pager
# 유닛이 있으면:
# sudo systemctl stop <unit-name>
```

- [ ] `pgrep` 출력이 비어있음을 확인

### 2.4 USB 포트 확인

```bash
ls -l /dev/ttyUSB0
```

- [ ] `/dev/ttyUSB0` 가 존재하고 `dialout` 그룹 권한이 있음

### 2.5 Mac 로컬 실행 시 (개발자)

Mac 에서 하네스를 실행하면 아래 경고가 자동 출력된다:

```
[WARN] Mac host detected. Motor commands disabled (ref: feedback_motor_brownout_mac_usb). Read-only sniff mode.
```

이 경우 하네스는 read-only 모드로 동작하며 모터 커맨드를 차단한다.
**운영 검증(100탭 완전 수행)은 반드시 Jetson 에서 실행할 것.**

---

## 3. 실행 절차

### 3.1 표준 실행 명령

```bash
# Jetson 에서 실행
python3 /home/jetson/<repo>/scripts/test_rc522_regression.py \
  --taps 100 \
  --timeout 300 \
  --report /tmp/rc522_regression.json
```

> `<repo>` 는 Jetson 에 클론된 저장소 경로 (예: `~/casting-factory`).

### 3.2 탭 시퀀스

1. 카드를 RC522 리더 중앙에 올린다 (약 1초 유지).
2. 카드를 리더에서 완전히 제거한다 (리더에서 2cm 이상 이격).
3. 1~2를 반복한다 (100회 목표, 5분 이내).

- [ ] 진행 중 화면에서 JSON 라인이 출력되는지 확인 (`rfid_tag` 이벤트)
- [ ] 예상치 못한 `BOOT:` 라인 재출력 시 즉시 중단 → 섹션 6 참조

### 3.3 실시간 진행 확인 (선택)

```bash
# 별도 터미널에서 JSON 리포트 모니터링 (완료 후)
cat /tmp/rc522_regression.json | python3 -m json.tool
```

---

## 4. 판정 기준

### AC-1 · Happy Path (v1.5.1 100탭 성공)

| 필드 | 기대값 |
|------|--------|
| `exit_code` | `0` |
| `total_taps` | `100` |
| `successful_uid_reads` | ≥ `99` |
| `ndef_parse_successes` | ≥ `95` (NDEF 카드 사용 시) |
| `firmware_crashed` | `false` |
| `failure_category` | `null` |
| `healthcheck_state` | `"off"` |

- [ ] exit code = 0 확인: `echo $?`
- [ ] `/tmp/rc522_regression.json` 파일 확인
- [ ] 위 필드값이 기대값과 일치

### AC-2 · Healthcheck Regression Block

healthcheck 재도입 실험 빌드를 검증할 때:

```bash
python3 scripts/test_rc522_regression.py \
  --healthcheck-expected on \
  --uid-threshold 99 \
  --taps 100 \
  --report /tmp/rc522_healthcheck.json
```

- 기대: exit 1, `failure_category == "healthcheck_regression"`, 리포트에 `dd4c4eb` 참조

### AC-3 · Mac Read-Only Sniff

Mac 에서 실행 시 기대 동작:

```
[WARN] Mac host detected. Motor commands disabled (ref: feedback_motor_brownout_mac_usb). Read-only sniff mode.
```

- 모터 커맨드 (RUN, STOP, start 등) 가 serial 에 전송되지 않음
- RFID 이벤트 수신 및 집계는 정상 동작

---

## 5. Deferred 항목

다음 항목은 이번 체크리스트에서 제외되며, 관련 카드/환경 확보 후 수행한다:

| 항목 | 조건 | 관련 AC |
|------|------|---------|
| no-NDEF 카드 테스트 | 공카드 또는 포맷 다른 카드 보유 시 | AC-E2 |
| UTF-8 손상 NDEF 카드 | 깨진 바이트가 포함된 카드 보유 시 | AC-E3 |
| 독립 스케치 report mode | Task 7 결정 후 | — |

---

## 6. 문제 발생 시

### 6.1 BOOT 라인 재출력 관측 시 즉시 중단

테스트 도중 `BOOT:conveyor_v5_serial 1.5.1` 이 두 번 이상 출력되면:

1. 하네스를 즉시 Ctrl+C 로 중단한다.
2. 다음 정보를 수집한다:
   - 펌웨어 버전 (BOOT 라인 원문)
   - 크래시 시점 탭 횟수 (`first_crash_at_tap` 필드)
   - 최근 15줄 Serial 로그
   - 실행 환경 (`uname -a` 출력)
   - MFRC522 version Reg 값 (`rfid_reader` 이벤트의 `version` 필드)
3. 리포트 JSON 을 저장한다: `/tmp/rc522_regression.json`
4. 이슈를 등록하고 위 정보를 첨부한다.

### 6.2 exit code = 2 (포트 열기 실패)

```
[ERROR] 시리얼 포트 열기 실패: ...
Port already in use. Stop jetson_publisher / esp_bridge before running this suite.
```

→ 섹션 2.3 의 프로세스 중지 절차를 다시 수행한다.

### 6.3 UID 성공률 저하

- `uid_detection_below_threshold`: 카드 탭 각도/거리 점검, 카드 상태 확인.
  v1.5.0 이 플래시된 경우 `firmware_version` 필드에서 확인 후 v1.5.1 로 업그레이드.
- `healthcheck_regression`: `--healthcheck-expected on` 없이 발생하면 즉시 dd4c4eb 커밋 상태를 확인한다.

### 6.4 NDEF 성공률 저하

- 카드의 NDEF 페이로드를 독립 스케치 (`rc522_standalone_test.ino`) 로 별도 검증한다.
- 카드가 악화된 경우 교체를 고려한다.

---

## 참조

- SPEC-RC522-001: `.moai/specs/SPEC-RC522-001/spec.md`
- Acceptance: `.moai/specs/SPEC-RC522-001/acceptance.md`
- 수정 커밋: `dd4c4eb` (v1.5.1 — healthcheck 간섭 버그 수정)
- 메모리: `feedback_rc522_healthcheck_bug`, `feedback_motor_brownout_mac_usb`
- Jetson SSH: `ssh jetson-conveyor` (Tailscale `100.77.62.67`)
