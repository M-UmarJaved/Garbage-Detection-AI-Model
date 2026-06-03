"""
voice.py  —  Offline Voice Feedback
=====================================
Uses pyttsx3 (no internet required).
Runs in a background daemon thread so it NEVER blocks the detection loop.

Usage
-----
  import voice
  voice.init()            # call once at startup
  voice.speak("Small_Bottle", 0.95)
  voice.shutdown()        # call at exit
"""

import threading
import queue
import time

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MIN_SPEAK_INTERVAL = 3.0      # seconds between announcements
CONFIDENCE_SPEAK_THRESHOLD = 0.70   # only speak above this confidence
VOICE_RATE  = 175             # words per minute
VOICE_VOLUME = 0.95           # 0.0 – 1.0

# ─────────────────────────────────────────────
# FRIENDLY NAMES
# ─────────────────────────────────────────────
_FRIENDLY = {
    "Small_Bottle":  "plastic bottle",
    "Crushed_Paper": "crushed paper",
    "bottle":        "plastic bottle",
    "paper":         "paper",
}

# ─────────────────────────────────────────────
# MODULE STATE
# ─────────────────────────────────────────────
_speech_queue: queue.Queue   = queue.Queue(maxsize=3)
_worker_thread: threading.Thread | None = None
_last_spoken: float          = 0.0
_engine                      = None
_ready: bool                 = False


# ─────────────────────────────────────────────
# BACKGROUND WORKER
# ─────────────────────────────────────────────
def _worker() -> None:
    """Background thread that drives pyttsx3 serially."""
    global _engine
    try:
        import pyttsx3
        _engine = pyttsx3.init()
        _engine.setProperty("rate",   VOICE_RATE)
        _engine.setProperty("volume", VOICE_VOLUME)

        # prefer a female voice if available
        voices = _engine.getProperty("voices")
        for v in voices:
            if "zira" in v.name.lower() or "female" in v.name.lower():
                _engine.setProperty("voice", v.id)
                break

        print("[Voice] OK pyttsx3 engine initialised")

        while True:
            text = _speech_queue.get()
            if text is None:          # sentinel → shutdown
                break
            try:
                _engine.say(text)
                _engine.runAndWait()
            except Exception as ex:
                print(f"[Voice] WARN speak error: {ex}")
            _speech_queue.task_done()

    except ImportError:
        print("[Voice] WARN pyttsx3 not installed — voice disabled. Run: pip install pyttsx3")
    except Exception as e:
        print(f"[Voice] WARN init error: {e}")


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────
def init() -> None:
    """Start the background TTS worker thread."""
    global _worker_thread, _ready
    _worker_thread = threading.Thread(target=_worker, daemon=True, name="VoiceWorker")
    _worker_thread.start()
    time.sleep(0.3)   # give pyttsx3 a moment to init
    _ready = True
    print("[Voice] Background voice worker started")


def speak(obj_class: str, confidence: float, extra: str = "") -> None:
    """
    Queue a speech announcement if conditions are met.

    Args:
        obj_class  : YOLO class name e.g. "Small_Bottle"
        confidence : detection confidence 0.0 – 1.0
        extra      : optional extra phrase e.g. "bin almost full"
    """
    global _last_spoken
    if not _ready:
        return
    if confidence < CONFIDENCE_SPEAK_THRESHOLD:
        return
    if time.time() - _last_spoken < MIN_SPEAK_INTERVAL:
        return

    friendly  = _FRIENDLY.get(obj_class, obj_class.replace("_", " "))
    conf_pct  = int(confidence * 100)
    text      = f"{friendly} detected, {conf_pct} percent confidence"
    if extra:
        text += f". {extra}"

    _last_spoken = time.time()

    try:
        _speech_queue.put_nowait(text)
        print(f"[Voice] Speaking: '{text}'")
    except queue.Full:
        pass   # drop if queue is full — never block detection


def speak_alert(message: str) -> None:
    """Speak an arbitrary alert message (e.g. 'Bin almost full')."""
    global _last_spoken
    if not _ready:
        return
    if time.time() - _last_spoken < MIN_SPEAK_INTERVAL:
        return
    _last_spoken = time.time()
    try:
        _speech_queue.put_nowait(message)
        print(f"[Voice] Alert: '{message}'")
    except queue.Full:
        pass


def shutdown() -> None:
    """Cleanly stop the TTS worker thread."""
    if _worker_thread and _worker_thread.is_alive():
        try:
            _speech_queue.put_nowait(None)   # sentinel
        except queue.Full:
            pass
    print("[Voice] Voice worker shut down")


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init()
    time.sleep(1)
    speak("Small_Bottle", 0.95)
    speak("Crushed_Paper", 0.88)
    speak_alert("Plastic bin is almost full. Please empty soon.")
    time.sleep(6)   # wait for speech to finish
    shutdown()
    print("[Voice] test complete")
