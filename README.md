# ESP32 RFID Solana Hardware Wallet

A DIY Solana hardware wallet built using an ESP32 and RC522 RFID reader.

This project allows an ESP32 to act as a hardware signer for Solana transactions. Transactions are created in a Flask web app, approved using an RFID tag, signed on the ESP32, and then broadcast to Solana Devnet.

---

# Features

* RFID-based transaction approval
* ESP32 signs transactions locally using Ed25519
* Flask web dashboard
* Solana Devnet support
* Wallet balance viewer
* Duplicate scan protection
* LED approval indicator
* Real transaction broadcasting

---

# Architecture

```text
Browser UI
    ↓
Flask Backend
    ↓
Serial Communication
    ↓
ESP32 + RC522 RFID
    ↓
Ed25519 Transaction Signing
    ↓
Flask broadcasts to Solana Devnet
```

---

# Hardware Required

* ESP32 Dev Board
* RC522 RFID Module
* RFID Card / Tag
* Micro USB Cable

Optional:

* OLED display
* Secure Element (ATECC608A)

---

# Wiring

## RC522 → ESP32

| RC522 | ESP32   |
| ----- | ------- |
| SDA   | GPIO 5  |
| SCK   | GPIO 18 |
| MOSI  | GPIO 23 |
| MISO  | GPIO 19 |
| RST   | GPIO 22 |
| GND   | GND     |
| 3.3V  | 3.3V    |

---

# Project Structure

```text
esp32_wallet_signer/
│
├── app.py
├── serial_wallet.py
├── solana_utils.py
├── generate_wallet.py
│
├── templates/
│   └── index.html
│
├── static/
│   └── style.css
│
├── esp32/
│   └── esp32_wallet.ino
│
├── requirements.txt
└── README.md
```

---

# Setup

## 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/esp32_wallet_signer.git

cd esp32_wallet_signer
```

---

# 2. Create Python Environment

Linux/macOS:

```bash
python3 -m venv venv

source venv/bin/activate
```

Windows:

```bash
python -m venv venv

venv\Scripts\activate
```

---

# 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 4. Generate Wallet

Run:

```bash
python generate_wallet.py
```

This prints:

* Public Key
* Private Key Bytes
* Private Key Base58

---

# 5. Configure ESP32 Wallet

Copy the generated private key bytes into:

```cpp
uint8_t PRIVATE_KEY[64] = {
  ...
};
```

inside:

```text
esp32_wallet.ino
```

---

# 6. Set Wallet Address in Flask

Update:

```python
WALLET_ADDRESS = "YOUR_PUBLIC_KEY"
```

inside:

```text
app.py
```

and:

```python
ESP32_WALLET = "YOUR_PUBLIC_KEY"
```

inside:

```text
solana_utils.py
```

---

# 7. Install Arduino Libraries

Install these libraries using Arduino IDE Library Manager:

* MFRC522
* ArduinoJson
* Crypto

---

# 8. Upload ESP32 Firmware

Open:

```text
esp32/esp32_wallet.ino
```

Select:

* Board: ESP32 Dev Module
* Upload Speed: 115200

Upload firmware.

---

# 9. Find Serial Port

Linux:

```bash
ls /dev/ttyUSB*
```

Windows:
Check Device Manager for COM port.

Update:

```python
SERIAL_PORT = "/dev/ttyUSB0"
```

inside:

```text
serial_wallet.py
```

---

# 10. Run Flask App

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# Using the Wallet

1. Enter recipient wallet
2. Enter amount
3. Click "Send Transaction"
4. ESP32 LED starts blinking
5. Scan authorized RFID tag
6. ESP32 signs transaction
7. Flask broadcasts transaction to Solana Devnet

---

# RFID Authorization

Update authorized RFID UID:

```cpp
byte allowedUID[4] = {
  0xE1, 0xA9, 0x10, 0x06
};
```

inside ESP32 firmware.

---

# Getting RFID UID

Upload a simple RFID reader sketch and scan your tag to print UID in Serial Monitor.

---

# Solana Devnet Faucet

Get free Devnet SOL:

[Solana Faucet](https://faucet.solana.com?utm_source=chatgpt.com)

---

# Security Notes

This is an educational project.

Current limitations:

* Private key stored in ESP32 flash
* No secure element
* No encrypted storage

Do NOT use mainnet funds.

---

# Future Improvements

* OLED transaction preview
* Multi-wallet support
* Transaction history
* Secure element integration
* WebSocket live updates
* Mobile support
* Replay protection
* PIN verification

---

# License

MIT License

---

# Acknowledgements

Built using:

* [Flask](https://flask.palletsprojects.com?utm_source=chatgpt.com)
* [Solana Python SDK](https://github.com/michaelhly/solana-py?utm_source=chatgpt.com)
* [ESP32 Arduino Core](https://github.com/espressif/arduino-esp32?utm_source=chatgpt.com)
* [MFRC522 Library](https://github.com/miguelbalboa/rfid?utm_source=chatgpt.com)
