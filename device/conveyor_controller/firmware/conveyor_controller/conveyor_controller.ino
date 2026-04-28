/*
 * Conveyor Belt Controller - ESP32 DevKitC V4
 * v4.0.0 - WiFi + MQTT vision integration
 *
 * Hardware:
 *   - Motor: JGB37-555 DC12V 167RPM (via L298N motor driver)
 *   - Sensors: TOF250 (Taidacent) x2 - ASCII UART @ 9600 baud
 *   - MCU: ESP32 DevKitC V4
 *
 * Sensor wiring (only White TX needed):
 *   TOF1 White -> GPIO16 (UART1 RX)
 *   TOF2 White -> GPIO17 (UART2 RX)
 *   Both: Red -> 3.3V, Black -> GND
 *   Yellow, Blue, Green: NOT CONNECTED
 *
 * Sensor output: ASCII "NNN\r\n" format (e.g. "18\r\n")
 *
 * Motor wiring (L298N):
 *   ENA -> GPIO25 (PWM)
 *   IN1 -> GPIO26
 *   IN2 -> GPIO27
 *
 * State flow:
 *   IDLE -> (TOF1 detect) -> RUNNING
 *        -> (TOF2 detect) -> STOPPED (5s)
 *        -> POST_RUN (2s)
 *        -> CLEARING (until TOF2 clear)
 *        -> IDLE
 */

#include <HardwareSerial.h>
#include <WiFi.h>
#include "ESP32MQTTClient.h"
#include "config.h"

// === MQTT Client ===
ESP32MQTTClient mqttClient;
bool mqttConnected = false;
unsigned long lastHeartbeat = 0;
bool visionResultReceived = false;  // set by MQTT callback when vision/1/result arrives
String visionResult = "";            // "ok" or "ng"

// === Pin Definitions ===
static const int PIN_MOTOR_ENA = 25;
static const int PIN_MOTOR_IN1 = 26;
static const int PIN_MOTOR_IN2 = 27;
static const int PIN_TOF1_RX   = 16;  // Sensor 1 White wire
static const int PIN_TOF2_RX   = 17;  // Sensor 2 White wire

// === Config ===
static const long TOF_BAUD = 9600;   // TOF250 Taidacent baud rate
static const int  DETECT_MIN_MM = 1;   // 1mm 이상이면 감지
static const int  DETECT_MAX_MM = 30;  // 3cm 이내만 감지 (실제 주물은 4-8mm)
static const int  MOTOR_SPEED   = 180;
static const unsigned long STOP_WAIT_MS    = 5000;  // 센서2 감지 후 대기
static const unsigned long POST_RUN_MS     = 4000;  // 후처리 모터 구동 시간
static const unsigned long CLEAR_TIMEOUT_MS = 5000;
static const unsigned long REPORT_MS       = 300;
static const unsigned long DEBOUNCE_MS     = 500;

// Anti-crosstalk: Minimum motor run time before TOF2 can trigger exit.
// Two TOF250 sensors mounted close together cross-talk on 940nm IR.
// This blocks false TOF2 detection within MIN_RUN_MS after motor start.
static const unsigned long MIN_RUN_MS = 1000;  // 1초

// === States ===
enum State { ST_IDLE, ST_RUNNING, ST_STOPPED, ST_POST_RUN, ST_CLEARING };
const char* ST_NAME[] = {"idle", "running", "stopped", "post_run", "clearing"};

// === Globals ===
HardwareSerial tof1(1);
HardwareSerial tof2(2);

State state = ST_IDLE;
unsigned long stateStart = 0;
unsigned long lastReport = 0;

int dist1 = -1, dist2 = -1;
bool det1 = false, det2 = false;      // debounced
bool raw1 = false, raw2 = false;      // instant
unsigned long det1Start = 0, det2Start = 0;
int objCount = 0;

// ASCII parsing buffers
String buf1 = "";
String buf2 = "";

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

// === TOF250 ASCII Parser ===
// Reads bytes, accumulates into buffer until \r or \n, then parses int
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
      if (buffer.length() > 10) buffer = "";  // safety
    } else {
      // ignore non-digit non-terminator chars (e.g., unit text)
    }
  }
  return result;
}

// === Sensor Reading with Debounce ===
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

  // Debounce TOF1
  if (raw1) {
    if (det1Start == 0) det1Start = now;
    if (now - det1Start >= DEBOUNCE_MS) det1 = true;
  } else {
    det1Start = 0;
    det1 = false;
  }

  // Debounce TOF2 with anti-crosstalk gating:
  // TOF1 IR emitter saturates TOF2 receiver when TOF1 sees an object,
  // making TOF2 falsely report ~5mm. Ignore TOF2 raw signal whenever
  // TOF1 raw is also active. Object only counts when it has cleared TOF1.
  bool raw2_valid = raw2 && !raw1;
  if (raw2_valid) {
    if (det2Start == 0) det2Start = now;
    if (now - det2Start >= DEBOUNCE_MS) det2 = true;
  } else {
    det2Start = 0;
    det2 = false;
  }
}

// === MQTT Publish helpers ===
void mqttPublish(const char* topic, const String& payload) {
  Serial.println(payload);  // always log to USB serial
  if (mqttConnected) {
    mqttClient.publish(topic, payload.c_str(), 0, false);
  }
}

void publishEvent(const String& json) {
  mqttPublish(TOPIC_EVENT, json);
}

// === State Machine ===
void setState(State s) {
  String msg = String("{\"event\":\"state\",\"to\":\"") + ST_NAME[s] + "\"}";
  publishEvent(msg);
  state = s;
  stateStart = millis();
}

void update() {
  unsigned long elapsed = millis() - stateStart;

  switch (state) {
    case ST_IDLE:
      if (det1) {
        motorOn();
        publishEvent(String("{\"event\":\"entry\",\"dist\":") + dist1 + "}");
        setState(ST_RUNNING);
      }
      break;

    case ST_RUNNING:
      // Anti-crosstalk: ignore TOF2 detection during minimum run window
      if (elapsed < MIN_RUN_MS) {
        // wait for object to physically travel from TOF1 to TOF2
        break;
      }
      if (det2) {
        motorOff();
        visionResultReceived = false;  // wait for new inspection
        visionResult = "";
        publishEvent(String("{\"event\":\"exit\",\"dist\":") + dist2
                     + ",\"inspection\":\"requested\"}");
        setState(ST_STOPPED);
      }
      break;

    case ST_STOPPED:
      // Transition to POST_RUN when either:
      //   1) MQTT vision result received (preferred)
      //   2) STOP_WAIT_MS timeout expired (fallback, so system keeps moving)
      if (visionResultReceived || elapsed >= STOP_WAIT_MS) {
        objCount++;
        motorOn();
        const char* reason = visionResultReceived ? "vision" : "timeout";
        publishEvent(String("{\"event\":\"post_start\",\"count\":") + objCount
                     + ",\"reason\":\"" + reason
                     + "\",\"result\":\"" + (visionResult.length() ? visionResult : "unknown") + "\"}");
        visionResultReceived = false;
        setState(ST_POST_RUN);
      }
      break;

    case ST_POST_RUN:
      if (elapsed >= POST_RUN_MS) {
        publishEvent(String("{\"event\":\"post_done\",\"tof2_det\":")
                     + (det2 ? "true" : "false") + "}");
        setState(ST_CLEARING);
      }
      break;

    case ST_CLEARING:
      if (!det2) {
        motorOff();
        publishEvent(String("{\"event\":\"cycle_done\",\"count\":") + objCount + "}");
        raw1 = raw2 = false;
        det1 = det2 = false;
        det1Start = det2Start = 0;
        setState(ST_IDLE);
      } else if (elapsed >= CLEAR_TIMEOUT_MS) {
        motorOff();
        publishEvent("{\"event\":\"clear_timeout\",\"warn\":\"tof2_stuck\"}");
        raw1 = raw2 = false;
        det1 = det2 = false;
        det1Start = det2Start = 0;
        setState(ST_IDLE);
      }
      break;
  }
}

// === Command handler (shared between USB serial and MQTT) ===
void handleCommand(const String& cmd, const String& source) {
  if (cmd == "start")        { motorOn(); setState(ST_RUNNING); }
  else if (cmd == "stop")    { motorOff(); setState(ST_IDLE); }
  else if (cmd == "reset")   {
    motorOff();
    objCount = 0;
    raw1 = raw2 = false;
    det1 = det2 = false;
    det1Start = det2Start = 0;
    visionResultReceived = false;
    visionResult = "";
    setState(ST_IDLE);
  }
  else if (cmd == "camera_ok" || cmd == "inspect_done") {
    // Vision inspection complete - transition STOPPED -> POST_RUN immediately
    visionResult = "ok";
    visionResultReceived = true;
    Serial.printf("{\"ack\":\"camera_ok\",\"src\":\"%s\"}\n", source.c_str());
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
  else if (cmd == "status") { sendStatus(); }
}

// === USB Serial Command Parser ===
void processCmd() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;
  handleCommand(cmd, "usb");
}

// === MQTT payload parser (accepts plain text or JSON with "cmd"/"result") ===
void handleMqttCommand(const String& topic, const std::string& payloadStd) {
  String p = String(payloadStd.c_str());
  p.trim();
  if (p.length() == 0) return;

  // Vision result topic
  if (topic == TOPIC_VISION) {
    // Accept either raw string "ok"/"ng" or JSON {"result":"ok"}
    String result = p;
    int idx = p.indexOf("\"result\"");
    if (idx >= 0) {
      int colon = p.indexOf(':', idx);
      int q1 = p.indexOf('"', colon + 1);
      int q2 = p.indexOf('"', q1 + 1);
      if (q1 >= 0 && q2 > q1) result = p.substring(q1 + 1, q2);
    }
    result.toLowerCase();
    visionResult = result;
    visionResultReceived = true;
    Serial.printf("{\"vision_result\":\"%s\"}\n", result.c_str());
    return;
  }

  // Command topic - accept plain text or JSON {"cmd":"start"}
  if (topic == TOPIC_CMD) {
    String cmd = p;
    int idx = p.indexOf("\"cmd\"");
    if (idx >= 0) {
      int colon = p.indexOf(':', idx);
      int q1 = p.indexOf('"', colon + 1);
      int q2 = p.indexOf('"', q1 + 1);
      if (q1 >= 0 && q2 > q1) cmd = p.substring(q1 + 1, q2);
    }
    handleCommand(cmd, "mqtt");
  }
}

void sendStatus() {
  bool motorRunning = digitalRead(PIN_MOTOR_IN1) || digitalRead(PIN_MOTOR_IN2);
  char buf[384];
  snprintf(buf, sizeof(buf),
    "{\"state\":\"%s\",\"elapsed\":%lu,\"motor\":%s,"
    "\"range\":{\"min\":%d,\"max\":%d},"
    "\"tof1\":{\"mm\":%d,\"det\":%s},"
    "\"tof2\":{\"mm\":%d,\"det\":%s},"
    "\"count\":%d,"
    "\"wifi\":%s,\"mqtt\":%s}",
    ST_NAME[state], millis() - stateStart,
    motorRunning ? "true" : "false",
    DETECT_MIN_MM, DETECT_MAX_MM,
    dist1, det1 ? "true" : "false",
    dist2, det2 ? "true" : "false",
    objCount,
    (WiFi.status() == WL_CONNECTED) ? "true" : "false",
    mqttConnected ? "true" : "false"
  );
  Serial.println(buf);
  if (mqttConnected) {
    mqttClient.publish(TOPIC_STATUS, buf, 0, false);
  }
}

// === WiFi + MQTT ===
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // keep connection stable for MQTT
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("{\"wifi\":\"connecting\",\"ssid\":\"%s\"}\n", WIFI_SSID);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("{\"wifi\":\"connected\",\"ip\":\"%s\",\"rssi\":%d}\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("{\"wifi\":\"timeout\",\"warn\":\"will retry in background\"}");
  }
}

void setupMQTT() {
  if (strlen(MQTT_USERNAME) > 0) {
    mqttClient.setURI(MQTT_URI, MQTT_USERNAME, MQTT_PASSWORD);
  } else {
    mqttClient.setURI(MQTT_URI);
  }
  mqttClient.setMqttClientName(MQTT_CLIENT_ID);
  mqttClient.enableLastWillMessage(TOPIC_HEARTBEAT, "offline", true);
  mqttClient.setKeepAlive(MQTT_KEEPALIVE_SEC);
  mqttClient.loopStart();  // starts background task
  Serial.printf("{\"mqtt\":\"starting\",\"uri\":\"%s\",\"id\":\"%s\"}\n",
                MQTT_URI, MQTT_CLIENT_ID);
}

// === Setup & Loop ===
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);

  // TOF250 sensors @ 9600 baud ASCII
  tof1.begin(TOF_BAUD, SERIAL_8N1, PIN_TOF1_RX, -1);
  tof2.begin(TOF_BAUD, SERIAL_8N1, PIN_TOF2_RX, -1);

  // Motor driver
  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  ledcAttach(PIN_MOTOR_ENA, 1000, 8);
  ledcWrite(PIN_MOTOR_ENA, 0);

  delay(500);
  Serial.println("{\"boot\":\"conveyor_v4.0\",\"tof1\":16,\"tof2\":17,"
                 "\"tof_baud\":9600,\"proto\":\"ASCII\",\"mqtt\":\"enabled\"}");

  setupWiFi();
  setupMQTT();

  stateStart = millis();
}

void loop() {
  readSensors();
  update();
  processCmd();

  if (millis() - lastReport >= REPORT_MS) {
    lastReport = millis();
    sendStatus();
  }

  // Heartbeat (retained MQTT message)
  if (mqttConnected && millis() - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = millis();
    char hb[64];
    snprintf(hb, sizeof(hb), "{\"alive\":%lu,\"count\":%d}", millis(), objCount);
    mqttClient.publish(TOPIC_HEARTBEAT, hb, 0, true);
  }
}

// === ESP32MQTTClient required callbacks ===

// Called by library when MQTT connection is established
void onMqttConnect(esp_mqtt_client_handle_t client) {
  if (mqttClient.isMyTurn(client)) {
    mqttConnected = true;
    Serial.println("{\"mqtt\":\"connected\"}");

    mqttClient.subscribe(TOPIC_CMD, [](const std::string& payload) {
      handleMqttCommand(TOPIC_CMD, payload);
    });
    mqttClient.subscribe(TOPIC_VISION, [](const std::string& payload) {
      handleMqttCommand(TOPIC_VISION, payload);
    });

    mqttClient.publish(TOPIC_HEARTBEAT, "online", 0, true);
  }
}

// ESP-IDF MQTT event bridge (required boilerplate by library)
#if ESP_IDF_VERSION < ESP_IDF_VERSION_VAL(5, 0, 0)
esp_err_t handleMQTT(esp_mqtt_event_handle_t event) {
  mqttClient.onEventCallback(event);
  return ESP_OK;
}
#else
void handleMQTT(void* handler_args, esp_event_base_t base,
                int32_t event_id, void* event_data) {
  auto* event = static_cast<esp_mqtt_event_handle_t>(event_data);
  mqttClient.onEventCallback(event);
}
#endif
