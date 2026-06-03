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

# ESP32 WROOM Serial Port
SERIAL_PORT = "COM9"  # CHANGE THIS! (Check in Arduino IDE)
BAUD_RATE = 115200

# =====================================================
# CONNECT TO ESP32 MOTOR CONTROLLER
# =====================================================

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("✅ Motor controller connected")
except Exception as e:
    print(f"⚠️ Motor controller not connected: {e}")
    print("Running in DETECTION-ONLY mode")
    arduino = None

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading model...")
model = YOLO(MODEL_PATH)
print("✅ Model loaded")

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

print("Connecting to ESP32-CAM...")
vs = VideoStream(STREAM_URL)
time.sleep(2)
print("✅ Camera connected")

fps_time = time.time()
fps_count = 0
fps_display = 0
frame_counter = 0
last_results = None

print("\n" + "="*60)
print("🚀 COMPLETE GARBAGE DETECTION SYSTEM")
print("="*60)
print("Features:")
print("  ✓ Real-time AI detection")
print("  ✓ Automatic basket positioning")
print("  ✓ IR sensor safety limits")
print("="*60)
print("\nPress 'Q' to quit")
print("Press 'S' for screenshot")
print("Press 'SPACE' to stop motors\n")

# =====================================================
# MAIN LOOP
# =====================================================

while True:
    grabbed, frame = vs.read()
    
    if not grabbed or frame is None:
        continue
    
    height, width = frame.shape[:2]
    zone_height = int(height * 0.6)
    
    # Draw detection zone
    cv2.rectangle(frame, (0, 0), (width, zone_height), (255, 0, 0), 2)
    cv2.putText(frame, "DETECTION ZONE", (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Draw center line
    cv2.line(frame, (width//2, 0), (width//2, height), (0, 255, 255), 1)
    
    frame_counter += 1
    
    # Detect every 2nd frame
    if frame_counter % 2 == 0:
        results = model(frame, conf=CONFIDENCE_THRESHOLD, imgsz=IMAGE_SIZE, verbose=False)
        last_results = results
    else:
        results = last_results if last_results else None
    
    # Process detections
    if results:
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].int().tolist()
            confidence = box.conf[0].item()
            label = model.names[int(box.cls[0])]
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            if center_y < zone_height:
                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label}: {confidence:.2f}", (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Send to motor controller
                if arduino and frame_counter % 10 == 0:  # Send every 10 frames
                    command = f"MOVE,{center_x},{center_y}\n"
                    arduino.write(command.encode())
                    print(f"→ Basket moving to X:{center_x}")
    
    # FPS
    fps_count += 1
    if time.time() - fps_time >= 1.0:
        fps_display = fps_count
        print(f"FPS: {fps_display}")
        fps_count = 0
        fps_time = time.time()
    
    # Display info
    cv2.putText(frame, f"FPS: {fps_display}", (10, height - 80),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    motor_status = "CONNECTED" if arduino else "DISCONNECTED"
    motor_color = (0, 255, 0) if arduino else (0, 0, 255)
    cv2.putText(frame, f"Motors: {motor_status}", (10, height - 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, motor_color, 2)
    
    cv2.putText(frame, "COMPLETE SYSTEM", (10, height - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    cv2.imshow("Garbage Detection System", frame)
    
    # Keyboard controls
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
    elif key == ord('s'):
        filename = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        print(f"📸 Saved: {filename}")
    elif key == ord(' '):
        if arduino:
            arduino.write(b"STOP\n")
            print("⏹️ Motors stopped manually")

# Cleanup
vs.stop()
if arduino:
    arduino.write(b"STOP\n")
    arduino.close()
cv2.destroyAllWindows()
print("\n✅ System stopped")