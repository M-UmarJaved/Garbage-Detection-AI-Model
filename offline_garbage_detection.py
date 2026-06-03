import cv2
from ultralytics import YOLO
import time

# =====================================================
# CONFIGURATION
# =====================================================

# Your trained model (NO INTERNET NEEDED!)
MODEL_PATH = "runs/detect/runs/train/garbage_model-4/weights/best.pt"

# ESP32-CAM Stream (AP Mode)
STREAM_URL = "http://192.168.4.1:81/stream"

# Detection settings
CONFIDENCE_THRESHOLD = 0.7
IMAGE_SIZE = 320

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading trained model...")
model = YOLO(MODEL_PATH)
print("✅ Model loaded successfully - OFFLINE MODE!")
print(f"Classes: {model.names}")

# =====================================================
# CONNECT TO ESP32
# =====================================================

cap = cv2.VideoCapture(STREAM_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("ERROR: Cannot connect to ESP32-CAM")
    print("\nTroubleshooting:")
    print("1. Is ESP32 powered on?")
    print("2. Is laptop connected to 'ESP32-GARBAGE' WiFi?")
    print("3. Can you open http://192.168.4.1 in browser?")
    exit()

print("✅ ESP32-CAM Connected")

# =====================================================
# PERFORMANCE TRACKING
# =====================================================

fps_time = time.time()
fps_count = 0
fps_display = 0

detection_count = {name: 0 for name in model.names.values()}

print("\n" + "="*60)
print("🚀 OFFLINE GARBAGE DETECTION SYSTEM")
print("="*60)
print("Features:")
print("  ✓ NO Internet Required")
print("  ✓ Real-time Detection")
print("  ✓ Fast Processing (15-25 FPS expected)")
print("  ✓ Your Custom Trained Model")
print("="*60)
print("\nPress 'Q' to quit")
print("Press 'S' to save screenshot")
print("="*60 + "\n")

# =====================================================
# MAIN DETECTION LOOP
# =====================================================

while True:
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("⚠️ Frame read failed, retrying...")
        continue
    
    # Get frame dimensions
    height, width = frame.shape[:2]
    
    # Draw detection zone (top 60% of frame - where objects will appear)
    zone_height = int(height * 0.6)
    cv2.rectangle(frame, (0, 0), (width, zone_height), (255, 0, 0), 2)
    cv2.putText(frame, "DETECTION ZONE", (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # =====================================================
    # RUN DETECTION (OFFLINE!)
    # =====================================================
    
    results = model(
        frame,
        conf=CONFIDENCE_THRESHOLD,
        imgsz=IMAGE_SIZE,
        verbose=False  # Don't print to console each frame
    )
    
    # =====================================================
    # PROCESS DETECTIONS
    # =====================================================
    
    detected_objects = []
    
    for box in results[0].boxes:
        # Extract box coordinates
        x1, y1, x2, y2 = box.xyxy[0].int().tolist()
        
        # Get confidence and class
        confidence = box.conf[0].item()
        class_id = int(box.cls[0])
        label = model.names[class_id]
        
        # Calculate center point
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Only process if in detection zone
        if center_y < zone_height:
            
            detected_objects.append({
                'label': label,
                'confidence': confidence,
                'center_x': center_x,
                'center_y': center_y,
                'box': (x1, y1, x2, y2)
            })
            
            # Update detection count
            detection_count[label] += 1
            
            # Draw bounding box (green)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw center point (red)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # Draw label with confidence
            text = f"{label}: {confidence:.2f}"
            
            # Background for text (better visibility)
            (text_width, text_height), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                frame,
                (x1, y1 - text_height - 10),
                (x1 + text_width, y1),
                (0, 255, 0),
                -1
            )
            
            # Draw text
            cv2.putText(
                frame, text, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
            )
            
            # Print to console
            print(f"✓ {label} detected at X:{center_x} Y:{center_y} conf:{confidence:.2f}")
            
            # =====================================================
            # MOTOR CONTROL LOGIC (Add your motor code here)
            # =====================================================
            
            if label == "Small_Bottle":
                print(f"  → MOVING basket to X:{center_x}")
                # TODO: Send command to ESP32 WROOM
                # arduino.write(f"MOVE,{center_x},{center_y}\n".encode())
            
            elif label == "Crushed_Paper":
                print(f"  → MOVING basket to X:{center_x}")
                # TODO: Send command to ESP32 WROOM
    
    # =====================================================
    # FPS CALCULATION
    # =====================================================
    
    fps_count += 1
    current_time = time.time()
    
    if current_time - fps_time >= 1.0:
        fps_display = fps_count
        print(f"\n📊 FPS: {fps_display}")
        if detected_objects:
            print(f"📦 Objects in frame: {len(detected_objects)}")
        print()
        fps_count = 0
        fps_time = current_time
    
    # =====================================================
    # DISPLAY INFO ON FRAME
    # =====================================================
    
    # FPS
    cv2.putText(frame, f"FPS: {fps_display}", (10, height - 80),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Offline indicator
    cv2.putText(frame, "OFFLINE MODE", (10, height - 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    # Detection count
    cv2.putText(frame, f"Detected: {len(detected_objects)}", (10, height - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Model confidence threshold
    cv2.putText(frame, f"Confidence: {CONFIDENCE_THRESHOLD}", (width - 200, height - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # =====================================================
    # DISPLAY FRAME
    # =====================================================
    
    cv2.imshow("Offline Garbage Detection - YOLOv5", frame)
    
    # =====================================================
    # KEYBOARD CONTROLS
    # =====================================================
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        # Quit
        break
    
    elif key == ord('s'):
        # Save screenshot
        filename = f"detection_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        print(f"📸 Screenshot saved: {filename}")

# =====================================================
# CLEANUP AND SUMMARY
# =====================================================

cap.release()
cv2.destroyAllWindows()

print("\n" + "="*60)
print("✅ Detection Stopped")
print("="*60)
print("Detection Summary:")
for label, count in detection_count.items():
    if count > 0:
        print(f"  {label}: {count} detections")
print("="*60)