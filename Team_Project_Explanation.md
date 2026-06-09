# 📖 Smart Garbage Basket — Complete Project Documentation
### A Comprehensive Guide for Every Team Member

---

> **Who is this document for?**  
> This document is for every member of the team, even if you only worked on one part of the project. By the end of reading this, you will understand the **entire system end-to-end** — from how we collected data, to how the AI detects garbage, to how the microcontroller physically drives the motors.

---

## Table of Contents
1. [Project Overview — The "What and Why"](#1-project-overview)
2. [System Architecture — The Big Picture](#2-system-architecture)
3. [Phase 1: Dataset Collection Using ESP32-CAM](#3-phase-1-dataset-collection)
4. [Phase 2: Data Annotation with Roboflow](#4-phase-2-annotation-with-roboflow)
5. [Phase 3: AI Model Training (YOLOv5s)](#5-phase-3-ai-model-training)
6. [Phase 4: The Real-Time Detection Script (test1.py)](#6-phase-4-real-time-detection)
7. [Phase 5: The Quadrant-Based Motor Command Logic](#7-phase-5-quadrant-motor-logic)
8. [Phase 6: Wireless Communication (UDP Networking)](#8-phase-6-wireless-communication)
9. [Phase 7: The ESP32 WROOM Firmware (Hardware)](#9-phase-7-esp32-wroom-firmware)
10. [Phase 8: Motors, L298N Driver, and PWM](#10-phase-8-motors-and-l298n)
11. [Phase 9: Safety — IR Obstacle Sensors](#11-phase-9-ir-sensors)
12. [Phase 10: Voice Feedback System (voice.py)](#12-phase-10-voice-feedback)
13. [Phase 11: The Live Dashboard (dashboard.py)](#13-phase-11-live-dashboard)
14. [Complete Components List](#14-complete-components-list)
15. [Training Results & Performance Metrics](#15-training-results-and-metrics)
16. [Challenges We Faced and How We Solved Them](#16-challenges-and-solutions)
17. [Presentation Cheat Sheet](#17-presentation-cheat-sheet)

---

## 1. Project Overview

### The Problem
In lecture theatres, students throw paper balls and plastic bottles toward the bin but often miss. The result is litter on the floor. A **fixed bin** cannot react to the incoming trajectory of a thrown object.

### Our Solution
We built a **motorized, AI-powered garbage basket** that autonomously repositions itself underneath a falling piece of trash to catch it. The basket uses:
- A **camera** to see the garbage
- An **AI model** running on a laptop to recognize and locate the garbage
- **Wireless networking** to send movement commands
- A **microcontroller** with motors to physically drive under the trash

### Why It Is Impressive
This system works entirely **offline** (no internet after training), responds in under **100 milliseconds**, and achieves **82.1% detection accuracy** on custom-built garbage data.

---

## 2. System Architecture

Here is the **complete data flow** of the entire system, from the moment you throw a piece of trash to the moment the basket moves:

```
[You throw trash]
       ↓
[ESP32-CAM captures MJPEG video stream at 192.168.4.1:81/stream]
       ↓
[Laptop connects to Wi-Fi → OpenCV reads frames in a background thread]
       ↓
[YOLOv5s AI Model runs on every other frame → finds bounding box]
       ↓
[Python calculates: where is the trash center vs. camera center?]
       ↓
[Quadrant logic converts pixel displacement → movement command string]
       (e.g., "FORWARD_FAST", "LEFT", "STOP")
       ↓
[UDP Socket sends command packet → 192.168.4.2:1234 (< 5ms delivery)]
       ↓
[ESP32 WROOM firmware receives the string over UDP]
       ↓
[ESP32 sets GPIO pins HIGH/LOW → sends signals to L298N Motor Driver]
       ↓
[L298N opens high-current path from 12V battery → DC Motors spin]
       ↓
[Basket drives toward garbage using differential steering]
       ↓
[IR sensors stop the basket if it hits a wall]
       ↓
[Dashboard on localhost shows live FPS, detection label, command]
       ↓
[Voice assistant announces: "Plastic bottle detected, 87% confidence"]
```

---

## 3. Phase 1: Dataset Collection

### Why We Couldn't Use Google Images
A key decision we made early on: **do not use random images from the internet.** Why? Because our AI model needs to recognize garbage as it looks through the **ESP32-CAM specifically** — which has its own lens distortion, color rendition, and resolution (320×240 pixels at JPEG quality). A model trained on high-res, perfectly-lit images from Google would perform poorly through our cheap camera module.

### How We Collected Images
We wrote a simple Python script that accessed the ESP32-CAM's `/capture` endpoint:
```python
import requests
url = "http://192.168.4.1/capture"
for i in range(400):
    response = requests.get(url)
    with open(f"images/img_{i}.jpg", "wb") as f:
        f.write(response.content)
```

This script kept downloading snapshots one after another as we moved the objects around in front of the camera.

### What We Photographed
We captured **300–400 images** per class under varying conditions:

| Condition | Details |
|-----------|---------|
| Object Types | Full plastic bottle, crushed/dented bottle, small paper ball, large paper ball |
| Viewing Angles | Top-down (camera looking down from basket frame), isometric, side-on |
| Lighting | Bright classroom fluorescent, dim lighting, direct sunlight from window |
| Backgrounds | Floor tiles, desk surface, near the basket rim, mixed cluttered backgrounds |

This diversity is what makes the model **robust** — it won't get confused just because the lighting is slightly different on the day of the demo.

---

## 4. Phase 2: Annotation with Roboflow

### What is Annotation?
The AI doesn't automatically know what it's looking at in the images. We have to **manually tell it** where the garbage is. This process is called **annotation** or **labelling**.

### How We Did It
1. We uploaded all our images to **[Roboflow](https://roboflow.com)** — a free online platform for managing computer vision datasets.
2. For each image, we drew a **bounding box** (a rectangle) around every object and typed the class name (`bottle` or `paper`).
3. Roboflow stored these annotations in a structured format.

### Dataset Splitting
After annotation, Roboflow automatically split the dataset:
- **70%** → Training set (the AI learns from these)
- **15%** → Validation set (the AI checks its progress during training)
- **15%** → Test set (completely unseen images to evaluate final performance)

We enabled **stratified splitting** — this ensures each class (bottle AND paper) is proportionally represented in every split. Without this, you might accidentally have all your paper images only in the training set and nothing to validate against.

### Augmentations Applied in Roboflow
To increase the effective size of our dataset without taking more pictures, Roboflow applied **augmentations** — artificial transformations that create variations of existing images:

| Augmentation | Effect |
|---|---|
| Horizontal Flip | Creates a mirrored version of each image |
| Random Rotation (±15°) | Simulates objects at different tilt angles |
| Brightness Adjustment | Simulates different lighting conditions |
| Mosaic | Combines 4 images into one, exposing the model to multiple objects at once |

### Exporting the Dataset
We exported the final dataset in **YOLOv5 format**, which produces:
- A folder of `.jpg` image files
- A folder of `.txt` label files (one per image, each line = `class_id cx cy width height` all normalized 0–1)
- A `data.yaml` configuration file pointing to the image folders and listing class names

---

## 5. Phase 3: AI Model Training

### What is YOLO?
**YOLO** stands for "You Only Look Once." It is the most famous object detection algorithm in the world because of its incredible speed. Unlike older algorithms that had to scan an image multiple times at different scales, YOLO runs the image through a neural network **once** and predicts all bounding boxes and class labels simultaneously.

### Why YOLOv5s (Small)?
We specifically chose **YOLOv5s** (the "small" variant) because:
- Our laptop doesn't have a dedicated GPU, so we need a lightweight model
- It runs at 15–25 FPS on a regular laptop CPU (good enough for real-time)
- It's pre-trained on COCO (a massive dataset of 80 common object classes), so we don't start from zero — we just *fine-tune* it on our garbage data

### The YOLOv5 Architecture (What's Inside the Model)

| Component | What It Does |
|---|---|
| **Backbone: CSPDarknet** | Scans the input image and extracts feature maps — patterns like edges, textures, and shapes |
| **Neck: PANet (Path Aggregation Network)** | Fuses features detected at different scales so the model can find both small and large objects |
| **Head: Detection Layer** | Takes the fused features and predicts: where is the bounding box? What class is it? How confident are we? |

### The Training Script (`train_yolo.py`)
Here is the exact training script we used:

```python
from ultralytics import YOLO

DATASET_PATH = "Garbage-Detection-1/data.yaml"  # Our Roboflow export
MODEL_SIZE   = "yolov5nu.pt"                     # Pre-trained small model
EPOCHS       = 100                               # 100 full cycles through all training images
IMAGE_SIZE   = 320                               # Match ESP32-CAM resolution exactly
BATCH_SIZE   = 8                                 # How many images to process at once

model = YOLO(MODEL_SIZE)

results = model.train(
    data=DATASET_PATH,
    epochs=EPOCHS,
    imgsz=IMAGE_SIZE,
    batch=BATCH_SIZE,
    patience=20,          # Stop early if no improvement for 20 epochs
    save=True,            # Save checkpoints
    device='cpu',         # No GPU needed
    workers=4,            # Use 4 CPU cores
    project='runs/train',
    name='garbage_model'
)
```

### What Happens During Training?
In each epoch (one complete pass through all training images), the model:
1. **Looks** at a batch of 8 training images
2. **Predicts** bounding boxes and labels for them
3. **Compares** its predictions to the human-drawn ground truth boxes
4. **Calculates three loss values:**
   - **Box Loss**: How far off is the predicted box from the real box?
   - **Class Loss**: Did it guess the right class (bottle vs. paper)?
   - **Objectness Loss**: Was it confident enough that an object exists?
5. **Backpropagates** — adjusts millions of internal weights slightly in the direction that reduces these losses
6. Repeats for all 100 epochs until the losses converge (stop decreasing)

### Best Weights Saved
The checkpoint with the **highest validation mAP@50** across all 100 epochs is automatically saved as:
`runs/detect/runs/train/garbage_model-4/weights/best.pt`

This `best.pt` file is the trained brain of the robot.

---

## 6. Phase 4: Real-Time Detection (test1.py)

This is the **most important file** in the entire project. When you run `test1.py`, it:
1. Connects to the ESP32-CAM's video stream
2. Runs YOLOv5 inference on live frames
3. Sends movement commands to the ESP32 WROOM over UDP
4. Announces detections via the voice assistant
5. Broadcasts metadata to the dashboard

### Multi-Threaded Video Capture
The biggest technical challenge in real-time detection is **latency**. OpenCV's default `VideoCapture.read()` waits for a new frame to arrive from the network before returning — this causes a 2–3 second delay because it queues up frames.

Our solution: **run the frame reading in a completely separate background thread.**

```python
class VideoStream:
    def __init__(self, src):
        self.stream  = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Keep buffer tiny
        self.frame   = None
        self.stopped = False
        # Start reading in background daemon thread
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        # This runs forever in the background
        while not self.stopped:
            if self.stream.isOpened():
                (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        # Main loop gets the latest frame instantly — no waiting!
        return self.grabbed, self.frame
```

The background thread always fetches the newest frame and stores it in `self.frame`. The main detection loop grabs this variable directly without waiting for the network. This eliminates the queuing latency entirely.

### Frame Skipping for Performance
Running inference on **every single frame** would be too slow. We use a simple trick — only run the AI model on every **2nd frame**, and reuse the previous result for the skipped frame:

```python
frame_counter += 1

if frame_counter % 2 == 0:
    results = model(frame.copy(), conf=0.75, imgsz=320, verbose=False)
    last_results = results
else:
    results = last_results  # Reuse previous detection — no AI call
```

This doubles effective FPS without meaningfully reducing tracking accuracy since garbage doesn't teleport between frames.

### Key Configuration Values

```python
MODEL_PATH  = "runs/detect/runs/train/garbage_model-4/weights/best.pt"
STREAM_URL  = "http://192.168.4.1:81/stream"   # ESP32-CAM MJPEG stream
CONFIDENCE  = 0.75      # Only detect if ≥ 75% confident
IMAGE_SIZE  = 320       # Match camera resolution

WROOM_IP    = "192.168.4.2"   # ESP32 WROOM static IP on the AP network
WROOM_PORT  = 1234             # UDP port it listens on

FRAME_W = 320           # Camera frame width
FRAME_H = 240           # Camera frame height
CENTER_X = 160          # Horizontal center of frame
CENTER_Y = 120          # Vertical center of frame
```

---

## 7. Phase 5: Quadrant-Based Motor Command Logic

Once an object is detected, the code calculates the **displacement** of the garbage from the center of the camera:

```python
center_x = (x1 + x2) // 2     # Horizontal center of bounding box
center_y = (y1 + y2) // 2     # Vertical center of bounding box

mx = center_x - CENTER_X      # Horizontal displacement from screen center
my = CENTER_Y - center_y      # Vertical displacement (positive = above center)
```

### The Dead Zone
A **60-pixel dead zone** is defined around the screen center. If the garbage is within this box, the basket is already perfectly positioned — it sends `STOP` and doesn't waste energy twitching around.

```python
DEAD_ZONE_X = 60
DEAD_ZONE_Y = 60

if abs(mx) < DEAD_ZONE_X and abs(my) < DEAD_ZONE_Y:
    return "STOP"
```

### Speed Zones
Beyond the dead zone, the system has **soft** and **hard** zones so the basket moves slowly when the object is nearby and fast when it needs to cover large distances:

| Zone | Threshold | Command Example |
|---|---|---|
| Dead Zone | `abs(dx) < 60` | `STOP` |
| Soft Zone | `60 < abs(dx) < 120` | `FORWARD_SLOW` |
| Medium Zone | `120 < abs(dx) < 180` | `FORWARD` |
| Hard Zone | `abs(dx) > 180` | `FORWARD_FAST` |

### Complete Command Table

| Position of Garbage | Command Sent | Basket Behaviour |
|---|---|---|
| Perfectly centered | `STOP` | Stays still |
| Above center, nearly centered | `FORWARD_SLOW` | Creeps forward slowly |
| Far above center | `FORWARD_FAST` | Drives forward quickly |
| Below center | `BACKWARD` / `BACKWARD_FAST` | Reverses |
| Right of center | `RIGHT` / `RIGHT_FAST` | Turns right |
| Left of center | `LEFT` / `LEFT_FAST` | Turns left |

### Command Throttling
To prevent flooding the ESP32 with thousands of identical commands per second, the code only sends a new command if:
- The command is **different** from the last one, OR
- **200ms** has passed since the last send

```python
CMD_INTERVAL = 0.20  # seconds

def send_command(cmd):
    now = time.time()
    if cmd != last_cmd or now - last_cmd_time > CMD_INTERVAL:
        udp_socket.sendto(cmd.encode(), (WROOM_IP, WROOM_PORT))
```

---

## 8. Phase 6: Wireless Communication (UDP Networking)

### Why Wi-Fi Instead of a Wire?
Originally the system used a **USB serial cable** between the laptop and ESP32 WROOM. The problem: a cable tethers the basket and limits its movement range. Wi-Fi gives it full freedom to move anywhere within the room.

### Why UDP Instead of TCP?
The internet normally uses **TCP (Transmission Control Protocol)**, which guarantees delivery by making the sender wait for the receiver to say "got it!" before sending the next packet. This is great for email or file downloads but creates **unacceptable latency for a real-time control system**.

**UDP (User Datagram Protocol)** is the opposite: it fires packets into the network and doesn't wait for any acknowledgment. This makes it:
- Much faster (5–10ms delivery vs 50–200ms for TCP)
- Slightly less reliable (but a dropped motor command just means the basket pauses for one cycle — acceptable)

```python
# Create a connectionless UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Send a command — no connection needed, just blast it out
udp_socket.sendto("FORWARD_FAST".encode('utf-8'), ("192.168.4.2", 1234))
```

### The Wi-Fi Network Setup
The ESP32-CAM acts as a **Wi-Fi Access Point (AP)** — essentially a private mobile hotspot. Its SSID is `ESP32-GARBAGE`.

| Device | Role | IP Address |
|---|---|---|
| ESP32-CAM | Access Point (hotspot host) + camera | 192.168.4.1 |
| Laptop | Wi-Fi client (connects to AP) | 192.168.4.100 (auto-assigned) |
| ESP32 WROOM | Wi-Fi client (connects to same AP) | 192.168.4.2 (static, set in firmware) |

### The Dashboard IPC (Internal Communication)
The `test1.py` script also sends data to the **live dashboard** running locally. It uses a second UDP socket on `127.0.0.1:5555` (localhost) to send a JSON packet every frame:

```python
meta = {
    "fps": fps_display,      # Current frames per second
    "cmd": cmd,              # e.g. "LEFT_FAST"
    "conf": best_conf,       # e.g. 0.87
    "label": label           # e.g. "plastic bottle"
}
ipc_socket.sendto(json.dumps(meta).encode(), ('127.0.0.1', 5555))
```

The dashboard reads these packets and updates its gauges in real-time.

---

## 9. Phase 7: ESP32 WROOM Firmware (The Hardware Brain)

### What is the ESP32 WROOM?
The **ESP32 WROOM** is a small development board containing a **dual-core Xtensa LX6 processor** running at 240 MHz with 520 KB SRAM and built-in 802.11b/g/n Wi-Fi. This is the microcontroller that directly controls the motors.

### What the Firmware Does
1. **Connects** to the ESP32-CAM's Wi-Fi access point (`ESP32-GARBAGE`)
2. **Opens a UDP listener** on port 1234
3. **Waits** in a loop for packets to arrive
4. **Parses** the text command from the packet
5. **Updates GPIO pins** to drive the L298N motor driver

### Key Firmware Functions
Each movement command maps to a specific motor activation pattern:

```cpp
void doForwardFast() {
    // Left motor forward FULL speed
    digitalWrite(L_IN1, HIGH);  // L298N IN1 = HIGH
    digitalWrite(L_IN2, LOW);   // L298N IN2 = LOW
    analogWrite(L_EN, 255);     // Full speed PWM

    // Right motor forward FULL speed
    digitalWrite(R_IN1, HIGH);
    digitalWrite(R_IN2, LOW);
    analogWrite(R_EN, 255);
}

void doLeft() {
    // Left motor BACKWARD (slow) — creates left turn
    digitalWrite(L_IN1, LOW);
    digitalWrite(L_IN2, HIGH);
    analogWrite(L_EN, SPEED_TURN);

    // Right motor FORWARD (fast)
    digitalWrite(R_IN1, HIGH);
    digitalWrite(R_IN2, LOW);
    analogWrite(R_EN, SPEED_FULL);
}

void doStop() {
    analogWrite(L_EN, 0);  // Cut power to both motors
    analogWrite(R_EN, 0);
}
```

### GPIO Pin Assignments

| ESP32 GPIO Pin | Connected To | Purpose |
|---|---|---|
| GPIO 14 | L298N ENA | Left motor speed (PWM) |
| GPIO 27 | L298N IN1 | Left motor direction |
| GPIO 26 | L298N IN2 | Left motor direction |
| GPIO 32 | L298N ENB | Right motor speed (PWM) |
| GPIO 33 | L298N IN3 | Right motor direction |
| GPIO 25 | L298N IN4 | Right motor direction |
| GPIO 34 | Front IR Sensor OUT | Obstacle detection (front) |
| GPIO 35 | Back IR Sensor OUT | Obstacle detection (back) |

---

## 10. Phase 8: Motors, the L298N Driver, and PWM

### Why Can't We Connect Motors Directly to the ESP32?
The ESP32 outputs **3.3V signals** and can supply only ~40mA of current from any GPIO pin. A DC motor requires **12V** and draws **hundreds of milliamps** when under load. Connecting a motor directly to a GPIO pin would instantly burn out the ESP32.

The **L298N Motor Driver** is the solution. It is a **high-current H-bridge circuit** that:
- Takes the tiny, low-power control signals from the ESP32
- Uses those signals to switch high-current paths from the 12V battery to the motors

Think of it like the ESP32 flipping a light switch (3.3V, tiny current), and the L298N being the light switch that controls a massive industrial power line (12V, high current).

### The H-Bridge Explained
An H-bridge allows **current to flow in either direction** through a motor, which is what makes it spin both forward AND backward. It has 4 switches arranged in an "H" shape around the motor:

```
Battery +12V ──── [Switch A]──────[Switch B] ───── GND
                       |    MOTOR    |
Battery +12V ──── [Switch C]──────[Switch D] ───── GND
```
- Switches A + D closed → current flows LEFT → motor spins FORWARD
- Switches B + C closed → current flows RIGHT → motor spins BACKWARD
- All switches open → motor stops

The L298N handles all this automatically from the `IN1/IN2/IN3/IN4` signals from the ESP32.

### PWM (Pulse Width Modulation) — Speed Control
`analogWrite(L_EN, 255)` doesn't actually output 255 volts. It generates a **square wave signal** that rapidly switches between 3.3V and 0V. The key parameter is **duty cycle** — what percentage of each cycle is the signal HIGH:

- `analogWrite(L_EN, 255)` → 100% duty cycle → full speed
- `analogWrite(L_EN, 128)` → 50% duty cycle → half speed  
- `analogWrite(L_EN, 64)`  → 25% duty cycle → quarter speed
- `analogWrite(L_EN, 0)`   → 0% duty cycle → motor stops

This is how we achieve `FORWARD_SLOW`, `FORWARD`, and `FORWARD_FAST` without needing different power supplies — just different PWM duty cycles.

### Differential Steering (How the Basket Turns)
The basket has no steering wheel or axle. Instead, it uses **differential steering** — the same system used by tanks. To turn LEFT:
- Left motor spins **slower** (lower PWM duty cycle)
- Right motor spins **faster** (higher PWM duty cycle)
- The right side pushes harder → basket curves left

To turn RIGHT, the opposite happens. This is how the basket achieves all 9 movement directions using only 2 DC motors.

---

## 11. Phase 9: Safety — IR Obstacle Sensors

### What Are IR Sensors?
An **Infrared (IR) obstacle sensor** consists of an IR LED that emits invisible infrared light and a photodetector that checks if that light bounces back from a nearby surface. If an obstacle (like a wall) is within ~20cm, the sensor outputs a LOW signal.

### Why Are They Important?
Without IR sensors, the basket could:
- Drive into a wall while tracking a piece of garbage near the edge
- Get stuck in a corner with motors running continuously, draining the battery
- Potentially damage itself or the classroom furniture

### Hardware Interrupt Priority
The IR sensors are connected to **interrupt-capable GPIO pins** on the ESP32. This means they don't wait for the main `loop()` function to check them — they instantly **interrupt** whatever the processor is doing and execute a special `IRAM_ATTR` function immediately:

```cpp
void IRAM_ATTR frontObstacleISR() {
    // This runs IMMEDIATELY when front IR detects an obstacle
    // No waiting for the main loop
    doStop();
}

void setup() {
    // Attach interrupt to front IR sensor pin
    attachInterrupt(digitalPinToInterrupt(FRONT_IR_PIN), frontObstacleISR, FALLING);
}
```

The `IRAM_ATTR` attribute stores this function in fast IRAM (Instruction RAM) instead of slower flash memory, making it execute in just a few nanoseconds.

---

## 12. Phase 10: Voice Feedback System (voice.py)

### What It Does
Every time a piece of garbage is detected with ≥70% confidence, the system speaks a verbal announcement:
`"Plastic bottle detected, 87 percent confidence"`

This provides feedback to the user without needing to look at the screen.

### How It Works Without Blocking Detection
Voice synthesis (text-to-speech) takes ~1 second to generate and speak a sentence. If we called it directly in the detection loop, the entire system would freeze for 1 second — completely unacceptable for a real-time tracking system.

The solution: run the voice engine in a **completely separate background thread** with a **queue**:

```python
# voice.py simplified

import queue, threading, pyttsx3

_speech_queue = queue.Queue(maxsize=3)  # Max 3 queued announcements

def _worker():
    """This runs in a background thread forever"""
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)    # Speaking speed (words per minute)
    engine.setProperty("volume", 0.95)
    while True:
        text = _speech_queue.get()     # Wait for something to say
        if text is None: break         # Shutdown signal
        engine.say(text)
        engine.runAndWait()            # Actually speak — takes ~1 second
        # But the detection loop didn't wait! It kept running.

def speak(obj_class, confidence):
    # Only speak if:
    if confidence < 0.70: return            # Not confident enough
    if time.time() - _last_spoken < 3.0: return  # Too soon since last announcement
    
    text = f"{friendly_name} detected, {int(confidence*100)} percent confidence"
    _speech_queue.put_nowait(text)  # Queue it and return INSTANTLY
```

The detection loop calls `voice.speak()`, which returns in microseconds. The actual speaking happens in the background thread independently.

### Voice Toggle (User Control)
The dashboard has a toggle switch to enable/disable voice. When toggled, it writes `"1"` or `"0"` to a file called `voice_cfg.txt`. The `test1.py` detection script reads this file before each announcement:

```python
def is_voice_enabled():
    if os.path.exists("voice_cfg.txt"):
        with open("voice_cfg.txt", "r") as f:
            return f.read().strip() == "1"
    return True  # Default: enabled
```

---

## 13. Phase 11: The Live Dashboard (dashboard.py)

### What It Is
The dashboard is a **Streamlit web application** that runs locally in the browser and provides a beautiful real-time visualization of the detection system.

### What It Shows
| Section | Data Source | What It Displays |
|---|---|---|
| KPI Cards | IPC socket + SQLite | Total detections, plastic bottles, crushed papers, avg confidence |
| Movement Status | IPC socket | Current motor command (FORWARD, LEFT, etc.) live |
| Live Tracking Metrics | IPC socket | FPS, confidence, detection label |
| Charts | Plotly + IPC | Live FPS graph, confidence trend |

### How It Gets Live Data
The `test1.py` script broadcasts a JSON packet to `127.0.0.1:5555` every frame. The dashboard runs a background listener thread (using `@st.cache_resource`) that receives these packets:

```python
@st.cache_resource
def start_ipc_listeners():
    state = {"fps": 0, "cmd": "STOP", "conf": 0.0, "label": ""}
    
    def listen_meta():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 5555))
        while True:
            data, _ = sock.recvfrom(1024)
            update = json.loads(data.decode())
            state.update(update)   # Update shared state dict
    
    threading.Thread(target=listen_meta, daemon=True).start()
    return state
```

Streamlit reruns the page every second, reading the latest values from `state`.

### Database Persistence (SQLite)
Every detection session's totals are saved to a local **SQLite database** (`database.db`) when you click "Refresh" or close the session. This allows the dashboard to show **all-time statistics** across multiple sessions — not just the current run.

---

## 14. Complete Components List

### Hardware Components

| Component | Purpose | Specs |
|---|---|---|
| **ESP32 WROOM-32** | Motor control microcontroller | Dual-core 240MHz, Wi-Fi, 520KB SRAM |
| **ESP32-CAM (OV2640)** | Video capture & AP hosting | 2MP camera, MJPEG stream, Wi-Fi AP mode |
| **L298N Motor Driver** | Powers DC motors from high-voltage battery | 12V input, 2A per channel |
| **2× DC Geared Motors** | Drive the basket wheels | 6–12V, ~200RPM |
| **2× IR Obstacle Sensors** | Detect walls and obstacles | 3.3V–5V, ~20cm range |
| **12V Li-ion Battery Pack** | Power supply for motors and ESP32 | 12V, ~2000mAh |
| **Basket Frame / Chassis** | Physical housing | Custom-built |

### Software Components

| Software | Purpose |
|---|---|
| **Python 3.10+** | Main scripting language |
| **Ultralytics YOLO** | Loading and running the AI model |
| **OpenCV (cv2)** | Capturing and processing video frames |
| **PyTorch** | Backend framework that YOLOv5 runs on |
| **pyttsx3** | Offline text-to-speech voice engine |
| **Streamlit** | Dashboard web framework |
| **Plotly** | Charts and graphs in dashboard |
| **SQLite3** | Persistent database for session history |
| **socket (UDP)** | Wireless command transmission |
| **Roboflow** | Dataset annotation and management |

---

## 15. Training Results and Performance Metrics

### Validation Set Performance (After 100 Epochs)

| Metric | Value | What It Means |
|---|---|---|
| **mAP@50** | **82.1%** | Model correctly localizes AND classifies ~8 of every 10 detected objects |
| **Precision** | **77.8%** | ~3 in 4 positive detections are genuine garbage (not false alarms) |
| **Recall** | **85.8%** | Model catches 8.5 out of every 10 real trash items in view |
| **F1-Score** | **81.6%** | Balanced measure — good trade-off between precision and recall |

### Per-Class Performance (Unseen Test Set)

| Class | mAP@50 | Reason for Difference |
|---|---|---|
| **Crushed Paper** | **87.0%** | Distinctive crumpled texture and irregular shape — very easy for the model to distinguish |
| **Plastic Bottle** | **77.0%** | Smooth cylindrical shape can occasionally be confused with other round objects |
| **Overall** | **82.0%** | Strong generalization across both categories |

### Speed Performance

| Metric | Value |
|---|---|
| Inference FPS | 15–25 FPS on laptop CPU |
| Frame processing time | ~40–65 ms |
| UDP command delivery | 5–10 ms |
| End-to-end latency | **80–120 ms total** |

---

## 16. Challenges and Solutions

| Challenge | What Went Wrong | How We Fixed It |
|---|---|---|
| **High frame capture latency** | OpenCV was queuing frames, causing 2-3 second delay | Implemented a background daemon thread that constantly reads the latest frame, completely eliminating the queue |
| **Green-tinted corrupted images** | ESP32-CAM at QVGA resolution was producing malformed JPEG frames | Switched to HVGA (480×320) resolution with proper JPEG quality settings |
| **Motor not responding to commands** | Diagonal commands weren't working; motors ignored them | Tuned differential steering speeds for each command; reduced dead zone; added serial print debugging to verify the quadrant logic |
| **Serial "Access Denied" error** | Arduino IDE's Serial Monitor was keeping the COM port open | Closed Serial Monitor in Arduino IDE; switched from Serial to UDP entirely, eliminating the port conflict permanently |
| **Low recall for small paper balls** | Small paper balls at distance were missed | Lowered confidence threshold from 0.80 to 0.70 after analyzing the precision-recall curve on the validation set |
| **Model confused bottles with cylinders** | Bottles were sometimes confused with water cups | Collected additional training images of cluttered scenes and applied stronger augmentations |
| **Voice blocking detection loop** | `pyttsx3.runAndWait()` froze the main thread | Moved all TTS to a background daemon thread with a queue; detection loop now just puts text in the queue and continues instantly |

---

## 17. Presentation Cheat Sheet

Use this section right before you go up to present.

### If Someone Asks "How does the AI work?"
> "We used YOLOv5s, a single-stage object detector. We first captured 300–400 images using the ESP32-CAM itself so the model learns what garbage looks like through our specific camera. We annotated the images in Roboflow, split them 70/15/15, and trained locally on our laptop for 100 epochs. The result is a model that detects garbage with 82% accuracy at 20 frames per second."

### If Someone Asks "What is YOLO?"
> "YOLO stands for You Only Look Once. Unlike older methods that scan an image multiple times, YOLO passes the image through a neural network exactly once and predicts all bounding boxes and class labels in a single forward pass. This makes it extremely fast — critical for a basket that must react in milliseconds."

### If Someone Asks "How does the basket know where to move?"
> "Once the AI draws a bounding box around the garbage, we calculate the center pixel of that box and compare it to the exact center of the camera frame. The horizontal and vertical displacement tells us which way the basket needs to drive. We divide the frame into speed zones — if the garbage is far from center, we send FORWARD_FAST; if it's close, FORWARD_SLOW; if it's perfectly centered, STOP."

### If Someone Asks About the Hardware (COAL subject)
> "The ESP32 WROOM receives movement commands over a UDP Wi-Fi socket. It parses the command string, then writes HIGH/LOW signals to its GPIO pins connected to the L298N motor driver. The L298N is an H-bridge IC that uses those tiny 3.3V signals to switch high-current 12V paths from the battery into the DC motors. We use PWM — Pulse Width Modulation — to control motor speed. A 100% duty cycle gives full speed, 50% gives half speed. To turn, we spin one motor faster than the other — this is called differential steering. IR sensors are wired to hardware interrupt pins so the ESP32 instantly stops the motors the moment an obstacle is detected, without waiting for the main loop."

### If Someone Asks About the Communication
> "We use UDP sockets over Wi-Fi. The ESP32-CAM creates its own Wi-Fi hotspot. Our laptop and the ESP32 WROOM both connect to this network. The laptop sends movement commands as plain text strings like 'FORWARD_FAST' over UDP to the WROOM's IP address and port number. UDP is connectionless — no handshake, no waiting for acknowledgment — so delivery takes only 5 to 10 milliseconds, which is why the basket reacts almost instantly."

---

*Document created from full analysis of: `test1.py`, `train_yolo.py`, `voice.py`, `dashboard.py`, `Smart_Garbage_Basket_AI_Report.docx`, and all project hardware documentation.*
