<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# firmware

ESP32/Arduino 펌웨어 — 컨베이어 제어, RFID 리더, 모터 테스트, 센서 프로토콜.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `conveyor_controller/` | ESP32 컨베이어 컨트롤러 v4 (L298N + TOF250 + JGB37-555) |
| `conveyor_v5_serial/` | ESP32 컨베이어 v5 — WiFi/MQTT 제거, Serial 115200 수신만 |
| `rc522_standalone_test/` | RC522 RFID 독립 테스트 펌웨어 (ESP32) |
| `motor_test/` | DC 모터 기본 테스트 스케치 |
| `i2c_scan/` | I2C 디바이스 스캐너 유틸리티 |
| `tof_protocol_scan/` | TOF250 프로토콜 분석 도구 |

## For AI Agents

### Working In This Directory
- Arduino CLI: `arduino-cli compile --fqbn esp32:esp32:esp32 <sketch>/`
- Upload: `arduino-cli upload --port /dev/ttyUSB0 --fqbn esp32:esp32:esp32 <sketch>/`
- ESP32 Core 3.3.7 + micro_ros_arduino 설치 필요
- **주의**: 모터 테스트는 Mac USB 금지 (brownout) — Jetson 또는 외부 12V 필수

### Testing Requirements
- 아두이노 스케치는 compile 성공으로 1차 검증
- 실기 테스트: ESP32 USB 연결 후 Serial Monitor

### Common Patterns
- `.ino` 파일이 소스 오브 트루스 — HTML 다이어그램은 참조용
- `config.h` 는 gitignored — `config.example.h` 에서 복사
- Serial 9600 (v4) 또는 115200 (v5) ASCII UART
- TOF250: AliExpress 모듈은 ASCII UART 9600, NOT I2C

## Dependencies

### External
- Arduino CLI 1.4.1+, ESP32 core 3.3.7
- Libraries: MFRC522, WiFi (v4 only), ESP32Servo
