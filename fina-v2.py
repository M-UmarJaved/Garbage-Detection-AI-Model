"""
fina-v2.py  —  Main Garbage Detection + Full Feature Stack
============================================================
Features in this version:
  ✅ YOLO real-time object detection (offline, no internet)
  ✅ Zone-based directional basket control via Serial
  ✅ Event logging to SQLite   (logger.py)
  ✅ Offline voice feedback    (voice.py)
  ✅ Bin fill HTTP server      (fill_server.py)
  ✅ Live dashboard available  (streamlit run dashboard.py)
  ✅ PDF report generation     (python report.py)
"""

import sys
import cv2
# Force UTF-8 output on Windows so emoji print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from ultralytics import YOLO
import time
import threading
import serial

# ─────────────────────────────────────────────
# FEATURE PLUG-INS
# ─────────────────────────────────────────────
import logger
import voice
import fill_server

# =====================================================
# CONFIGURATION
# =====================================================

MODEL_PATH           = "runs/detect/runs/train/garbage_model-4/weights/best.pt"
STREAM_URL           = "http://192.168.4.1:81/stream"
CONFIDENCE_THRESHOLD = 0.7
IMAGE_SIZE           = 320
SERIAL_PORT          = "COM9"
BAUD_RATE            = 115200

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

# ─────────────────────────────────────────────
# INITIALISE PLUG-IN MODULES
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("🚀 GARBAGE DETECTION SYSTEM  —  FULL FEATURE MODE")
print("=" * 60)

# 1. Database
logger.init()
session_id = logger.start_session()

# 2. Voice engine (background thread)
voice.init()

# 3. Bin fill server (background thread, port 5050)
fill_server.start()

# =====================================================
# CONNECT MOTOR CONTROLLER
# =====================================================

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("[OK] Motor controller connected")
except Exception as e:
    print(f"[WARN] Motor not connected: {e}")
    arduino = None

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading model...")
model = YOLO(MODEL_PATH)
print(f"[OK] Model loaded | Classes: {model.names}")

# =====================================================
# VIDEO STREAM  (threaded for minimum latency)
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

print("Connecting to ESP32-CAM...")
vs = VideoStream(STREAM_URL)
time.sleep(2)
print("[OK] Camera connected")

# =====================================================
# VARIABLES
# =====================================================

fps_time        = time.time()
fps_count       = 0
fps_display     = 0.0
frame_counter   = 0
last_results    = None
last_command    = ""
last_cmd_time   = 0
CMD_INTERVAL    = 0.3   # seconds between serial commands
total_logged    = 0     # tracks how many events logged this session

print("\nControls:")
print("  Q          -> quit")
print("  S          -> save screenshot")
print("  SPACE      -> stop motors")
print("  R          -> generate PDF report now")
print("  D          -> print DB summary to console")
print("=" * 60 + "\n")

# =====================================================
# HELPER: SEND SERIAL COMMAND
# =====================================================

def send_command(cmd: str) -> None:
    global last_command, last_cmd_time
    current_time = time.time()
    if arduino and (cmd != last_command or
                    current_time - last_cmd_time > CMD_INTERVAL):
        arduino.write(f"{cmd}\n".encode())
        print(f"-> Command: {cmd}")
        last_command    = cmd
        last_cmd_time   = current_time

# =====================================================
# HELPER: GET DIRECTION FROM X POSITION
# =====================================================

def get_direction(center_x: int, frame_width: int) -> str:
    if center_x < ZONE_FAR_LEFT:
        return "TURN_LEFT_FAST"
    elif center_x < ZONE_LEFT:
        return "TURN_LEFT"
    elif center_x < ZONE_CENTER_R:
        return "CENTER"
    elif center_x < ZONE_FAR_RIGHT:
        return "TURN_RIGHT"
    else:
        return "TURN_RIGHT_FAST"

# =====================================================
# HELPER: DRAW ZONE DIVIDERS ON FRAME
# =====================================================

def draw_zones(frame, width: int, height: int) -> None:
    cv2.line(frame, (ZONE_FAR_LEFT, 0),  (ZONE_FAR_LEFT, height),  (0, 0, 255), 1)
    cv2.line(frame, (ZONE_LEFT, 0),      (ZONE_LEFT, height),      (0, 165, 255), 1)
    cv2.line(frame, (ZONE_CENTER_L, 0),  (ZONE_CENTER_L, height),  (0, 255, 0), 1)
    cv2.line(frame, (ZONE_CENTER_R, 0),  (ZONE_CENTER_R, height),  (0, 255, 0), 1)
    cv2.line(frame, (ZONE_RIGHT, 0),     (ZONE_RIGHT, height),     (0, 165, 255), 1)
    cv2.line(frame, (ZONE_FAR_RIGHT, 0), (ZONE_FAR_RIGHT, height), (0, 0, 255), 1)
    cv2.putText(frame, "FL",  (5,   15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    cv2.putText(frame, "L",   (70,  15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
    cv2.putText(frame, "CTR", (130, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.putText(frame, "R",   (200, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
    cv2.putText(frame, "FR",  (265, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

# =====================================================
# MAIN DETECTION LOOP
# =====================================================

while True:
    grabbed, frame = vs.read()

    if not grabbed or frame is None:
        continue

    height, width  = frame.shape[:2]
    zone_height    = int(height * 0.6)

    # Draw detection zone boundary
    cv2.rectangle(frame, (0, 0), (width, zone_height), (255, 0, 0), 2)

    # Draw zone dividers
    draw_zones(frame, width, height)

    frame_counter += 1

    # ── Run YOLO inference every 2nd frame ──────────
    infer_start = time.time()
    if frame_counter % 2 == 0:
        results = model(frame, conf=CONFIDENCE_THRESHOLD,
                        imgsz=IMAGE_SIZE, verbose=False)
        last_results = results
    else:
        results = last_results if last_results else None
    inference_ms = (time.time() - infer_start) * 1000

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

                # ── Direction calculation ────────────
                direction = get_direction(center_x, width)

                # ── Motor command ────────────────────
                send_command(direction)

                # ── ① EVENT LOGGING ──────────────────
                event = {
                    "timestamp":    time.strftime("%Y-%m-%d %H:%M:%S"),
                    "class":        label,
                    "confidence":   confidence,
                    "fps":          fps_display,
                    "inference_ms": inference_ms,
                    "direction":    direction,
                    "center_x":     center_x,
                    "center_y":     center_y,
                }
                logger.log_detection(event)
                total_logged += 1

                # ── ② VOICE FEEDBACK ─────────────────
                voice.speak(label, confidence)

                # ── Draw detection visuals ───────────
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Label background
                cv2.rectangle(frame,
                               (x1, y1 - 25), (x1 + 160, y1),
                               (0, 255, 0), -1)
                cv2.putText(frame,
                            f"{label} {confidence:.2f}",
                            (x1, y1 - 7),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

                # Center dot
                cv2.circle(frame, (center_x, center_y), 6, (0, 0, 255), -1)

                # Direction label on frame
                dir_color = {
                    "TURN_LEFT_FAST":  (0, 0, 255),
                    "TURN_LEFT":       (0, 165, 255),
                    "CENTER":          (0, 255, 0),
                    "TURN_RIGHT":      (0, 165, 255),
                    "TURN_RIGHT_FAST": (0, 0, 255),
                }.get(direction, (255, 255, 255))

                cv2.putText(frame,
                            f"-> {direction}",
                            (center_x - 60, center_y - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, dir_color, 2)

    # ── No object → stop motors ─────────────────────
    if not object_found:
        send_command("STOP")

    # =====================================================
    # FPS CALCULATION
    # =====================================================

    fps_count += 1
    if time.time() - fps_time >= 1.0:
        fps_display = float(fps_count)
        fps_count   = 0
        fps_time    = time.time()

    # =====================================================
    # DISPLAY OVERLAY
    # =====================================================

    # FPS
    cv2.putText(frame, f"FPS: {int(fps_display)}",
                (10, height - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Motor status
    motor_status = "CONNECTED"  if arduino else "DISCONNECTED"
    motor_color  = (0, 255, 0) if arduino else (0, 0, 255)
    cv2.putText(frame, f"Motors: {motor_status}",
                (10, height - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, motor_color, 2)

    # Last command
    cv2.putText(frame, f"CMD: {last_command}",
                (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # Detections logged counter (top-right)
    cv2.putText(frame, f"Logged: {total_logged}",
                (width - 140, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    # Bin fill levels (top-right)
    fill_info = fill_server.get_latest()
    cv2.putText(frame,
                f"Bin P:{fill_info['plastic_pct']:.0f}% Pa:{fill_info['paper_pct']:.0f}%",
                (width - 200, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 255), 1)

    cv2.imshow("GarbAI - Full Feature System", frame)

    # =====================================================
    # KEYBOARD CONTROLS
    # =====================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

    elif key == ord('s'):
        fname = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(fname, frame)
        print(f"[Screenshot] Saved: {fname}")

    elif key == ord(' '):
        send_command("STOP")
        print("[STOP] Manual stop")

    elif key == ord('r'):
        # Generate PDF report in background thread
        def _gen_report():
            try:
                import report
                path = report.generate_report(period="daily")
                print(f"[Report] Ready: {path}")
            except Exception as ex:
                print(f"[WARN] Report error: {ex}")
        threading.Thread(target=_gen_report, daemon=True).start()
        print("[Report] Generating PDF report...")

    elif key == ord('d'):
        # Print live DB summary to console
        s = logger.get_summary()
        print("\n[DB] DATABASE SUMMARY")
        print(f"   Total detections : {s['total_detections']}")
        print(f"   Plastic bottles  : {s['bottle_count']}")
        print(f"   Crushed papers   : {s['paper_count']}")
        print(f"   Avg confidence   : {s['avg_confidence']}%")
        print(f"   Avg FPS          : {s['avg_fps']}")
        print(f"   Sessions         : {s['sessions_count']}")
        print(f"   Latest plastic   : {s['latest_plastic']}%")
        print(f"   Latest paper     : {s['latest_paper']}%\n")

# =====================================================
# CLEANUP
# =====================================================

vs.stop()
if arduino:
    arduino.write(b"STOP\n")
    arduino.close()
cv2.destroyAllWindows()

# Close DB session
logger.end_session(total_detections=total_logged)
voice.shutdown()

print("\n" + "=" * 60)
print("[OK] GarbAI System Stopped")
print(f"   Session detections logged: {total_logged}")
print(f"   Database: garbage.db")
print("=" * 60)