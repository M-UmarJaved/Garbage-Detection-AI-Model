import serial
import time

# Change this to your actual COM port
PORT = "COM9"
BAUD = 115200

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)               # Wait for ESP32 to reset
    ser.write(b"STATUS\n")
    time.sleep(0.5)
    while ser.in_waiting:
        print(ser.readline().decode().strip())
    ser.close()
    print("✅ Communication successful")
except Exception as e:
    print(f"❌ Failed: {e}")
    print("   Check: Is the ESP32 WROOM plugged in?")
    print("   Check: Is the COM port correct?")
    print("   Check: Is the Serial Monitor closed?")