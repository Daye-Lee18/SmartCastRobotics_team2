/*
 * Conveyor Belt Controller v5.0 — Serial Bridge (V6 Architecture)
 * Firmware tag: 1.5.1 (2026-04-22 확인 · SPEC-AMR-001 Wave 3 handoff 버튼 포함)
 * Base: conveyor_controller v4.0.0 (성숙한 TOF 센서 로직·anti-crosstalk 재사용)
 *
 * 1.5.1 확인사항 (2026-04-22):
 *   - RFID-RC522 카드 감지 실패 원인 제거 (주기 VersionReg healthcheck 삭제).
 *   - SPEC-AMR-001 Wave 3: 후처리존 A접점 푸시 버튼 (GPIO 33, INPUT_PULLUP)
 *     이미 포함. 버튼 rising edge (뗀 순간) 에서 `HANDOFF_ACK` 토큰 +
 *     {"event":"handoff_ack","zone":"postprocessing",...} JSON 이벤트 발행.
 *     Jetson bridge (jetson_publisher/esp_bridge.py) 가 파싱해
 *     Management gRPC `ReportHandoffAck` 로 전달, public.handoff_acks 에 INSERT.
 *     디바운스 50ms + 연타 병합 500ms.
 *
 * 1.5.0 (2026-04-17):
 *   - RFID-RC522 가 UID 외에 NDEF Text 레코드도 파싱하여 JSON 이벤트에 포함.
 *     페이지 4~15 (48 바이트) 에서 Text Record 감지 → UTF-8 텍스트 추출.
 *     논블로킹 (delay 사용 X), 실패해도 UID 이벤트는 항상 발행.
 *     예: {"event":"rfid_tag","uid":"AA:BB:CC:DD","type":"NTAG213","text":"AMR-001"}
 *   - JSON escape helper 로 따옴표/백슬래시/제어문자 안전 처리.
 *
 * v4.0 → v5.0 주요 변경점:
 *   1) WiFi/MQTT 기본 비활성 (#define ENABLE_WIFI_MQTT 0).
 *      Jetson Image Publisher 와 **USB Serial** (/dev/ttyUSB0 @ 115200) 로만 통신.
 *   2) ST_STOPPED 의 5초 타임아웃 자동 탈출 제거.
 *      → Jetson 의 "RUN\n" (또는 camera_ok/inspect_done) 수신 시에만 POST_RUN 진입.
 *   3) Serial 프로토콜 토큰 추가 (기존 JSON event 는 그대로 유지, 디버깅 용):
 *        ESP → Jetson: BOOT / STOPPED / STARTED / DONE / PONG / STATE:<name>
 *        Jetson → ESP: RUN / STOP / PING / STATUS / camera_ok / inspect_done
 *
 * v4.0 과 동일하게 유지:
 *   - TOF250 (Taidacent) x2 ASCII @ 9600: TOF1=GPIO16 (진입), TOF2=GPIO17 (카메라 앞)
 *   - Motor L298N: ENA=GPIO25 (PWM), IN1=GPIO26, IN2=GPIO27
 *   - Debounce (DEBOUNCE_MS=500ms), Anti-crosstalk gating (raw2 && !raw1),
 *     MIN_RUN_MS=1000ms (motor start 후 TOF2 false trigger 차단)
 *
 * State flow:
 *   IDLE → (TOF1 감지) → RUNNING
 *        → (TOF2 감지, MIN_RUN_MS 경과 후) → STOPPED + "STOPPED\n" TX
 *        → (Jetson "RUN\n" RX) → POST_RUN + "STARTED\n" TX
 *        → (POST_RUN_MS=4000ms 경과) → CLEARING + "DONE\n" TX
 *        → (TOF2 clear) → IDLE
 */

#include <HardwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

// === Feature flags ===
#define ENABLE_WIFI_MQTT 0   // v5.0 기본 꺼둠. 1 로 바꾸면 v4.0 동작 (config.h 필요)

#if ENABLE_WIFI_MQTT
  #include <WiFi.h>
  #include "ESP32MQTTClient.h"
  #include "config.h"
  ESP32MQTTClient mqttClient;
  bool mqttConnected = false;
  unsigned long lastHeartbeat = 0;
#endif

// === Pin Definitions (v4.0 동일) ===
static const int PIN_MOTOR_ENA = 25;
static const int PIN_MOTOR_IN1 = 26;
static const int PIN_MOTOR_IN2 = 27;
static const int PIN_TOF1_RX   = 16;
static const int PIN_TOF2_RX   = 17;

// === RFID-RC522 (VSPI 고정 배선, 2026-04-17 확정) ===
static const char* RFID_SPI_NAME = "VSPI";
static const uint8_t PIN_RFID_SCK  = 18;
static const uint8_t PIN_RFID_MISO = 19;
static const uint8_t PIN_RFID_MOSI = 23;
static const uint8_t PIN_RFID_SS   = 5;
static const uint8_t PIN_RFID_RST  = 22;

// === Handoff ACK Push Button (SPEC-AMR-001, 2026-04-17) ===
// 후처리존 A접점 푸시 버튼. 버튼 한쪽→GP33, 다른쪽→GND. INPUT_PULLUP 사용.
// 평시 HIGH, 눌림 LOW. release edge(LOW→HIGH) 에서 1회 이벤트 발행.
static const int PIN_HANDOFF_BUTTON = 33;
static const unsigned long HANDOFF_DEBOUNCE_MS = 50;   // 물리 디바운스
static const unsigned long HANDOFF_MIN_GAP_MS  = 500;  // 연타 병합 (동일 이벤트 처리)

// === Config (v4.0 동일) ===
static const long TOF_BAUD = 9600;
static const int  DETECT_MIN_MM = 1;
static const int  DETECT_MAX_MM = 30;
static const int  MOTOR_SPEED   = 180;
static const unsigned long POST_RUN_MS     = 4000;  // v5: 사용자 요구 4초
static const unsigned long CLEAR_TIMEOUT_MS = 5000;
static const unsigned long REPORT_MS       = 300;
static const unsigned long DEBOUNCE_MS     = 500;
static const unsigned long MIN_RUN_MS      = 1000;
static const unsigned long RFID_REINIT_MS        = 3000;   // 리더 lost 시 재초기화 간격
static const unsigned long RFID_HEALTHCHECK_MS   = 2000;
static const unsigned long RFID_TAG_HOLD_MS      = 700;

// v5: STOPPED 탈출은 Jetson RUN 수신에만 의존 (타임아웃 자동 탈출 제거)
// 안전 타임아웃이 필요하면 아래를 양수로 (0 = 무한 대기).
static const unsigned long STOP_WAIT_TIMEOUT_MS = 0;

// === States ===
enum State { ST_IDLE, ST_RUNNING, ST_STOPPED, ST_POST_RUN, ST_CLEARING };
const char* ST_NAME[] = {"IDLE", "RUNNING", "STOPPED", "POST_RUN", "CLEARING"};

// === Globals ===
HardwareSerial tof1(1);
HardwareSerial tof2(2);
MFRC522 rfid(PIN_RFID_SS, PIN_RFID_RST);  // v1.5.1: 생성자에서 핀 설정 (독립 스니펫과 동일)

State state = ST_IDLE;
unsigned long stateStart = 0;
unsigned long lastReport = 0;

int dist1 = -1, dist2 = -1;
bool det1 = false, det2 = false;
bool raw1 = false, raw2 = false;
unsigned long det1Start = 0, det2Start = 0;
int objCount = 0;

bool visionResultReceived = false;
String visionResult = "";

String buf1 = "";
String buf2 = "";

bool rfidReaderReady = false;
byte activeRfidVersion = 0;
unsigned long lastRfidInitAttemptMs = 0;
unsigned long lastRfidHealthcheckMs = 0;
unsigned long lastRfidSeenMs = 0;
String lastRfidUid = "";
String lastRfidType = "";

// Handoff button state
int  handoffLastRaw = HIGH;              // INPUT_PULLUP: 평시 HIGH
int  handoffStableLevel = HIGH;
unsigned long handoffLastChangeMs = 0;
unsigned long handoffLastEmitMs = 0;
unsigned long handoffPressCount = 0;

// NDEF Text payload (2026-04-17 추가)
#define RFID_TEXT_MAX_LEN 64
char lastRfidText[RFID_TEXT_MAX_LEN] = "";
int  lastRfidTextLen = 0;

// === Forward decls ===
void publishJson(const String& json);
void publishToken(const char* token);
void sendStatus();
void handleCommand(const String& cmd, const String& source);
bool initRfid();
void pollRfid();
void pollHandoffButton();
void emitHandoffAck(const char* reason);

// === Motor Control ===
void motorOn() {
  digitalWrite(PIN_MOTOR_IN1, HIGH);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  ledcWrite(PIN_MOTOR_ENA, MOTOR_SPEED);
}
void motorOff() {
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  ledcWrite(PIN_MOTOR_ENA, 0);
}

// === TOF250 ASCII Parser (v4.0 동일) ===
int parseTofLine(HardwareSerial& ss, String& buffer) {
  int result = -1;
  while (ss.available()) {
    char c = ss.read();
    if (c == '\r' || c == '\n') {
      if (buffer.length() > 0) {
        result = buffer.toInt();
        buffer = "";
      }
    } else if (isdigit(c)) {
      buffer += c;
      if (buffer.length() > 10) buffer = "";
    }
  }
  return result;
}

String uidToString(const MFRC522::Uid& uid) {
  String out;
  for (byte i = 0; i < uid.size; ++i) {
    if (i > 0) out += ':';
    if (uid.uidByte[i] < 0x10) out += '0';
    out += String(uid.uidByte[i], HEX);
  }
  out.toUpperCase();
  return out;
}

// === NDEF Text Record 파서 (NTAG213/215/216 MIFARE Ultralight 계열) ===
// 동작: 페이지 4~15(48 바이트) 에서 NDEF 메시지를 찾아 Text 레코드 페이로드만 추출.
// 설계 원칙: 블로킹 delay 금지, 버퍼 범위 엄격 검증, 실패 시 0 반환.
// 시그니처: out 버퍼는 null 종단됨. maxLen 은 '\0' 포함 크기.
static int parseNdefText(const byte *data, int dataLen, char *out, size_t maxLen) {
  if (maxLen == 0) return 0;
  out[0] = '\0';

  // NDEF TLV: 0x03 [len] 0xD1 [type_len=01] [payload_len] 'T' [status] [lang..] [text..]
  for (int i = 0; i < dataLen - 2; i++) {
    if (data[i] != 0x03 || data[i + 2] != 0xD1) continue;

    int idx = i + 2;                 // 0xD1 위치
    if (idx + 3 >= dataLen) break;
    idx++;                           // header(0xD1) 건너뜀
    idx++;                           // type_length 건너뜀 (보통 1)
    byte payloadLen = data[idx++];
    char type = (char)data[idx++];
    if (type != 'T') return 0;       // Text 레코드만 지원

    if (idx >= dataLen) return 0;
    byte status = data[idx++];
    byte langLen = status & 0x3F;    // 언어 코드 길이
    idx += langLen;                  // 언어 코드 건너뜀

    int textLen = (int)payloadLen - (int)langLen - 1;
    if (textLen <= 0 || idx + textLen > dataLen) return 0;
    if ((size_t)textLen >= maxLen) textLen = (int)maxLen - 1;

    for (int j = 0; j < textLen; j++) {
      out[j] = (char)data[idx + j];
    }
    out[textLen] = '\0';
    return textLen;
  }
  return 0;
}

// === 감지된 카드에서 NDEF Text 페이로드 읽기 ===
// 전제: PICC_IsNewCardPresent + PICC_ReadCardSerial 이 방금 성공해 세션이 열려 있음.
// MIFARE_Read 는 16 바이트씩(= 4 페이지) 반환. 3회 호출로 48 바이트 수집.
// 실패 시 지금까지 수집된 바이트만으로 파싱 시도 (짧은 NDEF 는 페이지 4~7 로 충분).
static int readNdefFromCard(char *out, size_t maxLen) {
  byte buffer[18];
  byte fullData[48];
  int offset = 0;

  for (byte page = 4; page < 16; page += 4) {
    byte bufSize = sizeof(buffer);
    MFRC522::StatusCode st = rfid.MIFARE_Read(page, buffer, &bufSize);
    if (st != MFRC522::STATUS_OK) break;
    for (int i = 0; i < 16 && offset < (int)sizeof(fullData); i++) {
      fullData[offset++] = buffer[i];
    }
  }
  return parseNdefText(fullData, offset, out, maxLen);
}

// === JSON 문자열 이스케이프 ===
// NDEF Text 가 따옴표나 백슬래시를 포함할 수 있으므로 publishJson 전에 적용.
// 제어 문자는 드롭 (CR/LF/TAB 만 escape sequence 유지).
static String jsonEscape(const char *s) {
  String r;
  if (s == nullptr) return r;
  size_t n = strlen(s);
  r.reserve(n + 4);
  for (size_t i = 0; i < n; ++i) {
    char c = s[i];
    if (c == '"' || c == '\\')      { r += '\\'; r += c; }
    else if (c == '\n')             r += "\\n";
    else if (c == '\r')             r += "\\r";
    else if (c == '\t')             r += "\\t";
    else if ((unsigned char)c < 0x20) { /* drop */ }
    else                            r += c;
  }
  return r;
}

void clearRfidTag() {
  if (lastRfidUid.length() == 0) return;

  publishJson(String("{\"event\":\"rfid_clear\",\"uid\":\"") + lastRfidUid + "\"}");
  lastRfidUid = "";
  lastRfidType = "";
  lastRfidText[0] = '\0';
  lastRfidTextLen = 0;
}

// RC522 를 VSPI 배선으로 1회 초기화. 실패 시 false 반환 (주기적 재시도).
// v1.5.1: 독립 스니펫과 동일하게 SPI.begin() 기본값 사용, PCD_Init 무인자 호출.
bool initRfid() {
  clearRfidTag();
  rfidReaderReady = false;
  activeRfidVersion = 0;
  lastRfidInitAttemptMs = millis();

  SPI.begin();     // ESP32 기본 VSPI: SCK=18, MISO=19, MOSI=23, SS=5 (고정 배선과 동일)
  rfid.PCD_Init(); // 생성자에 전달한 SS/RST 핀 사용
  delay(50);

  byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  if (version == 0x00 || version == 0xFF) {
    publishJson("{\"event\":\"rfid_reader\",\"status\":\"not_found\"}");
    Serial.println("RFID:READER:NOT_FOUND");
    return false;
  }

  rfidReaderReady = true;
  activeRfidVersion = version;
  lastRfidHealthcheckMs = lastRfidInitAttemptMs;

  publishJson(
    String("{\"event\":\"rfid_reader\",\"status\":\"ready\",\"spi\":\"")
    + RFID_SPI_NAME
    + "\",\"ss\":" + PIN_RFID_SS
    + ",\"rst\":" + PIN_RFID_RST
    + ",\"version\":\"0x" + String(version, HEX) + "\"}"
  );
  Serial.printf(
    "RFID:READER:FOUND spi=%s sck=%u miso=%u mosi=%u ss=%u rst=%u version=0x%02X\n",
    RFID_SPI_NAME, PIN_RFID_SCK, PIN_RFID_MISO, PIN_RFID_MOSI,
    PIN_RFID_SS, PIN_RFID_RST, version
  );
  return true;
}

void pollRfid() {
  unsigned long now = millis();

  if (!rfidReaderReady) {
    if (now - lastRfidInitAttemptMs >= RFID_REINIT_MS) {
      initRfid();
    }
    return;
  }

  // v1.5.1: 주기 VersionReg healthcheck 제거 (카드 감지 간섭 의심).
  // RC522 가 PICC_IsNewCardPresent 자체로 상태 확인되므로 별도 헬스체크 불필요.
  // 필요 시 에러 누적 후 재초기화 로직 추후 추가.

  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    if (lastRfidUid.length() > 0 && now - lastRfidSeenMs >= RFID_TAG_HOLD_MS) {
      clearRfidTag();
    }
    return;
  }

  String uid = uidToString(rfid.uid);
  MFRC522::PICC_Type cardType = rfid.PICC_GetType(rfid.uid.sak);
  String cardTypeName = String(rfid.PICC_GetTypeName(cardType));

  lastRfidSeenMs = now;
  if (uid != lastRfidUid) {
    lastRfidUid = uid;
    lastRfidType = cardTypeName;

    // NDEF Text 읽기 (실패해도 UID 이벤트는 항상 발행)
    char textBuf[RFID_TEXT_MAX_LEN];
    lastRfidTextLen = readNdefFromCard(textBuf, sizeof(textBuf));
    strncpy(lastRfidText, textBuf, sizeof(lastRfidText) - 1);
    lastRfidText[sizeof(lastRfidText) - 1] = '\0';

    String json = String("{\"event\":\"rfid_tag\",\"uid\":\"") + uid
                + "\",\"type\":\"" + cardTypeName + "\"";
    if (lastRfidTextLen > 0) {
      json += ",\"text\":\"" + jsonEscape(lastRfidText) + "\"";
    }
    json += "}";
    publishJson(json);

    Serial.print("RFID_UID:");
    Serial.println(uid);
    if (lastRfidTextLen > 0) {
      Serial.print("RFID_TEXT:");
      Serial.println(lastRfidText);
    }
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

// === Handoff ACK Button (SPEC-AMR-001) ===
// Token line: HANDOFF_ACK + JSON event. Jetson bridge 가 파싱해 Mgmt gRPC 로 전달.
// 연타/채터링 방지: 디바운스 50 ms + 연속 이벤트 500 ms 최소 간격.
void emitHandoffAck(const char* reason) {
  unsigned long now = millis();
  handoffPressCount++;
  handoffLastEmitMs = now;

  publishToken("HANDOFF_ACK");   // ★ Jetson bridge 가 주로 이 토큰 사용
  String json = String("{\"event\":\"handoff_ack\",\"zone\":\"postprocessing\"")
              + ",\"ts\":" + String(now)
              + ",\"count\":" + String(handoffPressCount)
              + ",\"reason\":\"" + reason + "\""
              + (strcmp(reason, "sim") == 0 ? ",\"sim\":true" : "")
              + "}";
  publishJson(json);
}

void pollHandoffButton() {
  unsigned long now = millis();
  int raw = digitalRead(PIN_HANDOFF_BUTTON);

  if (raw != handoffLastRaw) {
    handoffLastRaw = raw;
    handoffLastChangeMs = now;
    return;  // 아직 디바운스 대기
  }

  // 디바운스 기간 유지된 값 → stable 로 승격
  if (now - handoffLastChangeMs < HANDOFF_DEBOUNCE_MS) return;
  if (raw == handoffStableLevel) return;  // 상태 변화 없음

  int prev = handoffStableLevel;
  handoffStableLevel = raw;

  // rising edge: 눌렀다 뗀 순간 (LOW → HIGH)
  if (prev == LOW && raw == HIGH) {
    if (now - handoffLastEmitMs >= HANDOFF_MIN_GAP_MS) {
      emitHandoffAck("button");
    }
  }
}

// === Sensor Reading (v4.0 anti-crosstalk 포함) ===
void readSensors() {
  unsigned long now = millis();

  int d1 = parseTofLine(tof1, buf1);
  if (d1 >= 0) {
    dist1 = d1;
    raw1 = (d1 >= DETECT_MIN_MM && d1 <= DETECT_MAX_MM);
  }

  int d2 = parseTofLine(tof2, buf2);
  if (d2 >= 0) {
    dist2 = d2;
    raw2 = (d2 >= DETECT_MIN_MM && d2 <= DETECT_MAX_MM);
  }

  if (raw1) {
    if (det1Start == 0) det1Start = now;
    if (now - det1Start >= DEBOUNCE_MS) det1 = true;
  } else {
    det1Start = 0;
    det1 = false;
  }

  // Anti-crosstalk: TOF1 active 중엔 TOF2 raw 무시 (v4.0 핵심)
  bool raw2_valid = raw2 && !raw1;
  if (raw2_valid) {
    if (det2Start == 0) det2Start = now;
    if (now - det2Start >= DEBOUNCE_MS) det2 = true;
  } else {
    det2Start = 0;
    det2 = false;
  }
}

// === Event publish (Serial + optional MQTT) ===
void publishJson(const String& json) {
  Serial.println(json);
#if ENABLE_WIFI_MQTT
  if (mqttConnected) mqttClient.publish(TOPIC_EVENT, json.c_str(), 0, false);
#endif
}

// v5 신규: Jetson bridge 가 파싱하는 간단 토큰 라인
void publishToken(const char* token) {
  Serial.println(token);
}

void setState(State s) {
  String msg = String("{\"event\":\"state\",\"to\":\"") + ST_NAME[s] + "\"}";
  publishJson(msg);
  // v5: Jetson bridge 가 인식하는 STATE:<NAME> 라인 추가
  Serial.print("STATE:");
  Serial.println(ST_NAME[s]);
  state = s;
  stateStart = millis();
}

// === State Machine ===
void update() {
  unsigned long elapsed = millis() - stateStart;

  switch (state) {
    case ST_IDLE:
      if (det1) {
        motorOn();
        publishJson(String("{\"event\":\"entry\",\"dist\":") + dist1 + "}");
        setState(ST_RUNNING);
      }
      break;

    case ST_RUNNING:
      if (elapsed < MIN_RUN_MS) break;
      if (det2) {
        motorOff();
        visionResultReceived = false;
        visionResult = "";
        publishJson(String("{\"event\":\"exit\",\"dist\":") + dist2
                    + ",\"inspection\":\"requested\"}");
        setState(ST_STOPPED);
        publishToken("STOPPED");  // ★ Jetson bridge 트리거
      }
      break;

    case ST_STOPPED:
      // v5: Jetson 의 RUN/camera_ok/inspect_done 수신 시에만 탈출
      if (visionResultReceived) {
        objCount++;
        motorOn();
        publishJson(String("{\"event\":\"post_start\",\"count\":") + objCount
                    + ",\"reason\":\"jetson_run\""
                    + ",\"result\":\"" + (visionResult.length() ? visionResult : "unknown") + "\"}");
        visionResultReceived = false;
        setState(ST_POST_RUN);
        publishToken("STARTED");  // ★ Jetson 에 모터 재시작 통지
      } else if (STOP_WAIT_TIMEOUT_MS > 0 && elapsed >= STOP_WAIT_TIMEOUT_MS) {
        // 안전 타임아웃 (기본 0 = 비활성)
        objCount++;
        motorOn();
        publishJson("{\"event\":\"post_start\",\"reason\":\"safety_timeout\"}");
        setState(ST_POST_RUN);
        publishToken("STARTED");
      }
      break;

    case ST_POST_RUN:
      if (elapsed >= POST_RUN_MS) {
        publishJson(String("{\"event\":\"post_done\",\"tof2_det\":")
                    + (det2 ? "true" : "false") + "}");
        publishToken("DONE");  // ★ 4초 구동 완료
        setState(ST_CLEARING);
      }
      break;

    case ST_CLEARING:
      if (!det2) {
        motorOff();
        publishJson(String("{\"event\":\"cycle_done\",\"count\":") + objCount + "}");
        raw1 = raw2 = false;
        det1 = det2 = false;
        det1Start = det2Start = 0;
        setState(ST_IDLE);
      } else if (elapsed >= CLEAR_TIMEOUT_MS) {
        motorOff();
        publishJson("{\"event\":\"clear_timeout\",\"warn\":\"tof2_stuck\"}");
        raw1 = raw2 = false;
        det1 = det2 = false;
        det1Start = det2Start = 0;
        setState(ST_IDLE);
      }
      break;
  }
}

// === Command handler ===
void handleCommand(const String& cmd, const String& source) {
  // v5 신규/기존 호환 alias
  if (cmd == "RUN" || cmd == "run" || cmd == "camera_ok" || cmd == "inspect_done") {
    visionResult = "ok";
    visionResultReceived = true;
    Serial.printf("{\"ack\":\"run\",\"src\":\"%s\"}\n", source.c_str());
  }
  else if (cmd == "PING" || cmd == "ping") {
    publishToken("PONG");
  }
  else if (cmd == "STATUS" || cmd == "status") {
    sendStatus();
  }
  else if (cmd == "STOP" || cmd == "stop") {
    motorOff();
    setState(ST_IDLE);
  }
  else if (cmd == "RFID_SCAN" || cmd == "rfid_scan") {
    initRfid();
    Serial.println("{\"ack\":\"rfid_scan\"}");
  }
  else if (cmd == "sim_ack" || cmd == "SIM_ACK") {
    // SPEC-AMR-001 FR-AMR-01-07: HW 없이도 실제 버튼과 동일한 이벤트 발행
    emitHandoffAck("sim");
    Serial.println("{\"ack\":\"sim_ack\"}");
  }
  else if (cmd == "start") {          // v4 호환 (수동 시작)
    motorOn(); setState(ST_RUNNING);
  }
  else if (cmd == "reset") {
    motorOff();
    objCount = 0;
    raw1 = raw2 = false;
    det1 = det2 = false;
    det1Start = det2Start = 0;
    visionResultReceived = false;
    visionResult = "";
    setState(ST_IDLE);
  }
  else if (cmd == "sim_entry") {
    raw1 = true; det1 = true; dist1 = 50;
    det1Start = millis() - DEBOUNCE_MS;
    Serial.println("{\"ack\":\"sim_entry\"}");
  }
  else if (cmd == "sim_exit") {
    raw2 = true; det2 = true; dist2 = 50;
    det2Start = millis() - DEBOUNCE_MS;
    Serial.println("{\"ack\":\"sim_exit\"}");
  }
  else if (cmd.length() > 0) {
    Serial.print("ERR:unknown_cmd:");
    Serial.println(cmd);
  }
}

// === Command parser (USB Serial only in v5) ===
String cmdBuf;
void processCmd() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdBuf.length() > 0) {
        cmdBuf.trim();
        handleCommand(cmdBuf, "usb");
        cmdBuf = "";
      }
    } else if (cmdBuf.length() < 64) {
      cmdBuf += c;
    } else {
      cmdBuf = "";
    }
  }
}

void sendStatus() {
  bool motorRunning = digitalRead(PIN_MOTOR_IN1) || digitalRead(PIN_MOTOR_IN2);
  char buf[640];
  snprintf(buf, sizeof(buf),
    "{\"state\":\"%s\",\"elapsed\":%lu,\"motor\":%s,"
    "\"range\":{\"min\":%d,\"max\":%d},"
    "\"tof1\":{\"mm\":%d,\"det\":%s},"
    "\"tof2\":{\"mm\":%d,\"det\":%s},"
    "\"rfid\":{\"ready\":%s,\"spi\":\"%s\",\"ss\":%u,"
    "\"rst\":%u,\"uid\":\"%s\",\"type\":\"%s\",\"text\":\"%s\",\"version\":\"0x%02X\"},"
    "\"count\":%d}",
    ST_NAME[state], millis() - stateStart,
    motorRunning ? "true" : "false",
    DETECT_MIN_MM, DETECT_MAX_MM,
    dist1, det1 ? "true" : "false",
    dist2, det2 ? "true" : "false",
    rfidReaderReady ? "true" : "false",
    RFID_SPI_NAME,
    PIN_RFID_SS,
    PIN_RFID_RST,
    lastRfidUid.c_str(),
    lastRfidType.c_str(),
    lastRfidText,    // NDEF Text (비어 있으면 빈 문자열)
    activeRfidVersion,
    objCount
  );
  Serial.println(buf);
}

// === Setup & Loop ===
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);

  tof1.begin(TOF_BAUD, SERIAL_8N1, PIN_TOF1_RX, -1);
  tof2.begin(TOF_BAUD, SERIAL_8N1, PIN_TOF2_RX, -1);

  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  ledcAttach(PIN_MOTOR_ENA, 1000, 8);
  ledcWrite(PIN_MOTOR_ENA, 0);

  // SPEC-AMR-001: 후처리존 핸드오프 버튼 (INPUT_PULLUP)
  pinMode(PIN_HANDOFF_BUTTON, INPUT_PULLUP);
  handoffLastRaw = digitalRead(PIN_HANDOFF_BUTTON);
  handoffStableLevel = handoffLastRaw;

  delay(500);
  Serial.println();
  Serial.println("BOOT:conveyor_v5_serial 1.5.1");
  publishJson("{\"boot\":\"conveyor_v5.0\",\"tof1\":16,\"tof2\":17,"
              "\"tof_baud\":9600,\"proto\":\"serial_only\","
              "\"rfid\":{\"spi\":\"VSPI\",\"sck\":18,\"miso\":19,"
              "\"mosi\":23,\"ss\":5,\"rst\":22,\"ndef\":\"text\"},"
              "\"handoff\":{\"pin\":33,\"pull\":\"up\","
              "\"debounce_ms\":50,\"min_gap_ms\":500}}");
  setState(ST_IDLE);
  initRfid();

#if ENABLE_WIFI_MQTT
  // v4.0 스타일 WiFi/MQTT 는 필요 시 이 블록 활성화
#endif
}

void loop() {
  readSensors();
  update();
  processCmd();
  pollRfid();
  pollHandoffButton();

  if (millis() - lastReport >= REPORT_MS) {
    lastReport = millis();
    sendStatus();
  }
}
