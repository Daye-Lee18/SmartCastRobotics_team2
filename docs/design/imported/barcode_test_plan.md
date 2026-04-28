# 바코드 테스트 실행 플랜 — RFID 대안 검증

> 작성: 2026-04-22 · Branch `feat/v6-phase-c2-proxy`
> 대상: Jetson Orin NX (`jetson-conveyor` · Tailscale `100.77.62.67`) + USB HID 바코드 리더
> 관련 문서: [docs/barcode_vs_rfid_prep.md](barcode_vs_rfid_prep.md)

---

## 1. 사전 체크리스트 (실행 전 반드시 확인)

### 1.1 하드웨어

- [ ] Jetson 전원 켜짐 (Tailscale `ping 100.77.62.67` 응답)
- [ ] USB 바코드 리더 Jetson 포트에 연결
- [ ] 바코드 리더 LED 점등 (대기 모드 · 보통 적색 깜빡임)
- [ ] ESP32 (CP2102, `/dev/ttyUSB0`) 연결 상태 (바코드 테스트엔 불필요하지만 기존 배선 유지)

### 1.2 Jetson 진단 명령

```bash
ssh jetson-conveyor "lsusb | grep -E '0483:0011|10c4:ea60'"
```

기대 출력:
```
Bus 001 Device 004: ID 0483:0011 STMicroelectronics      ← 바코드
Bus 001 Device 005: ID 10c4:ea60 Silicon Labs CP210x     ← ESP32
```

```bash
ssh jetson-conveyor "ls -la /dev/input/by-id/"
```

기대:
```
usb-USB_Adapter_USB_Device-event-kbd -> ../event5
```

### 1.3 권한 · 패키지 블로커 해결

| 블로커 | 명령 | 완료 |
|---|---|---|
| Python `evdev` 설치 | `ssh jetson-conveyor "python3 -m pip install --user python-evdev"` | ☐ |
| `input` 그룹 추가 | `ssh jetson-conveyor "sudo usermod -aG input jetson && sudo reboot"` | ☐ |
| 재부팅 후 그룹 확인 | `ssh jetson-conveyor "id -a \| grep input"` | ☐ |

---

## 2. 단계별 실행 가이드

### Step 1. 샘플 바코드 생성 (로컬 Mac)

```bash
cd ~/Project/casting-factory
python3 -m pip install python-barcode Pillow
python3 tools/gen_test_barcodes.py
```

**결과**: `tools/barcodes_out/` 에 Code128 PNG 5 개 생성.

**인쇄**: 일반 A4 프린터 + 접착 라벨지 또는 Zebra 라벨 프린터. 크기는 **가로 50 mm 이상** 권장 (스캔 거리·각도 여유).

---

### Step 2. 단일 스캔 검증 — `tools/barcode_probe.py`

```bash
scp tools/barcode_probe.py jetson-conveyor:~/casting-factory/tools/
ssh jetson-conveyor
cd ~/casting-factory
python3 tools/barcode_probe.py
```

기대 동작:
```
[INFO] /dev/input/event5 에서 1 회 스캔 대기 (타임아웃 30s)
바코드를 스캔하세요...
```

→ 생성된 바코드 중 하나 스캔.

기대 출력 (JSON 1줄):
```json
{"ts":"2026-04-22T10:15:03+0900","raw":["KEY_O","KEY_R","KEY_D","KEY_E","KEY_R",...],"text":"order_1_item_20260417_1","latency_ms":82,"index":1}
```

**성공 기준**: `text` 필드가 기대 페이로드와 정확히 일치.

---

### Step 3. 반복 스캔 벤치마크 — `tools/barcode_benchmark.py`

```bash
scp tools/barcode_benchmark.py jetson-conveyor:~/casting-factory/tools/
ssh jetson-conveyor
cd ~/casting-factory

python3 tools/barcode_benchmark.py \
  --expected order_1_item_20260417_1 \
  --expected order_2_item_20260417_2 \
  --expected order_3_item_20260417_3 \
  --expected order_4_item_20260417_4 \
  --expected order_5_item_20260417_5 \
  --reps 10
```

총 50회 스캔 (5 페이로드 × 10 라운드). 각 라운드마다 5개 바코드를 순서대로 스캔.

기대 진행 로그:
```
[1/50] rep=1 expected=order_1_item_20260417_1 ... OK got='order_1_item_20260417_1' 78ms
[2/50] rep=1 expected=order_2_item_20260417_2 ... OK got='order_2_item_20260417_2' 72ms
...
[50/50] rep=10 expected=order_5_item_20260417_5 ... OK got='order_5_item_20260417_5' 85ms

===== SUMMARY =====
{
  "total_scans": 50,
  "matches": 50,
  "accuracy_pct": 100.0,
  "avg_latency_ms": 79.3,
  "duplicates": {},
  "failure_samples": []
}
```

**결과 리포트 저장**: `tools/barcode_bench_out/result_<timestamp>.json`

---

## 3. 성공 기준 (Pass/Fail)

| 지표 | 기준 | Pass 조건 |
|---|---|---|
| 정확도 | `accuracy_pct` | ≥ **99%** (50회 중 49회 이상 매칭) |
| 평균 레이턴시 | `avg_latency_ms` | **< 500 ms** (HID 전송 + 파싱) |
| 중복 발행 | `duplicates` | **0** (같은 페이로드가 두 번 읽혀도 둘 다 기대값이면 문제없음. 단, 읽지 않은 바코드가 두 번 잡히면 fail) |
| 실패 샘플 | `failure_samples` | 있다면 수동 분석 → 스캔 각도 / 바코드 인쇄 품질 재검토 |

---

## 4. RFID vs 바코드 비교 표 (실측 후 채움)

| 지표 | RFID (NTAG213 + RC522) | 바코드 (Code128 + HID) |
|---|---|---|
| 정확도 (%) | **99%** (SPEC-RC522-001 결과) | ☐ 측정 후 기록 |
| 평균 latency (ms) | 100~300 (읽기+NDEF) | ☐ |
| 중복 탐지 | UID 고유 (제조사 번호) | ☐ 페이로드 기반 |
| 스캔 거리 | ≤ 3 cm | ☐ (리더 스펙 따라) |
| 오염 내성 (먼지/주물) | 우수 (RF) | ☐ (광학 제약) |
| 방향성 | 무방향 (근접만) | ☐ (리더 각도) |
| 라벨 비용 / 개 | NFC 스티커 ~200원 | 종이 라벨 ~10원 |
| 재사용 | NDEF 재기록 가능 | 폐기 |
| 편의성 | 자동 근접 스캔 | 조작자 시선 확보 필요 |
| **권장** | | (실측 후 결정) |

---

## 5. 문제 해결

### 5.1 `ModuleNotFoundError: No module named 'evdev'`

```bash
ssh jetson-conveyor "python3 -m pip install --user python-evdev"
```

### 5.2 `PermissionError: [Errno 13]` on `/dev/input/event5`

```bash
ssh jetson-conveyor "sudo usermod -aG input jetson && sudo reboot"
```

또는 임시로:
```bash
ssh jetson-conveyor "sudo python3 tools/barcode_probe.py"
```

### 5.3 스캔 시 아무 출력 안 됨

1. 바코드 리더 LED 확인 (스캔 시 녹색·적색 점등)
2. `cat /dev/input/event5` (raw 바이너리 확인)
3. `evtest /dev/input/event5` 로 키 이벤트 raw 관찰
4. 리더 설정 모드: 일부 리더는 스위치·설정 바코드로 **USB HID 모드**를 명시적으로 선택해야 함 (기본 USB Virtual COM 모드일 수 있음)

### 5.4 받은 문자열이 깨지거나 일부만

1. `--reps 1` 로 단일 스캔 로그 먼저 확인
2. raw keys 에 예상치 못한 `KEY_LEFTSHIFT` 또는 특수 키 섞여있는지 확인
3. 필요 시 `tools/barcode_probe.py` 의 `KEY_MAP_NORMAL` / `KEY_MAP_SHIFT` 확장

---

## 6. 체크포인트 요약

- [ ] Step 1: 샘플 PNG 5개 생성 (로컬)
- [ ] Step 1.5: 인쇄 + 부착
- [ ] Step 2: probe 단일 스캔 성공
- [ ] Step 3: benchmark 50회 성공 (≥ 99%)
- [ ] Step 4: 비교 표에 실측 값 기입
- [ ] Step 5: 결과를 [Confluence 30539816](https://dayelee313.atlassian.net/wiki/spaces/addinedute/pages/30539816) "실험 2" 섹션에 업데이트

---

## 7. 관련 파일

| 경로 | 역할 |
|---|---|
| `tools/barcode_probe.py` | HID 진단 단일 스캔 |
| `tools/gen_test_barcodes.py` | Code128 PNG 생성 |
| `tools/barcode_benchmark.py` | 반복 스캔 벤치마크 |
| `docs/barcode_vs_rfid_prep.md` | 준비 보고서 · 블로커 · 하드웨어 |
| `docs/barcode_test_plan.md` | **본 문서** · 실행 가이드 |
| Confluence 30539816 | 실험 기록 원본 (RFID + 바코드) |
