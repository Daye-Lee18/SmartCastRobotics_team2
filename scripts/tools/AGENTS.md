<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# tools

CLI 유틸리티 — 바코드 생성/벤치마크, HID 라이브 ingest, Serial 스캔.

## Key Files

| File | Description |
|------|-------------|
| `barcode_live_ingest.py` | HID Keyboard Boot 바코드 리더 → Mgmt gRPC `ReportRfidScan` → DB 실시간 적재 |
| `barcode_benchmark.py` | 바코드 스캔 벤치마크 (50회, 100%/45ms 검증) |
| `barcode_probe.py` | 바코드 리더 HID 탐색 프로브 |
| `gen_test_barcodes.py` | 테스트용 Code 128 바코드 PNG 생성 (module_width=0.4mm) |
| `gen_test_barcodes_code39.py` | 테스트용 Code 39 바코드 PNG 생성 |
| `serial_scan_ingest.py` | Serial port 스캔 → DB 적재 유틸리티 |

## For AI Agents

### Working In This Directory
- `python tools/barcode_live_ingest.py` — Jetson `/dev/input/event5` HID 읽기
- `python tools/gen_test_barcodes.py` — `barcodes_out/`에 PNG 생성
- `python tools/barcode_benchmark.py` — 벤치마크 실행
- **중요**: python-barcode 기본 module_width 0.2mm → 저가 1D 리더 디코딩 실패. 0.4mm 필수

### Testing Requirements
- 벤치마크: `python tools/barcode_benchmark.py` 결과 JSON 확인
- Live ingest: DBeaver에서 `reader_id LIKE 'BARCODE-%'` 쿼리로 검증

### Common Patterns
- 바코드 리더: `0483:0011` 저가 1D 레이저, HID Keyboard Boot
- `ReportRfidScan` RPC 재사용 (reader_id=`BARCODE-JETSON-01`) — RfidService 무수정
- barcodes_out/, barcodes_out_code39/, barcode_bench_out/ 은 generated (gitignore 고려)

## Dependencies

### Internal
- `backend/management/proto/management.proto` — ReportRfidScan RPC

### External
- python-barcode, python-evdev (Jetson), Pillow
