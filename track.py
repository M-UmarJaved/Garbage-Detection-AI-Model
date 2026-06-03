import cv2
from ultralytics import YOLO
import time
import threading
import serial

# =====================================================
# CONFIGURATION
# =====================================================

MODEL_PATH    = "runs/detect/runs/train/garbage_model-4/weights/best.pt"
STREAM_URL    = "http://192.168.4.1:81/stream"
CONFIDENCE    = 0.7
IMAGE_SIZE    = 320
SERIAL_PORT   = "COM9"
BAUD_RATE     = 115200

DEAD_ZONE_X   = 40
DEAD_ZONE_Y   = 40

FRAME_W       = 320
FRAME_H       = 240
CENTER_X      = FRAME_W // 2
CENTER_Y      = FRAME_H // 2

# =====================================================
# CONNECT MOTOR CONTROLLER
# =====================================================

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("✅ Motor controller connected on " + SERIAL_PORT)
except Exception as e:
    print(f"⚠️  Motor not connected: {e}")
    print("   Check: Is ESP32 WROOM plugged in USB?")
    print("   Check: Is COM9 correct port?")
    print("   Check: Arduino IDE → Tools → Port")
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
        self.stream  = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed = False
        self.frame   = None
        self.stopped = False
        self.thread  = threading.Thread(target=self.update, daemon=True)
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

fps_time      = time.time()
fps_count     = 0
fps_display   = 0
frame_counter = 0
last_results  = None
last_cmd      = ""
last_cmd_time = 0
CMD_INTERVAL  = 0.2

# =====================================================
# QUADRANT LOGIC
# =====================================================

def get_quadrant_command(px, py):
    mx = px - CENTER_X
    my = CENTER_Y - py

    # Reduce dead zones for better turning response
    dead_x = 15   # was 40
    dead_y = 15   # was 40

    in_dead_x = abs(mx) < dead_x
    in_dead_y = abs(my) < dead_y

    if in_dead_x and in_dead_y:
        return "STOP"

    if in_dead_x and not in_dead_y:
        return "FORWARD" if my > 0 else "BACKWARD"

    if in_dead_y and not in_dead_x:
        return "RIGHT" if mx > 0 else "LEFT"

    # Quadrant cases (no dead zone in either axis)
    if mx > 0 and my > 0:
        return "FWD_RIGHT"
    if mx < 0 and my > 0:
        return "FWD_LEFT"
    if mx < 0 and my < 0:
        return "BWD_LEFT"
    if mx > 0 and my < 0:
        return "BWD_RIGHT"

    return "STOP"

# =====================================================
# SEND COMMAND
# =====================================================

def send_command(cmd):
    global last_cmd, last_cmd_time
    now = time.time()

    if arduino and (cmd != last_cmd or now - last_cmd_time > CMD_INTERVAL):
        try:
            arduino.write(f"{cmd}\n".encode())
            last_cmd      = cmd
            last_cmd_time = now
        except Exception as e:
            print(f"⚠️  Serial write error: {e}")
    elif not arduino:
        last_cmd = cmd

# =====================================================
# DRAW GRID (No text on camera - clean frame!)
# =====================================================

def draw_clean_grid(frame, w, h):
    cx = CENTER_X
    cy = CENTER_Y

    # X axis
    cv2.line(frame, (0, cy), (w, cy), (255, 255, 255), 1)
    # Y axis
    cv2.line(frame, (cx, 0), (cx, h), (255, 255, 255), 1)

    # Dead zone box only
    cv2.rectangle(frame,
                 (cx - DEAD_ZONE_X, cy - DEAD_ZONE_Y),
                 (cx + DEAD_ZONE_X, cy + DEAD_ZONE_Y),
                 (0, 255, 0), 1)

# =====================================================
# MAIN LOOP
# =====================================================

print("\n" + "="*60)
print("QUADRANT TRACKING SYSTEM")
print("="*60)
print(f"Dead zone: X=±{DEAD_ZONE_X}px  Y=±{DEAD_ZONE_Y}px")
print(f"Motor controller: {'CONNECTED on ' + SERIAL_PORT if arduino else 'NOT CONNECTED'}")
print("="*60)
print("Press Q=quit  S=screenshot  SPACE=stop motors")
print("="*60 + "\n")

log_time = time.time()  # For throttled terminal logs

while True:
    grabbed, frame = vs.read()

    if not grabbed or frame is None:
        continue

    height, width = frame.shape[:2]
    frame_counter += 1

    # ─── DETECTION ───────────────────────────────────

    if frame_counter % 2 == 0:
        # Run detection on CLEAN frame (before drawing anything!)
        results      = model(frame.copy(), conf=CONFIDENCE,
                            imgsz=IMAGE_SIZE, verbose=False)
        last_results = results
    else:
        results = last_results if last_results else None

    # Draw grid AFTER detection (so text doesn't confuse AI)
    draw_clean_grid(frame, width, height)

    # ─── PROCESS ─────────────────────────────────────

    object_found = False
    cmd          = "STOP"

    if results and len(results[0].boxes) > 0:

        # Pick highest confidence detection
        best_box  = None
        best_conf = 0

        for box in results[0].boxes:
            conf = box.conf[0].item()
            if conf > best_conf:
                best_conf = conf
                best_box  = box

        if best_box is not None:
            x1, y1, x2, y2 = best_box.xyxy[0].int().tolist()
            confidence      = best_box.conf[0].item()
            label           = model.names[int(best_box.cls[0])]
            center_x        = (x1 + x2) // 2
            center_y        = (y1 + y2) // 2

            object_found    = True
            cmd             = get_quadrant_command(center_x, center_y)

            # Math coordinates
            mx = center_x - CENTER_X
            my = CENTER_Y  - center_y

            # Draw bounding box only (NO text on frame)
            box_color = {
                "STOP":      (0, 255, 0),
                "FORWARD":   (0, 255, 0),
                "BACKWARD":  (0, 255, 0),
                "LEFT":      (0, 165, 255),
                "RIGHT":     (0, 165, 255),
                "FWD_LEFT":  (0, 255, 255),
                "FWD_RIGHT": (0, 255, 255),
                "BWD_LEFT":  (255, 165, 0),
                "BWD_RIGHT": (255, 165, 0),
            }.get(cmd, (255, 255, 255))

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # Center dot on object
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

            # Arrow from frame center to object
            cv2.arrowedLine(frame,
                           (CENTER_X, CENTER_Y),
                           (center_x, center_y),
                           box_color, 2)

            # Terminal log (throttled - every 0.5 sec)
            if time.time() - log_time > 0.5:
                print(f"[DETECT] {label} | conf:{confidence:.2f} | "
                      f"pos:({mx:+d},{my:+d}) | cmd:{cmd} | FPS:{fps_display}")
                log_time = time.time()

    # No object
    if not object_found:
        cmd = "STOP"
        if time.time() - log_time > 2.0:
            print(f"[WAITING] No object detected | FPS:{fps_display}")
            log_time = time.time()

    # Send command
    send_command(cmd)

    # ─── FPS ─────────────────────────────────────────

    fps_count += 1
    if time.time() - fps_time >= 1.0:
        fps_display = fps_count
        fps_count   = 0
        fps_time    = time.time()
        # FPS log every second
        print(f"[FPS] {fps_display} | "
              f"Motors:{'ON' if arduino else 'OFF'} | "
              f"Last CMD:{last_cmd}")

    # ─── DISPLAY (clean frame - no HUD text) ─────────

    cv2.imshow("Quadrant Tracking", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        fname = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(fname, frame)
        print(f"[SAVED] {fname}")
    elif key == ord(' '):
        send_command("STOP")
        print("[MANUAL] Motors stopped")

# ─── CLEANUP ─────────────────────────────────────────

vs.stop()
if arduino:
    arduino.write(b"STOP\n")
    arduino.close()
cv2.destroyAllWindows()
print("✅ System stopped")