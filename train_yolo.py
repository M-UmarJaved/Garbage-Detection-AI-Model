from ultralytics import YOLO
import os

# =====================================================
# TRAINING CONFIGURATION
# =====================================================

# Path to your downloaded dataset
# After download, you'll get a folder like:
# "garbage-detection-n7huv-2/"
DATASET_PATH = "Garbage-Detection-1/data.yaml"

# Model size - use "yolov5n" (nano) for speed
# Options: yolov5n, yolov5s, yolov5m, yolov5l
MODEL_SIZE = "yolov5nu.pt"  # Nano = fastest, perfect for your project

# Training parameters
EPOCHS = 100              # Number of training cycles
IMAGE_SIZE = 320          # Match your ESP32 camera resolution
BATCH_SIZE = 8           # Adjust based on your RAM (8, 16, or 32)

# =====================================================
# START TRAINING
# =====================================================

print("="*60)
print("🚀 Starting YOLOv5 Training")
print("="*60)
print(f"Dataset: {DATASET_PATH}")
print(f"Model: {MODEL_SIZE}")
print(f"Epochs: {EPOCHS}")
print(f"Image size: {IMAGE_SIZE}")
print("="*60)

# Load pretrained model
model = YOLO(MODEL_SIZE)

# Train the model
results = model.train(
    data=DATASET_PATH,
    epochs=EPOCHS,
    imgsz=IMAGE_SIZE,
    batch=BATCH_SIZE,
    patience=20,           # Stop early if no improvement
    save=True,             # Save checkpoints
    device='cpu',          # Use 'cuda' if you have GPU
    workers=4,             # CPU cores to use
    project='runs/train',  # Save location
    name='garbage_model'   # Model name
)

print("\n" + "="*60)
print("✅ Training Complete!")
print("="*60)
print(f"Best model saved at: runs/train/garbage_model/weights/best.pt")
print(f"Training results: runs/train/garbage_model/")
print("="*60)