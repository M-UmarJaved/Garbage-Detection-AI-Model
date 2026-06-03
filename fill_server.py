"""
fill_server.py  —  Bin Fill Level HTTP Server
===============================================
Runs a Flask web server on port 5050 in a background thread.
The ESP32-WROOM sends periodic GET requests:

    http://<laptop-ip>:5050/fill?plastic=82&paper=45

This module stores every reading in SQLite via logger.py
and exposes a /status endpoint for health checks.

Run standalone :  python fill_server.py
Run embedded   :  import fill_server; fill_server.start()
"""

import threading
import time
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
HOST = "0.0.0.0"    # accept from all interfaces (ESP32 on local network)
PORT = 5050

# Thresholds for voice alerts
ALERT_THRESHOLD = 85.0     # % — trigger voice alert when bin this full

# ─────────────────────────────────────────────
# LATEST READINGS  (in-memory cache for dashboard)
# ─────────────────────────────────────────────
_latest_plastic: float = 0.0
_latest_paper:   float = 0.0
_last_update:    str   = "Never"
_reading_count:  int   = 0


def get_latest() -> dict:
    """Return the most recent in-memory readings (used by dashboard)."""
    return {
        "plastic_pct":   _latest_plastic,
        "paper_pct":     _latest_paper,
        "last_update":   _last_update,
        "reading_count": _reading_count,
    }


# ─────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────
def _create_app():
    from flask import Flask, request, jsonify
    import logger

    app = Flask(__name__)

    # Suppress Flask's default banner
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    @app.route("/fill", methods=["GET"])
    def receive_fill():
        """
        Endpoint called by ESP32-WROOM.
        Query params:  plastic  (0-100)
                       paper    (0-100)
        """
        global _latest_plastic, _latest_paper, _last_update, _reading_count
        try:
            plastic = float(request.args.get("plastic", 0))
            paper   = float(request.args.get("paper",   0))

            # Clamp to valid range
            plastic = max(0.0, min(100.0, plastic))
            paper   = max(0.0, min(100.0, paper))

            _latest_plastic = plastic
            _latest_paper   = paper
            _reading_count += 1
            from datetime import datetime
            _last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Persist to SQLite
            logger.log_fill(plastic_pct=plastic, paper_pct=paper)

            # Voice alert if bin is near full
            try:
                import voice
                if plastic >= ALERT_THRESHOLD:
                    voice.speak_alert(f"Warning! Plastic bin is {int(plastic)} percent full. Please empty soon.")
                if paper >= ALERT_THRESHOLD:
                    voice.speak_alert(f"Warning! Paper bin is {int(paper)} percent full. Please empty soon.")
            except Exception:
                pass

            print(f"[FillServer] Plastic: {plastic:.1f}%  Paper: {paper:.1f}%")
            return jsonify({
                "status": "ok",
                "plastic_pct": plastic,
                "paper_pct":   paper,
                "timestamp":   _last_update
            }), 200

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/status", methods=["GET"])
    def status():
        """Health check endpoint."""
        return jsonify({
            "status":        "running",
            "readings":      _reading_count,
            "plastic_pct":   _latest_plastic,
            "paper_pct":     _latest_paper,
            "last_update":   _last_update,
        }), 200

    @app.route("/", methods=["GET"])
    def index():
        return (
            "<h2>🗑️ Garbage Bin Fill Server</h2>"
            f"<p>Plastic: {_latest_plastic:.1f}% | Paper: {_latest_paper:.1f}%</p>"
            f"<p>Readings: {_reading_count} | Last: {_last_update}</p>"
            "<p>Use <code>/fill?plastic=XX&paper=XX</code> to submit readings.</p>"
        ), 200

    return app


# ─────────────────────────────────────────────
# START IN BACKGROUND THREAD
# ─────────────────────────────────────────────
_server_thread: threading.Thread | None = None

def start() -> None:
    """Start the Flask fill server in a background daemon thread."""
    global _server_thread

    def _run():
        app = _create_app()
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

    _server_thread = threading.Thread(target=_run, daemon=True, name="FillServer")
    _server_thread.start()
    time.sleep(0.8)   # give Flask a moment to bind
    print(f"[FillServer] OK  Bin fill server running on http://{HOST}:{PORT}")
    print(f"[FillServer] ESP32 should GET: http://<your-laptop-ip>:{PORT}/fill?plastic=XX&paper=XX")


# ─────────────────────────────────────────────
# STANDALONE RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import logger
    logger.init()
    print("=" * 55)
    print("  BIN FILL LEVEL SERVER")
    print("=" * 55)
    print(f"Listening on http://0.0.0.0:{PORT}")
    print(f"Test with:  http://localhost:{PORT}/fill?plastic=72&paper=45")
    print("Press Ctrl+C to stop")
    print("=" * 55)
    app = _create_app()
    app.run(host=HOST, port=PORT, debug=True)
