import cv2
from ultralytics import YOLO
import time
import threading
import serial

# =====================================================
# CONFIGURATION
# =====================================================

MODEL_PATH = "runs/detect/runs/train/garbage_model-4/weights/best.pt"
STREAM_URL = "http://192.168.4.1:81/stream"
CONFIDENCE_THRESHOLD = 0.7
IMAGE_SIZE = 320
SERIAL_PORT = "COM9"
BAUD_RATE = 115200

# =====================================================
# FRAME ZONES - Divides frame into 5 sections
# =====================================================

# Frame width = 320px
# |  FAR LEFT  | LEFT | CENTER | RIGHT | FAR RIGHT |
# |    0-64    |64-128|128-192 |192-256|  256-320  |

ZONE_FAR_LEFT   = 64    # 0   to 64
ZONE_LEFT       = 128   # 64  to 128
ZONE_CENTER_L   = 144   # 128 to 144  (dead zone left)
ZONE_CENTER_R   = 176   # 144 to 176  (dead zone - no movement)
ZONE_RIGHT      = 192   # 176 to 192
ZONE_FAR_RIGHT  = 256   # 192 to 256
                        # 256 to 320 = FAR RIGHT

# =====================================================
# CONNECT MOTOR CONTROLLER
# =====================================================

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("✅ Motor controller connected")
except Exception as e:
    print(f"⚠️ Motor not connected: {e}")
    arduino = None

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading model...")
model = YOLO(MODEL_PATH)
print(f"✅ Model loaded | Classes: {model.names}")

# =====================================================
# VIDEO STREAM
# =====================================================

class VideoStream:
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed = False
        self.frame = None
        self.stopped = False
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while not self.stopped:
            if self.stream.isOpened():
                (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.grabbed, self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

print("Connecting to camera...")
vs = VideoStream(STREAM_URL)
time.sleep(2)
print("✅ Camera connected")

# =====================================================
# VARIABLES
# =====================================================

fps_time        = time.time()
fps_count       = 0
fps_display     = 0
frame_counter   = 0
last_results    = None
last_command    = ""
last_cmd_time   = 0
CMD_INTERVAL    = 0.3  # Send command every 0.3 seconds

# =====================================================
# COMMAND FUNCTION
# =====================================================

def send_command(cmd):
    global last_command, last_cmd_time
    current_time = time.time()

    # Only send if command changed OR enough time passed
    if arduino and (cmd != last_command or
                    current_time - last_cmd_time > CMD_INTERVAL):
        arduino.write(f"{cmd}\n".encode())
        print(f"→ Command: {cmd}")
        last_command = cmd
        last_cmd_time = current_time

# =====================================================
# GET DIRECTION FROM X POSITION
# =====================================================

def get_direction(center_x, frame_width):
    # Divide frame into zones
    if center_x < ZONE_FAR_LEFT:
        return "TURN_LEFT_FAST"    # Far left corner
    elif center_x < ZONE_LEFT:
        return "TURN_LEFT"         # Left side
    elif center_x < ZONE_CENTER_R:
        return "CENTER"            # Dead zone - stop
    elif center_x < ZONE_FAR_RIGHT:
        return "TURN_RIGHT"        # Right side
    else:
        return "TURN_RIGHT_FAST"   # Far right corner

# =====================================================
# DRAW ZONES ON FRAME
# =====================================================

def draw_zones(frame, width, height):
    # Draw zone dividers
    cv2.line(frame, (ZONE_FAR_LEFT, 0),  (ZONE_FAR_LEFT, height),  (0, 0, 255), 1)
    cv2.line(frame, (ZONE_LEFT, 0),      (ZONE_LEFT, height),      (0, 165, 255), 1)
    cv2.line(frame, (ZONE_CENTER_L, 0),  (ZONE_CENTER_L, height),  (0, 255, 0), 1)
    cv2.line(frame, (ZONE_CENTER_R, 0),  (ZONE_CENTER_R, height),  (0, 255, 0), 1)
    cv2.line(frame, (ZONE_RIGHT, 0),     (ZONE_RIGHT, height),     (0, 165, 255), 1)
    cv2.line(frame, (ZONE_FAR_RIGHT, 0), (ZONE_FAR_RIGHT, height), (0, 0, 255), 1)

    # Zone labels
    cv2.putText(frame, "FL",  (5,  15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    cv2.putText(frame, "L",   (70, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
    cv2.putText(frame, "CTR", (130,15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.putText(frame, "R",   (200,15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
    cv2.putText(frame, "FR",  (265,15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

# =====================================================
# MAIN LOOP
# =====================================================

print("\n" + "="*60)
print("🚀 DIRECTIONAL DETECTION SYSTEM")
print("="*60)
print("Zones: FAR_LEFT | LEFT | CENTER | RIGHT | FAR_RIGHT")
print("Press Q=quit, S=screenshot, SPACE=stop motors")
print("="*60 + "\n")

while True:
    grabbed, frame = vs.read()

    if not grabbed or frame is None:
        continue

    height, width = frame.shape[:2]
    zone_height = int(height * 0.6)

    # Draw detection zone
    cv2.rectangle(frame, (0, 0), (width, zone_height), (255, 0, 0), 2)

    # Draw zone dividers
    draw_zones(frame, width, height)

    frame_counter += 1

    # Detect every 2nd frame
    if frame_counter % 2 == 0:
        results = model(frame, conf=CONFIDENCE_THRESHOLD,
                       imgsz=IMAGE_SIZE, verbose=False)
        last_results = results
    else:
        results = last_results if last_results else None

    # =====================================================
    # PROCESS DETECTIONS
    # =====================================================

    object_found = False

    if results and len(results[0].boxes) > 0:
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].int().tolist()
            confidence      = box.conf[0].item()
            label           = model.names[int(box.cls[0])]
            center_x        = (x1 + x2) // 2
            center_y        = (y1 + y2) // 2

            if center_y < zone_height:
                object_found = True

                # Get direction command
                direction = get_direction(center_x, width)

                # Send command to motors
                send_command(direction)

                # Draw detection
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Label background
                cv2.rectangle(frame,
                             (x1, y1 - 25),
                             (x1 + 160, y1),
                             (0, 255, 0), -1)
                cv2.putText(frame,
                           f"{label} {confidence:.2f}",
                           (x1, y1 - 7),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

                # Draw center dot
                cv2.circle(frame, (center_x, center_y), 6, (0, 0, 255), -1)

                # Draw direction text on frame
                dir_color = {
                    "TURN_LEFT_FAST":  (0, 0, 255),
                    "TURN_LEFT":       (0, 165, 255),
                    "CENTER":          (0, 255, 0),
                    "TURN_RIGHT":      (0, 165, 255),
                    "TURN_RIGHT_FAST": (0, 0, 255)
                }.get(direction, (255, 255, 255))

                cv2.putText(frame,
                           f"→ {direction}",
                           (center_x - 60, center_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, dir_color, 2)

    # No object found - stop motors
    if not object_found:
        send_command("STOP")

    # =====================================================
    # FPS
    # =====================================================

    fps_count += 1
    if time.time() - fps_time >= 1.0:
        fps_display = fps_count
        print(f"FPS: {fps_display}")
        fps_count  = 0
        fps_time   = time.time()

    # =====================================================
    # DISPLAY INFO
    # =====================================================

    cv2.putText(frame, f"FPS: {fps_display}",
               (10, height - 80),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    motor_status = "CONNECTED" if arduino else "DISCONNECTED"
    motor_color  = (0, 255, 0) if arduino else (0, 0, 255)
    cv2.putText(frame, f"Motors: {motor_status}",
               (10, height - 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, motor_color, 2)

    cv2.putText(frame, f"CMD: {last_command}",
               (10, height - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    cv2.imshow("Directional Detection System", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        fname = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(fname, frame)
        print(f"📸 Saved: {fname}")
    elif key == ord(' '):
        send_command("STOP")
        print("⏹️ Manual stop")

# Cleanup
vs.stop()
if arduino:
    arduino.write(b"STOP\n")
    arduino.close()
cv2.destroyAllWindows()
print("✅ System stopped")