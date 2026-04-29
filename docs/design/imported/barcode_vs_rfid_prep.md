# RFID vs 바코드 테스트 준비 보고서

> 작성: 2026-04-22 · 상태: **RFID 완료 · 바코드 준비 중**
> Branch `feat/v6-phase-c2-proxy` · 관련 SPEC: SPEC-RC522-001, SPEC-RFID-001
> 관련 Confluence: [RFID / 바코드 통신 및 UID 추출 실험 (30539816)](https://dayelee313.atlassian.net/wiki/spaces/addinedute/pages/30539816)

---

## 1. RFID 최종 상태 요약 (✅ 완료)

| 항목 | 결과 |
|---|---|
| 하드웨어 | ESP32 DEVKIT + MFRC522 · **VSPI 고정 배선** (SCK=18, MISO=19, MOSI=23, SS=5, RST=22) |
| 펌웨어 | `firmware/conveyor_v5_serial/conveyor_v5_serial.ino` · tag **v1.5.1** |
| 라이브러리 | MFRC522 (Arduino) · NTAG213 지원 |
| 페이로드 포맷 | `order_{ord_id}_item_{YYYYMMDD}_{seq}` (예: `order_1_item_20260417_1`) |
| NDEF 파서 | Text Record 추출 — 페이지 4~15 (48 바이트) 읽어 TLV 0x03 + NDEF 0xD1 + Text 0x54 감지 |
| 회귀 테스트 | **SPEC-RC522-001** 회귀 스위트 · **70 tests 99% 통과** · PR #2 머지 |
| Management 연동 | SPEC-RFID-001 Wave 2 · `ReportRfidScan` gRPC + `rfid_scan_log` append-only 테이블 |
| 서비스 모듈 | `backend/management/services/rfid_service.py` (Wave 2, pytest 5/5 PASS) |
| 알려진 이슈 | healthcheck 주기 VersionReg 읽기가 `PICC_IsNewCardPresent` 간섭 — v1.5.1 에서 제거로 해결 |

### NDEF Text 파싱 로직 (ESP32 펌웨어 추출)

```cpp
if (data[i] == 0x03 && data[i + 2] == 0xD1) {      // TLV 0x03 + NDEF Record 0xD1
  byte payloadLength = data[index + 2];
  char type = data[index + 3];                       // 'T' = Text
  if (type == 'T') {
    byte status = data[index++];
    byte langLen = status & 0x3F;
    index += langLen;                                // "ko" 언어 코드 스킵
    // 나머지 bytes = payload (order_X_item_YYYYMMDD_N)
  }
}
```

---

## 2. Firmware v5.0 의 바코드 관련 역할 — **없음**

`firmware/conveyor_v5_serial` 는 컨베이어 제어 + RFID 읽기 전용. 바코드 테스트에서는 **ESP32 펌웨어 수정 불필요**.

이유:
- 일반적인 USB 바코드 리더기는 **HID 키보드 에뮬레이션** 모드로 동작
- 스캔 결과가 **USB HID 이벤트** 로 호스트(Jetson) 에 직접 전달됨
- ESP32 는 바코드 리더 경로에 관여하지 않음

따라서 바코드 테스트 구성은 **Jetson 단독**:

```
바코드 스티커 (맨홀 부착)
   ↓ 레이저 스캔
USB HID 바코드 리더 (Jetson /dev/input/event5)
   ↓ HID 키 입력 (수십 ms)
Jetson Python (python-evdev)
   ↓ 조립된 문자열 파싱
정확도 · 레이턴시 · 중복 탐지 리포트
```

RFID 플로우와 대조:

```
NFC 스티커 (맨홀 부착)
   ↓ 근접 (< 3cm)
ESP32 + RC522 (SPI · VSPI 고정)
   ↓ Serial 115200 JSON 이벤트
Jetson (serial.py)
   ↓ gRPC ReportRfidScan
Management Service → rfid_scan_log
```

---

## 3. Jetson 바코드 리더 하드웨어 인벤토리

### 3.1 USB 디바이스 스캔 결과 (lsusb)

```
Bus 001 Device 004: ID 0483:0011 STMicroelectronics       ← 바코드 리더
Bus 001 Device 005: ID 10c4:ea60 Silicon Labs CP210x UART ← ESP32
```

### 3.2 HID 속성

```
iManufacturer           1
iProduct                2
bInterfaceClass         3 Human Interface Device
bInterfaceSubClass      1 Boot Interface Subclass
bInterfaceProtocol      1 Keyboard
```

→ **HID Boot Keyboard** 모드. 스캔 결과가 키보드 입력처럼 들어옴.

### 3.3 디바이스 노드

```
/dev/input/by-id/usb-USB_Adapter_USB_Device-event-kbd → /dev/input/event5
```

by-id 심볼릭 링크로 접근 권장 (재부팅 시 event 번호가 바뀔 수 있음).

### 3.4 ESP32 (참고)

```
/dev/ttyUSB0 · crw-rw---- root dialout
baud 115200 · v5.0 업로드됨
```

jetson 사용자는 `dialout` 그룹 소속 → `/dev/ttyUSB0` 접근 가능.

---

## 4. 준비 블로커 3건 (실제 스캔 전 해결 필요)

### 4.1 ⚠️ `arduino-cli` 가 Jetson PATH 에 없음

```
$ arduino-cli version
bash: arduino-cli: command not found
```

**영향**: 바코드 테스트 자체에는 영향 없음 (ESP32 펌웨어 재업로드 불필요). 단 사용자 주장("Jetson 에 Arduino CLI 설치됨") 과 실제가 다르므로 기록.

**조치 (필요 시)**: `~/bin`, `/opt/arduino-cli` 경로 탐색, 또는 재설치:
```bash
# 참고: reference_arduino_cli 메모리 — v1.4.1 + ESP32 core 3.3.7
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=~/bin sh
```

### 4.2 ❌ Python `evdev` 미설치

```
$ python3 -c 'import evdev'
ModuleNotFoundError: No module named 'evdev'
```

**조치**:
```bash
ssh jetson-conveyor "python3 -m pip install --user python-evdev"
```

### 4.3 ❌ jetson 사용자가 `input` 그룹 미소속

```
$ id -a
uid=1000(jetson) groups=1000(jetson),4(adm),20(dialout),... (input 없음)
$ ls -la /dev/input/event5
crw-rw---- 1 root input 13, 69 ...
```

**영향**: `evdev.InputDevice('/dev/input/event5')` 호출 시 `PermissionError: [Errno 13]`.

**조치 (택 1)**:

| 방법 | 명령 | 주의 |
|---|---|---|
| A. 그룹 추가 (권장) | `sudo usermod -aG input jetson && sudo reboot` | 재부팅 필요 |
| B. sudo 실행 | `sudo python3 tools/barcode_probe.py` | 간단하지만 장기 비권장 |
| C. udev rule | `/etc/udev/rules.d/99-barcode.rules` 에 `SUBSYSTEM=="input", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="0011", MODE="0666"` | 드라이버 레벨 |

---

## 5. RFID vs 바코드 비교 설계 (사전 가설)

| 지표 | RFID (NFC 스티커) | 바코드 (Code128 인쇄) |
|---|---|---|
| **하드웨어 비용** | RC522 + NFC 스티커 (200원/개) | HID 리더 (대략 1만~3만원) + 프린터 라벨 (10원/개) |
| **스캔 거리** | ≤ 3cm (근접) | ≤ 30cm (시야 있으면 OK) |
| **오염 내성** | 표면 먼지/주물 분진에 강함 (RF) | 표면 먼지/긁힘에 약함 (광학) |
| **방향성** | 무방향 (근접만) | 리더 각도 제한 있음 (±60°) |
| **편의성** | 태그 부착 + 무의식 스캔 | 라인 오브 사이트 필요 |
| **프로세싱 시간** | 100~300 ms (읽기+NDEF 파싱) | 20~100 ms (HID 키보드 전송) |
| **중복 방지** | UID 고유 (물리 제조 번호) | 페이로드 중복 가능 (프린트 시 제어) |
| **재사용** | 가능 (NDEF 재기록) | 불가 (종이 라벨 폐기) |
| **현재 검증 상태** | ✅ 완료 (SPEC-RC522-001) | 🟡 준비 중 (본 문서) |

→ 실제 테스트 데이터로 이 표를 채우는 것이 목표.

---

## 6. 다음 단계 (Ralph 스토리)

- [x] US-001: 본 문서 (준비 보고서)
- [ ] US-002: `tools/barcode_probe.py` (evdev HID 진단 스크립트)
- [ ] US-003: `tools/gen_test_barcodes.py` (Code128 PNG 생성)
- [ ] US-004: `tools/barcode_benchmark.py` (50회 반복 스캔 계측)
- [ ] US-005: `docs/barcode_test_plan.md` (실행 가이드)
- [ ] US-006: Confluence 30539816 "실험 2: 바코드" 섹션 추가

---

## 참조

- SPEC-RC522-001: `docs/testing/rc522_regression_checklist.md`
- SPEC-RFID-001: `.moai/specs/SPEC-RFID-001/spec.md`
- Firmware v5: `firmware/conveyor_v5_serial/README.md`
- Jetson SSH: memory `reference_jetson_ssh.md`
- Arduino CLI: memory `reference_arduino_cli.md`
