import serial
import json
import base64
import time
import base58

SERIAL_PORT = "/dev/ttyUSB0"  # or COM3 on Windows
BAUD_RATE = 115200
TIMEOUT = 30  # seconds — user needs time to tap card

def send_to_esp32(message_bytes: bytes) -> dict:
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
            time.sleep(2)
            ser.flushInput()

            msg_b64 = base64.b64encode(message_bytes).decode("utf-8")
            payload = json.dumps({"message": msg_b64}) + "\n"

            # print(f"SENDING_LEN: {len(message_bytes)}")
            # print(f"SENDING_HEX: {message_bytes.hex()}")

            ser.write(payload.encode("utf-8"))

            debug_lines = []

            while True:
                line = ser.readline().decode("utf-8").strip()
                if not line:
                    continue

                # print(f"ESP32 RAW: {line}")  # prints to Flask terminal

                if line.startswith("MSG_LEN:") or line.startswith("MSG_HEX:"):
                    debug_lines.append(line)
                    continue

                if not line.startswith("{"):
                    continue

                response = json.loads(line)

                # attach debug info to response
                response["debug"] = debug_lines

                if response.get("success"):
                    sig = response["signature"]
                    decoded = base58.b58decode(sig)
                    if len(decoded) != 64:
                        return {
                            "success": False,
                            "error": f"Bad signature length: {len(decoded)} bytes"
                        }

                return response

    except serial.SerialTimeoutException:
        return {"success": False, "error": "ESP32 timeout — card not tapped"}
    except Exception as e:
        return {"success": False, "error": str(e)}