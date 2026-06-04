#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include "mbedtls/base64.h"
#include "randombytes.h"

extern "C" {
  #include "tweetnacl.h"
}

#define SS_PIN 5
#define RST_PIN 22
#define LED_PIN 2

MFRC522 rfid(SS_PIN, RST_PIN);

enum State { IDLE, WAITING_RFID, SIGNING };
State currentState = IDLE;

byte allowedUID[4] = {0x12, 0x34, 0x56, 0x7A}; //replace with your spi tag, eg. 1234567A

// Full 64-byte Solana keypair: [32-byte seed | 32-byte pubkey]
uint8_t PRIVATE_KEY[64] = {12,34,.....,56,78};

uint8_t* currentMessageBytes = nullptr;
size_t currentMessageLen = 0;

String lastUID = "";
unsigned long lastScanTime = 0;
const unsigned long DEDUP_WINDOW = 10000;

unsigned long lastBlink = 0;
bool ledState = false;

// ==============================
// BASE58 ENCODER
// ==============================
const char* BASE58_ALPHABET =
  "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

String base58Encode(const uint8_t* input, int length) {
  int size = (length * 137 / 100) + 8;
  uint8_t b58[size];
  memset(b58, 0, size);

  int zeros = 0;
  while (zeros < length && input[zeros] == 0) zeros++;

  for (int i = zeros; i < length; i++) {
    int carry = input[i];
    int j = size - 1;
    while (j >= 0) {
      carry += 256 * b58[j];
      b58[j] = carry % 58;
      carry /= 58;
      j--;
    }
  }

  int j = 0;
  while (j < size && b58[j] == 0) j++;

  String result = "";
  for (int i = 0; i < zeros; i++) result += '1';
  while (j < size) result += BASE58_ALPHABET[b58[j++]];

  return result;
}

// ==============================
// RFID HELPERS
// ==============================
String uidToString(MFRC522::Uid *uid) {
  String content = "";
  for (byte i = 0; i < uid->size; i++) {
    if (uid->uidByte[i] < 0x10) content += "0";
    content += String(uid->uidByte[i], HEX);
  }
  content.toUpperCase();
  return content;
}

bool isAuthorized(MFRC522::Uid *uid) {
  if (uid->size != 4) return false;
  for (int i = 0; i < 4; i++) {
    if (uid->uidByte[i] != allowedUID[i]) return false;
  }
  return true;
}

// ==============================
// LED
// ==============================
void blinkLED() {
  if (millis() - lastBlink > 300) {
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
    lastBlink = millis();
  }
}

void successBlink() {
  digitalWrite(LED_PIN, HIGH);
  delay(800);
  digitalWrite(LED_PIN, LOW);
}

// ==============================
// SIGNING — TweetNaCl Ed25519
// ==============================
String signMessage(uint8_t* message, size_t len) {
  // TweetNaCl sign produces: [64-byte signature | original message]
  unsigned long long smlen = 0;
  uint8_t* sm = (uint8_t*)malloc(64 + len);

  if (!sm) return "MEM_ERROR";

  // crypto_sign uses full 64-byte secret key (seed+pubkey) — exactly Solana format
  crypto_sign(
    sm, &smlen,
    message, len,
    PRIVATE_KEY   // full 64 bytes [seed | pubkey]
  );

  // First 64 bytes are the signature
  String result = base58Encode(sm, 64);
  free(sm);

  return result;
}

// ==============================
// SERIAL INPUT
// ==============================
bool readMessageFromSerial(uint8_t* &outMsg, size_t &len) {
  if (!Serial.available()) return false;

  String json = Serial.readStringUntil('\n');
  StaticJsonDocument<2048> doc;

  if (deserializeJson(doc, json)) return false;

  String msg_b64 = doc["message"].as<String>();
  size_t outLen = 0;

  mbedtls_base64_decode(NULL, 0, &outLen,
    (const unsigned char*)msg_b64.c_str(), msg_b64.length());

  outMsg = (uint8_t*)malloc(outLen);
  if (!outMsg) return false;

  if (mbedtls_base64_decode(outMsg, outLen, &outLen,
        (const unsigned char*)msg_b64.c_str(),
        msg_b64.length()) != 0) {
    free(outMsg);
    return false;
  }

  len = outLen;

  // DEBUG — print received bytes as hex
  Serial.print("MSG_LEN:");
  Serial.println(outLen);
  Serial.print("MSG_HEX:");
  for (size_t i = 0; i < outLen; i++) {
    if (outMsg[i] < 0x10) Serial.print("0");
    Serial.print(outMsg[i], HEX);
  }
  Serial.println();

  return true;
}

// ==============================
// SETUP
// ==============================
void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(LED_PIN, OUTPUT);
  SPI.begin(18, 19, 23, 5);
  rfid.PCD_Init();
  Serial.println("ESP32 Solana RFID Wallet Ready");
}

// ==============================
// LOOP
// ==============================
void loop() {

  if (currentState == IDLE) {
    uint8_t* msg = nullptr;
    size_t len = 0;
    if (readMessageFromSerial(msg, len)) {
      currentMessageBytes = msg;
      currentMessageLen = len;
      currentState = WAITING_RFID;
    }
  }

  if (currentState == WAITING_RFID) {
    blinkLED();

    if (!rfid.PICC_IsNewCardPresent()) return;
    if (!rfid.PICC_ReadCardSerial()) return;

    String uid = uidToString(&rfid.uid);

if (!isAuthorized(&rfid.uid)) {

  StaticJsonDocument<192> errDoc;

  errDoc["success"] = false;
  errDoc["error"] = "Unauthorized card";

  // return scanned UID
  errDoc["tag_uid"] = uid;

  serializeJson(errDoc, Serial);
  Serial.println();

  free(currentMessageBytes);
  currentMessageBytes = nullptr;

  currentState = IDLE;

  rfid.PICC_HaltA();

  return;
}

    if (uid == lastUID && millis() - lastScanTime < DEDUP_WINDOW) {
      StaticJsonDocument<128> errDoc;
      errDoc["success"] = false;
      errDoc["error"] = "Duplicate scan";
      serializeJson(errDoc, Serial);
      Serial.println();
      rfid.PICC_HaltA();
      return;
    }

    lastUID = uid;
    lastScanTime = millis();
    currentState = SIGNING;
    digitalWrite(LED_PIN, HIGH);

    String signature = signMessage(currentMessageBytes, currentMessageLen);

    free(currentMessageBytes);
    currentMessageBytes = nullptr;

    StaticJsonDocument<512> doc;
    doc["success"] = true;
    doc["signature"] = signature;
    serializeJson(doc, Serial);
    Serial.println();

    successBlink();
    digitalWrite(LED_PIN, LOW);
    currentState = IDLE;
    rfid.PICC_HaltA();
  }
}