# Conveyor MQTT Integration Guide

ESP32 컨베이어 컨트롤러(v4.0)와 RPi5/Jetson 비전 시스템 간 MQTT 통신 설정 가이드.

## 구조

```
                    [RPi5 Mosquitto Broker :1883]
                              ▲
                              │ WiFi / LAN
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   [ESP32 Conveyor]    [Jetson Vision]     [Dashboard]
   - pub: status        - sub: event        - sub: all
   - pub: event         - pub: result       - pub: cmd
   - sub: cmd
   - sub: vision/result
```

## 토픽 설계

| 토픽 | 방향 | QoS | Retained | 설명 |
|------|------|-----|----------|------|
| `conveyor/1/status` | ESP32 → * | 0 | false | 300ms 주기 상태 JSON |
| `conveyor/1/event` | ESP32 → * | 0 | false | state 전이, entry/exit 이벤트 |
| `conveyor/1/cmd` | * → ESP32 | 0 | false | start/stop/reset/camera_ok |
| `conveyor/1/heartbeat` | ESP32 → * | 0 | true | alive/online/offline (LWT) |
| `vision/1/result` | Vision → ESP32 | 0 | false | ok/ng 검사 결과 |

## Topic Payload 형식

### conveyor/1/status (ESP32 발행)
```json
{
  "state": "running",
  "elapsed": 1234,
  "motor": true,
  "range": {"min": 1, "max": 30},
  "tof1": {"mm": 5, "det": true},
  "tof2": {"mm": 150, "det": false},
  "count": 3,
  "wifi": true,
  "mqtt": true
}
```

### conveyor/1/event (ESP32 발행)
```json
{"event":"entry","dist":5}
{"event":"exit","dist":6,"inspection":"requested"}
{"event":"post_start","count":4,"reason":"vision","result":"ok"}
{"event":"cycle_done","count":4}
```

### conveyor/1/cmd (수신)
두 형식 모두 허용:
```
start
stop
reset
camera_ok
```
또는
```json
{"cmd":"camera_ok"}
```

### vision/1/result (수신)
두 형식 모두 허용:
```
ok
ng
```
또는
```json
{"result":"ok","defects":[]}
```

## RPi5에 Mosquitto 설치

```bash
# 설치
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

# 자동 시작
sudo systemctl enable --now mosquitto

# 기본 설정: LAN 접속 허용
sudo tee /etc/mosquitto/conf.d/local.conf > /dev/null <<'EOF'
listener 1883
allow_anonymous true
EOF

# 재시작
sudo systemctl restart mosquitto

# 상태 확인
sudo systemctl status mosquitto

# 방화벽 열기 (ufw 사용 시)
sudo ufw allow 1883/tcp
```

## 테스트 명령어

```bash
# 브로커가 동작하는지 확인
mosquitto_sub -h localhost -t 'conveyor/#' -v

# 다른 터미널에서 명령 발행
mosquitto_pub -h localhost -t 'conveyor/1/cmd' -m 'start'
mosquitto_pub -h localhost -t 'conveyor/1/cmd' -m 'stop'

# 비전 결과 발행 (ESP32가 STOPPED 상태에서 기다리는 중일 때)
mosquitto_pub -h localhost -t 'vision/1/result' -m 'ok'
```

## Python 비전 클라이언트 예제 (RPi5/Jetson)

```bash
pip install paho-mqtt
```

```python
#!/usr/bin/env python3
"""
Vision inspection client - subscribes to conveyor exit events,
runs inspection, publishes result back to ESP32.
"""
import json
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883

def run_inspection():
    # TODO: 실제 카메라 촬영 + 모델 추론 호출
    # 예: image = capture_camera()
    #     result = detect_defects(image)
    return "ok"

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[Connected] rc={rc}")
    client.subscribe("conveyor/1/event")
    client.subscribe("conveyor/1/status")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = {"raw": msg.payload.decode()}

    topic = msg.topic
    print(f"[{topic}] {payload}")

    # Conveyor reports object reached exit sensor → run inspection
    if topic == "conveyor/1/event" and payload.get("event") == "exit":
        print("[Inspection] running...")
        result = run_inspection()
        client.publish("vision/1/result", json.dumps({"result": result}))
        print(f"[Inspection] result: {result}")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vision_1")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
```

## ESP32 설정 파일

`firmware/conveyor_controller/config.h` 가 `.gitignore` 에 등록되어 있습니다.
템플릿 `config.example.h` 를 복사해서 실제 값으로 수정:

```bash
cd firmware/conveyor_controller
cp config.example.h config.h
# 편집: WIFI_SSID, WIFI_PASSWORD, MQTT_URI 수정
```

## 동작 흐름 요약

1. ESP32 부팅 → WiFi 연결 → MQTT 브로커 연결
2. `conveyor/1/heartbeat` 에 `online` 발행 (retained)
3. `conveyor/1/cmd`, `vision/1/result` 구독
4. 센서 이벤트 발생 시 `conveyor/1/event` 발행
5. TOF2 감지 시 `{"event":"exit","inspection":"requested"}` 발행 + STOPPED 상태
6. Vision 시스템이 `vision/1/result` 에 `ok` 또는 `ng` 발행
7. ESP32 수신 즉시 POST_RUN 전환 (5초 타임아웃은 안전망)
8. 사이클 완료 → IDLE 복귀

## 안전 타임아웃

MQTT 연결 끊김이나 vision 시스템 장애에 대비해:
- **STOP_WAIT_MS = 5000ms**: vision 응답이 없으면 5초 후 자동 진행
- **Last Will Testament**: ESP32 전원 끊김 시 `offline` 자동 발행
- **WiFi/MQTT 자동 재연결**: 라이브러리가 백그라운드 처리

네트워크가 끊겨도 컨베이어는 시간 기반으로 계속 작동합니다.
