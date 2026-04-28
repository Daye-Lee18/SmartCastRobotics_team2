/*
 * Conveyor Controller - Network Configuration Template
 *
 * 사용법: 이 파일을 config.h 로 복사 후 실제 값으로 수정
 *   cp config.example.h config.h
 *
 * config.h 는 .gitignore 에 등록되어 있어 커밋되지 않습니다.
 */

#pragma once

// === WiFi Credentials ===
#define WIFI_SSID     "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// === MQTT Broker ===
// RPi5에 Mosquitto 설치 후 RPi의 IP 주소 입력
// 설치: sudo apt install mosquitto mosquitto-clients
// 시작: sudo systemctl enable --now mosquitto
#define MQTT_URI         "mqtt://192.168.1.100:1883"
#define MQTT_CLIENT_ID   "conveyor_1"
#define MQTT_USERNAME    ""   // 비어 있으면 인증 없음
#define MQTT_PASSWORD    ""

// === Device Identity ===
#define DEVICE_ID        1    // 여러 컨베이어 운영 시 구분용

// === MQTT Topics ===
#define TOPIC_STATUS     "conveyor/1/status"
#define TOPIC_EVENT      "conveyor/1/event"
#define TOPIC_CMD        "conveyor/1/cmd"
#define TOPIC_VISION     "vision/1/result"
#define TOPIC_HEARTBEAT  "conveyor/1/heartbeat"

// === Timing ===
#define MQTT_KEEPALIVE_SEC 30
#define HEARTBEAT_INTERVAL_MS 10000  // 10초마다 heartbeat
