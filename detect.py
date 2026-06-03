import cv2
import time
from inference_sdk import InferenceHTTPClient

# =====================================================
# ROBOFLOW CONFIGURATION
# =====================================================

API_URL = "https://serverless.roboflow.com"

# Paste your Roboflow API Key here
API_KEY = "********"

# Example:
# MODEL_ID = "object-detection-abc123/2"
MODEL_ID = "garbage-detection-n7huv/2"

# =====================================================
# ESP32-CAM STREAM URL
# =====================================================

# Example:
# STREAM_URL = "http://192.168.1.105:81/stream"

STREAM_URL = "http://10.126.108.112:81/stream"

# =====================================================
# INITIALIZE ROBOFLOW CLIENT
# =====================================================

CLIENT = InferenceHTTPClient(
    api_url=API_URL,
    api_key=API_KEY
)

# =====================================================
# CONNECT TO ESP32 STREAM
# =====================================================

cap = cv2.VideoCapture(STREAM_URL)

# Reduce stream buffering (less lag)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("ERROR: Could not connect to ESP32-CAM stream")
    exit()

print("ESP32-CAM Connected Successfully")

# =====================================================
# PERFORMANCE SETTINGS
# =====================================================

FRAME_SKIP = 3
CONFIDENCE_THRESHOLD = 0.40

frame_count = 0
prev_time = time.time()

# =====================================================
# MAIN LOOP
# =====================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Failed to read frame")
        break

    frame_count += 1

    # Skip frames for smoother performance
    if frame_count % FRAME_SKIP != 0:
        continue

    # Resize frame for faster inference
    frame = cv2.resize(frame, (640, 480))

    # Save temporary frame
    cv2.imwrite("temp.jpg", frame)

    try:

        # =====================================================
        # RUN ROBOFLOW INFERENCE
        # =====================================================

        result = CLIENT.infer(
            "temp.jpg",
            model_id=MODEL_ID
        )

        predictions = result["predictions"]

        # =====================================================
        # DRAW DETECTIONS
        # =====================================================

        for pred in predictions:

            confidence = pred["confidence"]

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            x = int(pred["x"])
            y = int(pred["y"])
            w = int(pred["width"])
            h = int(pred["height"])

            label = pred["class"]

            # Bounding box coordinates
            x1 = int(x - w / 2)
            y1 = int(y - h / 2)
            x2 = int(x + w / 2)
            y2 = int(y + h / 2)

            # Draw bounding box
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # Label text
            text = f"{label} {confidence:.2f}"

            # Draw label
            cv2.putText(
                frame,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # =====================================================
            # OBJECT ACTIONS
            # =====================================================

            if label == "Small_Bottle":
                print("ACTION: MOVE FORWARD")

            elif label == "Crushed_Paper":
                print("ACTION: STOP")

        # =====================================================
        # FPS CALCULATION
        # =====================================================

        current_time = time.time()

        fps = 1 / (current_time - prev_time)

        prev_time = current_time

        cv2.putText(
            frame,
            f"FPS: {int(fps)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        # =====================================================
        # DISPLAY OUTPUT
        # =====================================================

        cv2.imshow("ESP32 AI Detection", frame)

    except Exception as e:
        print("Inference Error:", e)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# =====================================================
# CLEANUP
# =====================================================

cap.release()
cv2.destroyAllWindows()