"""
logger.py  —  SQLite Event Logger
==================================
Foundation module for the Garbage Detection Feature Extension.

Tables
------
  detections  : every YOLO detection event
  bins        : bin fill-level readings from ESP32-WROOM
  sessions    : tracks each run of fina-v2.py

Usage (from fina-v2.py)
-----------------------
  import logger
  logger.init()
  logger.log_detection({"timestamp": ..., "class": ..., ...})
  logger.log_fill(plastic_pct=82.0, paper_pct=45.0)
"""

import sqlite3
import os
from datetime import datetime

# ─────────────────────────────────────────────
# DATABASE PATH  (same folder as this script)
# ─────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(_BASE_DIR, "garbage.db")


# ─────────────────────────────────────────────
# INTERNAL HELPER
# ─────────────────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    """Open a connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# INITIALISE DATABASE (call once at startup)
# ─────────────────────────────────────────────
def init() -> None:
    """
    Create all tables if they do not exist yet.
    Safe to call every time the system starts.
    """
    conn = _get_conn()
    cur  = conn.cursor()

    # ── detections ──────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            class         TEXT    NOT NULL,
            confidence    REAL    NOT NULL,
            fps           REAL    DEFAULT 0,
            inference_ms  REAL    DEFAULT 0,
            direction     TEXT    DEFAULT '',
            center_x      INTEGER DEFAULT 0,
            center_y      INTEGER DEFAULT 0
        )
    """)

    # ── bins ────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bins (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            plastic_pct   REAL    NOT NULL,
            paper_pct     REAL    NOT NULL
        )
    """)

    # ── sessions ────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT    NOT NULL,
            end_time   TEXT,
            total_detections INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print(f"[Logger] OK  Database ready -> {DB_PATH}")


# ─────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────
_session_id: int | None = None

def start_session() -> int:
    """Create a new session row and return its id."""
    global _session_id
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (start_time) VALUES (?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
    )
    _session_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[Logger] Session #{_session_id} started")
    return _session_id

def end_session(total_detections: int = 0) -> None:
    """Mark the current session as ended."""
    global _session_id
    if _session_id is None:
        return
    conn = _get_conn()
    conn.execute(
        "UPDATE sessions SET end_time=?, total_detections=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_detections, _session_id)
    )
    conn.commit()
    conn.close()
    print(f"[Logger] Session #{_session_id} closed  ({total_detections} detections)")


# ─────────────────────────────────────────────
# LOG A DETECTION EVENT
# ─────────────────────────────────────────────
def log_detection(event: dict) -> None:
    """
    Insert one detection event.

    Expected keys (all optional except 'class'):
        timestamp     str   e.g. "2026-06-03 10:30:21"
        class         str   e.g. "Small_Bottle"
        confidence    float e.g. 0.95
        fps           float e.g. 28.3
        inference_ms  float e.g. 22.0
        direction     str   e.g. "TURN_LEFT"
        center_x      int
        center_y      int
    """
    ts = event.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    try:
        conn = _get_conn()
        conn.execute(
            """
            INSERT INTO detections
                (timestamp, class, confidence, fps, inference_ms, direction, center_x, center_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                event.get("class", "unknown"),
                float(event.get("confidence", 0.0)),
                float(event.get("fps", 0.0)),
                float(event.get("inference_ms", 0.0)),
                event.get("direction", ""),
                int(event.get("center_x", 0)),
                int(event.get("center_y", 0)),
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Logger] ⚠️  log_detection error: {e}")


# ─────────────────────────────────────────────
# LOG A BIN FILL READING
# ─────────────────────────────────────────────
def log_fill(plastic_pct: float, paper_pct: float) -> None:
    """
    Insert one bin fill reading.

    Args:
        plastic_pct : float  (0 – 100)
        paper_pct   : float  (0 – 100)
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO bins (timestamp, plastic_pct, paper_pct) VALUES (?, ?, ?)",
            (ts, float(plastic_pct), float(paper_pct))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Logger] ⚠️  log_fill error: {e}")


# ─────────────────────────────────────────────
# QUERY HELPERS  (used by dashboard + report)
# ─────────────────────────────────────────────
def get_detections(limit: int = 500) -> list[dict]:
    """Return the latest N detection rows as a list of dicts."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_fills(limit: int = 200) -> list[dict]:
    """Return the latest N bin fill rows."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM bins ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary() -> dict:
    """
    Return a high-level summary dict:
        total_detections  int
        bottle_count      int
        paper_count       int
        avg_confidence    float
        avg_fps           float
        latest_plastic    float
        latest_paper      float
        sessions_count    int
    """
    conn = _get_conn()
    d = conn.execute(
        "SELECT COUNT(*) as n, AVG(confidence) as ac, AVG(fps) as af FROM detections"
    ).fetchone()
    bottle = conn.execute(
        "SELECT COUNT(*) as n FROM detections WHERE class='Small_Bottle'"
    ).fetchone()
    paper = conn.execute(
        "SELECT COUNT(*) as n FROM detections WHERE class='Crushed_Paper'"
    ).fetchone()
    fill = conn.execute(
        "SELECT plastic_pct, paper_pct FROM bins ORDER BY id DESC LIMIT 1"
    ).fetchone()
    sess = conn.execute("SELECT COUNT(*) as n FROM sessions").fetchone()
    conn.close()

    return {
        "total_detections": d["n"]    if d    else 0,
        "bottle_count":     bottle["n"] if bottle else 0,
        "paper_count":      paper["n"]  if paper  else 0,
        "avg_confidence":   round(d["ac"] * 100, 1) if d and d["ac"] else 0.0,
        "avg_fps":          round(d["af"], 1)        if d and d["af"] else 0.0,
        "latest_plastic":   fill["plastic_pct"]      if fill else 0.0,
        "latest_paper":     fill["paper_pct"]        if fill else 0.0,
        "sessions_count":   sess["n"]                if sess else 0,
    }


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init()
    start_session()
    log_detection({
        "class": "Small_Bottle", "confidence": 0.95,
        "fps": 28.3, "inference_ms": 22.0,
        "direction": "TURN_LEFT", "center_x": 80, "center_y": 120
    })
    log_detection({
        "class": "Crushed_Paper", "confidence": 0.88,
        "fps": 27.1, "inference_ms": 24.5,
        "direction": "CENTER", "center_x": 160, "center_y": 100
    })
    log_fill(plastic_pct=72.0, paper_pct=35.0)
    end_session(total_detections=2)
    print("\n[Summary]:", get_summary())
    print("[Logger] test complete -- check garbage.db")
