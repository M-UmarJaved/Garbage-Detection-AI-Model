import cv2
from ultralytics import YOLO
import time
import threading
import socket
import os
import voice

voice.init()

def is_voice_enabled():
    if os.path.exists("voice_cfg.txt"):
        with open("voice_cfg.txt", "r") as f:
            return f.read().strip() == "1"
    return True

# =====================================================
# CONFIGURATION
# =====================================================

MODEL_PATH  = "runs/detect/runs/train/garbage_model-4/weights/best.pt"
STREAM_URL  = "http://192.168.4.1:81/stream"
CONFIDENCE  = 0.75
IMAGE_SIZE  = 320

# ESP32-WROOM UDP settings
WROOM_IP    = "192.168.4.2"
WROOM_PORT  = 1234

DEAD_ZONE_X = 60
DEAD_ZONE_Y = 60

SOFT_ZONE_X = 120
HARD_ZONE_X = 180

SOFT_ZONE_Y = 120
HARD_ZONE_Y = 180

CMD_INTERVAL = 0.20

FRAME_W     = 320
FRAME_H     = 240
CENTER_X    = FRAME_W // 2
CENTER_Y    = FRAME_H // 2

# =====================================================
# UDP SOCKET SETUP (FAST!)
# =====================================================

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"✅ UDP socket ready → {WROOM_IP}:{WROOM_PORT}")

# Local IPC socket for Dashboard
ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"✅ IPC socket ready → 127.0.0.1:5555 & 5556")

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading model...")
model = YOLO(MODEL_PATH)
print(f"✅ Model loaded")

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
log_time      = time.time()

# =====================================================
# SEND COMMAND VIA UDP (FAST - 5-10ms!)
# =====================================================

def send_command(cmd):
    global last_cmd, last_cmd_time

    now = time.time()

    if cmd != last_cmd or now - last_cmd_time > CMD_INTERVAL:

        print("SENDING:", cmd)

        last_cmd = cmd
        last_cmd_time = now

        try:
            udp_socket.sendto(
                cmd.encode(),
                (WROOM_IP, WROOM_PORT)
            )

        except Exception as e:
            print(e)

# =====================================================
# QUADRANT LOGIC
# =====================================================

def get_precise_command(px, py):

    # Camera looks upward
    # Car should move under the paper

    mx = center_x - CENTER_X
    my = center_y - CENTER_Y

    abs_mx = abs(mx)
    abs_my = abs(my)

    if abs_mx < DEAD_ZONE_X and abs_my < DEAD_ZONE_Y:
        return "STOP"

    # Pure vertical movement
    if abs_my > abs_mx:

        if my < 0:
            if abs_my > HARD_ZONE_Y:
                return "FORWARD_FAST"
            elif abs_my > SOFT_ZONE_Y:
                return "FORWARD"
            else:
                return "FORWARD_SLOW"

        else:
            if abs_my > HARD_ZONE_Y:
                return "BACKWARD_FAST"
            elif abs_my > SOFT_ZONE_Y:
                return "BACKWARD"
            else:
                return "BACKWARD_SLOW"

    # Pure horizontal movement
    else:

        if mx < 0:
            if abs_mx > HARD_ZONE_X:
                return "LEFT_FAST"
            elif abs_mx > SOFT_ZONE_X:
                return "LEFT"
            else:
                return "LEFT_SLOW"

        else:
            if abs_mx > HARD_ZONE_X:
                return "RIGHT_FAST"
            elif abs_mx > SOFT_ZONE_X:
                return "RIGHT"
            else:
                return "RIGHT_SLOW"




def get_color(cmd):
    if "STOP"     in cmd: return (0, 255, 0)
    if "FORWARD"  in cmd: return (0, 255, 100)
    if "BACKWARD" in cmd: return (100, 255, 0)
    if "LEFT"     in cmd: return (0, 165, 255)
    if "RIGHT"    in cmd: return (0, 100, 255)
    if "FWD"      in cmd: return (0, 255, 255)
    if "BWD"      in cmd: return (255, 165, 0)
    return (255, 255, 255)

def draw_clean_grid(frame):
    cv2.line(frame, (0, CENTER_Y), (FRAME_W, CENTER_Y), (200, 200, 200), 1)
    cv2.line(frame, (CENTER_X, 0), (CENTER_X, FRAME_H), (200, 200, 200), 1)
    cv2.rectangle(frame,
                 (CENTER_X - DEAD_ZONE_X, CENTER_Y - DEAD_ZONE_Y),
                 (CENTER_X + DEAD_ZONE_X, CENTER_Y + DEAD_ZONE_Y),
                 (0, 255, 0), 1)

# =====================================================
# MAIN LOOP
# =====================================================

print("\n" + "="*60)
print("UDP FAST TRACKING SYSTEM")
print("="*60)
print(f"Camera : {STREAM_URL}")
print(f"WROOM  : {WROOM_IP}:{WROOM_PORT} (UDP)")
print("Signal delay: ~5-10ms (was 100-500ms)")
print("="*60 + "\n")

while True:
    grabbed, frame = vs.read()

    if not grabbed or frame is None:
        continue

    height, width = frame.shape[:2]
    frame_counter += 1

    if frame_counter % 2 == 0:
        results      = model(frame.copy(), conf=CONFIDENCE,
                            imgsz=IMAGE_SIZE, verbose=False)
        last_results = results
    else:
        results = last_results if last_results else None

    draw_clean_grid(frame)

    object_found = False
    cmd          = "STOP"

    if results and len(results[0].boxes) > 0:
        best_box  = None
        best_conf = 0.0

        for box in results[0].boxes:
            c = box.conf[0].item()
            if c > best_conf:
                best_conf = c
                best_box  = box

        if best_box is not None:
            x1, y1, x2, y2 = best_box.xyxy[0].int().tolist()
            confidence      = best_box.conf[0].item()
            label           = model.names[int(best_box.cls[0])]
            center_x        = (x1 + x2) // 2
            center_y        = (y1 + y2) // 2
            mx              = center_x - CENTER_X
            my              = CENTER_Y - center_y

            object_found    = True
            cmd             = get_precise_command(center_x, center_y)
            color           = get_color(cmd)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.arrowedLine(frame, (CENTER_X, CENTER_Y),
                           (center_x, center_y), color, 2, tipLength=0.3)

            if time.time() - log_time > 0.4:
                print(f"[DETECT] {label:<15} conf:{confidence:.2f} "
                      f"pos:({mx:+4d},{my:+4d}) → {cmd:<18} fps:{fps_display}")
                log_time = time.time()
                if is_voice_enabled():
                    voice.speak(label, confidence)

    if not object_found:
        cmd = "STOP"
        if time.time() - log_time > 2.0:
            print(f"[WAITING] No object | fps:{fps_display}")
            log_time = time.time()

    send_command(cmd)

    fps_count += 1
    if time.time() - fps_time >= 1.0:
        fps_display = fps_count
        fps_count   = 0
        fps_time    = time.time()
        print(f"[FPS] {fps_display:2d} | cmd:{last_cmd:<18}")

    cv2.imshow("UDP Fast Tracking", frame)

    # ── IPC BROADCAST TO DASHBOARD (Metadata Only) ──
    try:
        import json
        _conf = best_conf if 'best_conf' in locals() else 0.0
        _label = label if 'label' in locals() and object_found else ""
        meta = {"fps": fps_display, "cmd": cmd, "conf": _conf, "label": _label}
        ipc_socket.sendto(json.dumps(meta).encode(), ('127.0.0.1', 5555))
    except Exception as e:
        print(f"IPC Error: {e}")

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        fname = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(fname, frame)
        print(f"[SAVED] {fname}")
    elif key == ord(' '):
        send_command("STOP")
        print("[EMERGENCY STOP]")

# Cleanup
vs.stop()
udp_socket.sendto(b"STOP", (WROOM_IP, WROOM_PORT))
udp_socket.close()
cv2.destroyAllWindows()
voice.shutdown()
print("Clean exit.")