// 사용자 제공 원본 스니펫 — HW 검증용 독립 테스트
// 목적: v5.0 통합 펌웨어 NDEF 파서와 동일 로직인지 확인 + RC522 RF 안테나 자체가 태그 감지 가능한지 확인
// VSPI 기본 (SS=5, RST=22, SCK=18, MISO=19, MOSI=23)
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN   5
#define RST_PIN  22

MFRC522 mfrc522(SS_PIN, RST_PIN);

// ===== NDEF 파싱 =====
void parseNDEF(byte *data, int length) {

  for (int i = 0; i < length - 2; i++) {

    // 정확한 NDEF 시작 조건
    if (data[i] == 0x03 && data[i + 2] == 0xD1) {

      byte ndefLength = data[i + 1];
      int index = i + 2;

      // ===== NDEF Header =====
      index++;  // header
      index++;  // type length
      byte payloadLength = data[index++];

      // ===== Type =====
      char type = data[index++];

      // ===== Text 타입 =====
      if (type == 'T') {
        byte status = data[index++];
        byte langLen = status & 0x3F;

        index += langLen;

        Serial.print("텍스트: ");
        for (int j = 0; j < payloadLength - langLen - 1; j++) {
          Serial.print((char)data[index++]);
        }
        Serial.println();
      }

      return;
    }
  }

  Serial.println("NDEF 못 찾음");
}

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  Serial.println("NDEF 분석 준비 완료");
}

void loop() {

  if (!mfrc522.PICC_IsNewCardPresent() ||
      !mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  Serial.println("\n카드 감지됨\n");

  // ===== 여러 페이지 읽기 =====
  byte buffer[18];
  byte size = sizeof(buffer);

  byte fullData[64];
  int offset = 0;

  for (byte page = 4; page < 16; page += 4) {

    if (mfrc522.MIFARE_Read(page, buffer, &size) == MFRC522::STATUS_OK) {

      for (int i = 0; i < 16; i++) {
        fullData[offset++] = buffer[i];
      }
    }
  }

  // ===== NDEF 분석 =====
  parseNDEF(fullData, offset);

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  Serial.println("\n카드를 제거하세요.");
  delay(3000);
}
