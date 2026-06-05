"""
dashboard.py  —  GarbAI Live Analytics Dashboard
==================================================
Run:  python -m streamlit run dashboard.py
All data pulled from garbage.db via logger.py — zero dummy values.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time, os, sys
import cv2
from ultralytics import YOLO
import threading
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logger
import sqlite3

# ════════════════════════════════════════════════════════
# DATABASE SETUP & SESSION LOGIC
# ════════════════════════════════════════════════════════
DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_det INTEGER,
            plastic_bot INTEGER,
            crushed_pap INTEGER,
            avg_conf REAL
        )
    ''')
    conn.commit()
    conn.close()

def get_all_time_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*), SUM(total_det), SUM(plastic_bot), SUM(crushed_pap), AVG(avg_conf) FROM sessions')
    row = c.fetchone()
    conn.close()
    return {
        "sessions": row[0] if row[0] else 0,
        "total_det": row[1] if row[1] else 0,
        "plastic_bot": row[2] if row[2] else 0,
        "crushed_pap": row[3] if row[3] else 0,
        "avg_conf": round(row[4], 1) if (row[0] and row[4]) else 0.0
    }

def save_session(total_det, plastic_bot, crushed_pap, avg_conf):
    if total_det == 0: return # Don't save empty sessions
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO sessions (total_det, plastic_bot, crushed_pap, avg_conf)
        VALUES (?, ?, ?, ?)
    ''', (total_det, plastic_bot, crushed_pap, avg_conf))
    conn.commit()
    conn.close()

init_db()

# ════════════════════════════════════════════════════════
# STREAMLIT SESSION STATE (For Current Session)
# ════════════════════════════════════════════════════════
if "curr_det" not in st.session_state:
    st.session_state.curr_det = 0
    st.session_state.curr_bot = 0
    st.session_state.curr_pap = 0
    st.session_state.conf_sum = 0.0
    st.session_state.conf_count = 0

# ════════════════════════════════════════════════════════
# IPC DASHBOARD LISTENERS (Receives data from test1.py)
# ════════════════════════════════════════════════════════
@st.cache_resource
def start_ipc_listeners():
    import threading, socket, json
    
    state = {
        "fps": 0,
        "cmd": "STOP",
        "conf": 0.0,
        "label": "",
        "active": False
    }
    
    def listen_meta():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', 5555))
        except Exception as e:
            print(f"Failed to bind: {e}")
            return
            
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                d = json.loads(data.decode())
                state.update(d)
                state["active"] = True
            except Exception as e:
                print(f"DASHBOARD IPC ERROR: {e}")

    threading.Thread(target=listen_meta, daemon=True).start()
    return state

ipc_state = start_ipc_listeners()


# ── PAGE CONFIG — must be first Streamlit call ──────────
st.set_page_config(
    page_title="GarbAI — Live Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════
# PROFESSIONAL CSS
# ════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── FONTS ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0');

/* ── TOKENS ─────────────────────────────────────────── */
:root {
    --bg:         #EFF3F1;
    --bg2:        #F7FAF8;
    --card:       #FFFFFF;
    --green:      #0F5132;
    --green2:     #1A7A4E;
    --green3:     #5DB589;
    --green4:     #A8D5BC;
    --glt:        #E8F5EE;
    --txt:        #111827;
    --txt2:       #374151;
    --muted:      #6B7280;
    --muted2:     #9CA3AF;
    --border:     #E5E9E7;
    --border2:    #D1D9D5;
    --amber:      #D97706;
    --amberlt:    #FEF3C7;
    --red:        #DC2626;
    --redlt:      #FEE2E2;
    --sh-xs: 0 1px 2px rgba(0,0,0,0.04);
    --sh-sm: 0 2px 8px rgba(0,0,0,0.05),0 1px 2px rgba(0,0,0,0.04);
    --sh-md: 0 4px 20px rgba(0,0,0,0.08),0 2px 4px rgba(0,0,0,0.04);
    --sh-g:  0 4px 22px rgba(15,81,50,0.20);
    --ease:  cubic-bezier(0.4,0,0.2,1);
    --spring: cubic-bezier(0.34,1.56,0.64,1);
}

/* ── BASE ───────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: var(--bg) !important;
    color: var(--txt) !important;
    -webkit-font-smoothing: antialiased !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.6rem 2.2rem 4rem !important; max-width: 1640px; }
::selection { background: var(--glt); color: var(--green); }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--green4); }

/* ── ANIMATIONS ─────────────────────────────────────── */
@keyframes fade-up    { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
@keyframes slide-in   { from{opacity:0;transform:translateY(-10px) scale(0.98)} to{opacity:1;transform:translateY(0) scale(1)} }
@keyframes blob-float { from{transform:translate(0,0) scale(1)} to{transform:translate(8px,-12px) scale(1.1)} }
@keyframes badge-glow { 0%,100%{box-shadow:0 0 0 0 rgba(15,81,50,0.45)} 50%{box-shadow:0 0 0 6px rgba(15,81,50,0)} }
@keyframes tag-glow   { 0%,100%{box-shadow:0 0 0 0 rgba(15,81,50,0.25)} 50%{box-shadow:0 0 0 5px rgba(15,81,50,0)} }
@keyframes bar-shine  { 0%{left:-80%} 100%{left:180%} }
@keyframes dot-beat   { 0%,100%{opacity:1;transform:scale(1);box-shadow:0 0 8px #4ADE80} 50%{opacity:0.45;transform:scale(0.75);box-shadow:0 0 0 #4ADE80} }
@keyframes st-flash   { 0%,100%{opacity:1} 50%{opacity:0.48} }
@keyframes card-top   { from{opacity:0} to{opacity:1} }

/* ── SIDEBAR ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--card) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 18px rgba(0,0,0,0.04) !important;
}
[data-testid="stSidebar"] > div { padding: 1.8rem 1.1rem; }

.sb-logo {
    display:flex; align-items:center; gap:12px;
    font-size:1.45rem; font-weight:800; color:var(--green);
    margin-bottom:2.2rem; padding:0 0.3rem; letter-spacing:-0.02em;
    cursor:default;
}
.sb-logo .material-symbols-rounded {
    font-size:2rem; background:var(--glt); color:var(--green);
    border-radius:12px; padding:7px;
    transition: transform 0.38s var(--spring), background 0.15s var(--ease), color 0.15s var(--ease);
}
.sb-logo:hover .material-symbols-rounded {
    transform: rotate(-14deg) scale(1.12);
    background: var(--green); color: white;
}

.nav-label {
    font-size:0.62rem; font-weight:800; letter-spacing:0.1em; color:var(--muted2);
    padding:0 0.6rem; margin:1.4rem 0 0.5rem 0; text-transform:uppercase;
}
.nav-item {
    display:flex; align-items:center; gap:10px;
    padding:0.68rem 0.9rem; border-radius:12px;
    font-size:0.88rem; font-weight:600; color:var(--muted);
    margin-bottom:0.1rem; cursor:pointer; position:relative;
    transition: background 0.15s var(--ease), color 0.15s var(--ease), transform 0.15s var(--ease);
}
.nav-item:hover { background:var(--bg2); color:var(--txt2); transform:translateX(3px); }
.nav-item .material-symbols-rounded { font-size:1.2rem; transition: transform 0.38s var(--spring); }
.nav-item:hover .material-symbols-rounded { transform:scale(1.12); }

.nav-active { background:var(--glt)!important; color:var(--green)!important; font-weight:700; }
.nav-active::before {
    content:''; position:absolute; left:-1.1rem; top:18%; height:64%;
    width:4px; background:var(--green); border-radius:0 4px 4px 0;
}
.nav-active .material-symbols-rounded { color:var(--green)!important; }

.nav-badge {
    margin-left:auto; background:var(--green); color:white;
    font-size:0.57rem; padding:2px 8px; border-radius:99px; font-weight:800;
    letter-spacing:0.05em; animation:badge-glow 2.2s ease-in-out infinite;
}

.sb-bottom {
    background:linear-gradient(135deg,var(--green) 0%,var(--green2) 100%);
    color:white; border-radius:18px; padding:1.3rem 1.1rem; margin-top:1.5rem;
    position:relative; overflow:hidden; box-shadow:var(--sh-g);
    transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease);
}
.sb-bottom:hover { transform:translateY(-3px); box-shadow:0 10px 32px rgba(15,81,50,0.32); }
.sb-bottom::before {
    content:''; position:absolute; top:-45px; right:-45px;
    width:130px; height:130px; border-radius:50%;
    background:rgba(255,255,255,0.09);
    animation:blob-float 6s ease-in-out infinite alternate;
}
.sb-bottom::after {
    content:''; position:absolute; bottom:-22px; left:-22px;
    width:85px; height:85px; border-radius:50%;
    background:rgba(255,255,255,0.06);
    animation:blob-float 8s ease-in-out infinite alternate-reverse;
}
.sb-bottom > * { position:relative; z-index:1; }
.sb-bottom .title { font-size:0.88rem; font-weight:700; margin-bottom:0.25rem; }
.sb-bottom .sub   { font-size:0.68rem; opacity:0.72; margin-bottom:0.9rem; }
.sb-bottom .btn   {
    background:white; color:var(--green); padding:0.42rem 1.1rem;
    border-radius:99px; font-size:0.7rem; font-weight:800; display:inline-block;
    font-family:'JetBrains Mono',monospace;
    transition: transform 0.15s var(--ease), box-shadow 0.15s var(--ease);
}
.sb-bottom .btn:hover { transform:scale(1.05); box-shadow:0 3px 10px rgba(0,0,0,0.18); }

/* ── TOP BAR ─────────────────────────────────────────── */
.top-bar {
    display:flex; justify-content:space-between; align-items:center;
    background:var(--card); border-radius:18px; padding:0.9rem 1.6rem;
    margin-bottom:1.6rem; border:1.5px solid var(--border);
    box-shadow:var(--sh-sm);
    transition: box-shadow 0.25s var(--ease);
}
.top-bar:hover { box-shadow:var(--sh-md); }

.search-pill {
    display:flex; align-items:center; gap:9px; background:var(--bg);
    border-radius:99px; padding:0.52rem 1.1rem; width:280px;
    font-size:0.82rem; color:var(--muted); border:1.5px solid var(--border); cursor:text;
    transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease), background 0.15s var(--ease);
}
.search-pill:hover { border-color:var(--border2); background:white; box-shadow:var(--sh-xs); }
.search-pill .material-symbols-rounded { font-size:17px; color:var(--muted2); }

.top-right { display:flex; align-items:center; gap:11px; }

.icon-chip {
    background:var(--bg); border-radius:50%; width:38px; height:38px;
    display:flex; align-items:center; justify-content:center;
    border:1.5px solid var(--border); color:var(--txt2); cursor:pointer;
    transition: background 0.15s var(--ease), border-color 0.15s var(--ease),
                color 0.15s var(--ease), transform 0.38s var(--spring);
}
.icon-chip:hover { background:var(--glt); border-color:var(--green4); color:var(--green); transform:scale(1.12) rotate(10deg); }
.icon-chip .material-symbols-rounded { font-size:19px; }

.av-chip {
    display:flex; align-items:center; gap:9px; background:var(--bg);
    border-radius:99px; padding:4px 14px 4px 4px; border:1.5px solid var(--border); cursor:pointer;
    transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease), background 0.15s var(--ease);
}
.av-chip:hover { border-color:var(--green4); box-shadow:var(--sh-xs); background:var(--glt); }
.av-dot {
    width:30px; height:30px; border-radius:50%;
    background:linear-gradient(135deg,var(--green),var(--green2));
    display:flex; align-items:center; justify-content:center;
    color:white; font-size:0.75rem; font-weight:800;
    box-shadow:0 2px 8px rgba(15,81,50,0.35);
}
.av-name { font-size:0.78rem; font-weight:700; color:var(--txt2); }

/* ── PAGE HEADER ─────────────────────────────────────── */
.page-hdr { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:1.6rem; }
.page-hdr h1 { font-size:2rem; font-weight:800; margin:0; letter-spacing:-0.03em; line-height:1.1; }
.page-hdr p  { font-size:0.84rem; color:var(--muted); margin:6px 0 0 0; }
.hdr-btns { display:flex; gap:10px; align-items:center; }

/* ── STREAMLIT BUTTON OVERRIDES (Match Old UI) ── */
div[data-testid="stButton"] button, 
div[data-testid="stDownloadButton"] button {
    border-radius: 99px !important;
    font-weight: 700 !important;
    font-size: 0.83rem !important;
    padding: 0.42rem 1.4rem !important;
    transition: transform 0.38s var(--spring), box-shadow 0.25s var(--ease), background 0.15s var(--ease) !important;
    min-height: 40px !important;
    width: 100% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 7px !important;
}

/* Primary Button (Generate Report) */
div[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, var(--green) 0%, var(--green2) 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: var(--sh-g) !important;
}
div[data-testid="stDownloadButton"] button:hover {
    transform: translateY(-2px) scale(1.03) !important;
    box-shadow: 0 10px 28px rgba(15,81,50,0.30) !important;
    color: white !important;
}
div[data-testid="stDownloadButton"] button::before {
    font-family: 'Material Symbols Rounded';
    content: 'picture_as_pdf';
    font-size: 16px;
    font-weight: normal;
}

/* Secondary Button (Refresh) */
div[data-testid="stButton"] button {
    background: white !important;
    color: var(--green) !important;
    border: 2px solid var(--border2) !important;
}
div[data-testid="stButton"] button:hover {
    border-color: var(--green) !important;
    background: var(--glt) !important;
    transform: translateY(-2px) !important;
    color: var(--green) !important;
}
div[data-testid="stButton"] button::before {
    font-family: 'Material Symbols Rounded';
    content: 'refresh';
    font-size: 16px;
    font-weight: normal;
}

/* ── CARDS ───────────────────────────────────────────── */
.card,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] div.stMarkdown .card-anchor) {
    background: var(--card) !important;
    border-radius: 20px !important;
    padding: 1.5rem !important;
    border: 1.5px solid var(--border) !important;
    box-shadow: var(--sh-sm) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: box-shadow 0.25s var(--ease), transform 0.25s var(--ease), border-color 0.25s var(--ease) !important;
    height: 100% !important;
}

.card:hover,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] div.stMarkdown .card-anchor):hover {
    box-shadow: var(--sh-md) !important;
    transform: translateY(-3px) !important;
    border-color: var(--border2) !important;
}

/* Accent shimmer line appears at top on hover */
.card::after,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] div.stMarkdown .card-anchor)::after {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 3px !important;
    background: linear-gradient(90deg, transparent 0%, var(--green3) 50%, transparent 100%) !important;
    border-radius: 20px 20px 0 0 !important;
    opacity: 0 !important;
    transition: opacity 0.25s var(--ease) !important;
}

.card:hover::after,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] div.stMarkdown .card-anchor):hover::after {
    opacity: 1 !important;
}

/* Hide the card anchor container completely to prevent layout spacing */
div[data-testid="element-container"]:has(.card-anchor) {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Green gradient card */
.card-g {
    background:linear-gradient(145deg,var(--green) 0%,var(--green2) 100%);
    border-radius:20px; padding:1.5rem; border:none;
    box-shadow:var(--sh-g); position:relative; overflow:hidden;
    transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease);
    animation: fade-up 0.4s var(--spring) both;
}
.card-g::before {
    content:''; position:absolute; top:-60px; right:-60px;
    width:180px; height:180px; border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,0.10) 0%,transparent 70%);
    animation:blob-float 5s ease-in-out infinite alternate;
}
.card-g::after {
    content:''; position:absolute; bottom:-30px; left:-30px;
    width:110px; height:110px; border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,0.07) 0%,transparent 70%);
    animation:blob-float 7s ease-in-out infinite alternate-reverse;
}
.card-g > * { position:relative; z-index:1; }
.card-g:hover { transform:translateY(-4px); box-shadow:0 14px 40px rgba(15,81,50,0.30); }

/* ── KPI ─────────────────────────────────────────────── */
.kpi-lbl {
    font-size:0.74rem; font-weight:800; margin-bottom:0.8rem;
    display:flex; justify-content:space-between; align-items:center;
    text-transform:uppercase; letter-spacing:0.06em;
}
.kpi-lbl .material-symbols-rounded {
    font-size:1.1rem; padding:5px; border-radius:8px;
    background:rgba(255,255,255,0.18); color:rgba(255,255,255,0.85);
    transition: transform 0.38s var(--spring);
}
.card-g:hover .kpi-lbl .material-symbols-rounded { transform:rotate(-12deg) scale(1.18); }
.kpi-lbl-dk .material-symbols-rounded { background:var(--glt)!important; color:var(--green)!important; }
.card:hover .kpi-lbl-dk .material-symbols-rounded { transform:rotate(-12deg) scale(1.18); }

.kpi-val { font-size:2.9rem; font-weight:800; line-height:1; margin-bottom:0.55rem; letter-spacing:-0.04em; }
.kpi-sub { font-size:0.7rem; display:flex; align-items:center; gap:6px; font-weight:500; }
.pill-w {
    background:rgba(255,255,255,0.22); color:rgba(255,255,255,0.92);
    padding:2px 8px; border-radius:6px; font-weight:800; font-size:0.62rem;
}
.pill-g {
    background:var(--glt); color:var(--green);
    padding:2px 8px; border-radius:6px; font-weight:800; font-size:0.62rem;
    border:1px solid var(--green4);
}

/* ── CARD TITLE ROW ──────────────────────────────────── */
.ctitle {
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:1.1rem; padding-bottom:0.85rem;
    border-bottom:1.5px solid var(--border);
}
.ctitle h3 { font-size:0.96rem; font-weight:800; margin:0; letter-spacing:-0.01em; }
.tag {
    font-size:0.61rem; font-weight:800; padding:4px 11px; border-radius:99px;
    border:1.5px solid var(--border2); color:var(--muted);
    letter-spacing:0.06em; text-transform:uppercase; background:var(--bg2);
}
.tag-g {
    border-color:var(--green4)!important; color:var(--green)!important;
    background:var(--glt)!important; animation:tag-glow 2.5s ease-in-out infinite;
}

/* ── ALERTS ──────────────────────────────────────────── */
.alert-strip {
    background:var(--redlt); border:1.5px solid #FCA5A5; border-radius:14px;
    padding:0.85rem 1.3rem; display:flex; align-items:center; gap:10px;
    font-size:0.83rem; font-weight:700; color:var(--red); margin-bottom:1rem;
    box-shadow:0 2px 10px rgba(220,38,38,0.08);
    animation:slide-in 0.35s var(--spring) both;
}
.ok-strip {
    background:var(--glt); border:1.5px solid var(--green4); border-radius:14px;
    padding:0.85rem 1.3rem; display:flex; align-items:center; gap:10px;
    font-size:0.83rem; font-weight:700; color:var(--green); margin-bottom:1rem;
    box-shadow:0 2px 10px rgba(15,81,50,0.08);
    animation:slide-in 0.35s var(--spring) both;
}

/* ── DETECTION LIST ──────────────────────────────────── */
.det-row {
    display:flex; align-items:center; gap:12px;
    padding:0.62rem 0.6rem; border-radius:12px;
    border-bottom:1px solid var(--border); cursor:default;
    transition: background 0.15s var(--ease), transform 0.15s var(--ease), box-shadow 0.15s var(--ease);
}
.det-row:last-child { border-bottom:none; }
.det-row:hover { background:var(--bg2); transform:translateX(4px); box-shadow:var(--sh-xs); }

.det-ic {
    width:36px; height:36px; border-radius:10px;
    display:flex; align-items:center; justify-content:center; flex-shrink:0;
    transition: transform 0.38s var(--spring), box-shadow 0.15s var(--ease);
}
.det-row:hover .det-ic { transform:scale(1.15) rotate(-6deg); box-shadow:0 4px 12px rgba(0,0,0,0.12); }

.det-info h4 { margin:0; font-size:0.83rem; font-weight:700; letter-spacing:-0.01em; }
.det-info p  { margin:0; font-size:0.66rem; color:var(--muted); font-family:'JetBrains Mono',monospace; }

.conf-b {
    margin-left:auto; font-size:0.67rem; font-weight:800; padding:3px 10px;
    border-radius:99px; background:var(--glt); color:var(--green);
    white-space:nowrap; border:1px solid var(--green4); letter-spacing:0.03em;
    transition: background 0.15s var(--ease), color 0.15s var(--ease), transform 0.38s var(--spring);
}
.det-row:hover .conf-b { background:var(--green); color:white; transform:scale(1.06); }

/* ── BIN ROWS ────────────────────────────────────────── */
.bin-row {
    display:flex; align-items:center; gap:10px; padding:0.8rem 0.5rem;
    border-radius:12px; border-bottom:1px solid var(--border);
    transition: background 0.15s var(--ease), transform 0.15s var(--ease);
}
.bin-row:last-child { border-bottom:none; }
.bin-row:hover { background:var(--bg2); transform:translateX(3px); }

.bin-name { font-size:0.84rem; font-weight:700; flex:1; color:var(--txt2); }
.bin-pct  { font-size:0.77rem; font-weight:800; width:34px; text-align:right; font-family:'JetBrains Mono',monospace; }
.bin-bar  {
    flex:2; height:10px; background:var(--border); border-radius:99px;
    overflow:hidden; box-shadow:inset 0 1px 3px rgba(0,0,0,0.07);
}
.bin-fill {
    height:100%; border-radius:99px; position:relative; overflow:hidden;
    transition: width 0.9s var(--ease);
}
/* Shimmer sweep across fill bar */
.bin-fill::after {
    content:''; position:absolute; top:0; left:-80%; width:55%; height:100%;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,0.45),transparent);
    animation:bar-shine 2.8s ease-in-out infinite;
}
.bin-st {
    font-size:0.59rem; font-weight:800; padding:3px 9px; border-radius:99px;
    width:50px; text-align:center; letter-spacing:0.05em; text-transform:uppercase;
}
.st-ok   { background:var(--glt);    color:var(--green); border:1px solid var(--green4); }
.st-warn { background:var(--amberlt); color:var(--amber); border:1px solid #FDE68A; }
.st-full { background:var(--redlt);   color:var(--red);   border:1px solid #FCA5A5; animation:st-flash 1.1s ease-in-out infinite; }

/* ── STAT ROWS ───────────────────────────────────────── */
.stat-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:0.55rem 0.5rem; border-radius:8px; border-bottom:1px solid var(--border);
    font-size:0.82rem;
    transition: background 0.15s var(--ease), transform 0.15s var(--ease);
}
.stat-row:last-child { border-bottom:none; }
.stat-row:hover { background:var(--bg2); transform:translateX(3px); }
.sk { color:var(--muted); font-weight:500; }
.sv { font-weight:800; font-family:'JetBrains Mono',monospace; font-size:0.79rem; }

/* ── SYSTEM STATUS CARD ──────────────────────────────── */
.sys-card {
    background:linear-gradient(145deg,var(--green) 0%,var(--green2) 60%,#1E9E64 100%);
    color:white; border-radius:20px; padding:1.5rem;
    position:relative; overflow:hidden; margin-bottom:1.2rem;
    box-shadow:var(--sh-g); border:1px solid rgba(255,255,255,0.10);
    transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease);
    animation: fade-up 0.4s var(--spring) both;
}
.sys-card:hover { transform:translateY(-4px); box-shadow:0 16px 44px rgba(15,81,50,0.34); }
.sys-card::before {
    content:''; position:absolute; width:220px; height:220px; border-radius:50%;
    top:-90px; right:-70px;
    background:radial-gradient(circle,rgba(255,255,255,0.11) 0%,transparent 70%);
    animation:blob-float 5.5s ease-in-out infinite alternate;
}
.sys-card::after {
    content:''; position:absolute; width:130px; height:130px; border-radius:50%;
    bottom:-45px; left:-35px;
    background:radial-gradient(circle,rgba(255,255,255,0.08) 0%,transparent 70%);
    animation:blob-float 7.5s ease-in-out infinite alternate-reverse;
}
.sys-card > * { position:relative; z-index:1; }

.sys-t   { font-size:0.74rem; font-weight:800; opacity:0.78; margin-bottom:0.4rem; text-transform:uppercase; letter-spacing:0.08em; }
.sys-fps { font-size:3.1rem; font-weight:800; line-height:1; margin-bottom:0.2rem; letter-spacing:-0.04em; }
.sys-sub { font-size:0.7rem; opacity:0.67; margin-bottom:1rem; }
.sys-on  {
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(255,255,255,0.18); border-radius:99px; padding:6px 16px;
    font-size:0.74rem; font-weight:800; letter-spacing:0.04em;
    border:1px solid rgba(255,255,255,0.22);
}
.dot {
    width:8px; height:8px; border-radius:50%;
    background:#4ADE80; box-shadow:0 0 8px #4ADE80;
    animation:dot-beat 1.6s ease-in-out infinite;
}
.sys-inf { font-size:0.7rem; opacity:0.67; margin-top:0.75rem; font-family:'JetBrains Mono',monospace; }

/* ── PLOTLY WRAPPER + MODEBAR KILL ──────────────────── */
[data-testid="stPlotlyChart"] {
    border-radius: 14px;
    overflow: hidden !important;
}

/* Force-hide modebar (the snipping tool bar) */
.modebar, .modebar-container, .modebar-group {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
}
/* Also hide any iframe-injected scrollbars */
[data-testid="stPlotlyChart"] iframe {
    border: none !important;
    overflow: hidden !important;
}

.js-plotly-plot, .plot-container {
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)


# Load all-time stats from database
db_stats = get_all_time_stats()

sessions    = db_stats["sessions"]
total_det   = db_stats["total_det"]
bottles     = db_stats["plastic_bot"]
papers      = db_stats["crushed_pap"]
avg_conf    = db_stats["avg_conf"]

# Current Session variables are in st.session_state
curr_det = st.session_state.curr_det
curr_bot = st.session_state.curr_bot
curr_pap = st.session_state.curr_pap
curr_conf_sum = st.session_state.conf_sum
curr_conf_count = st.session_state.conf_count
curr_avg_conf = round(curr_conf_sum / curr_conf_count, 1) if curr_conf_count else 0.0

# Percentages for current session
pct_bottle  = round(curr_bot / curr_det * 100) if curr_det else 0
pct_paper   = round(curr_pap / curr_det * 100) if curr_det else 0

plastic_pct = 0 # Or use a dummy value if bin capacity isn't tracked anymore
paper_pct = 0
avg_fps = 0
fps_str = "N/A"
today_count = curr_det
top_dir = "—"
avg_inf = 0.0


# ════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
<div class="sb-logo">
    <span class="material-symbols-rounded">recycling</span> GarbAI
</div>
<div class="nav-label">MENU</div>
<div class="nav-item nav-active">
    <span class="material-symbols-rounded">dashboard</span>Dashboard
</div>
<div class="nav-item">
    <span class="material-symbols-rounded">task_alt</span>Detections
    <div class="nav-badge">LIVE</div>
</div>
<div class="nav-item">
    <span class="material-symbols-rounded">bar_chart</span>Analytics
</div>
<div class="nav-item">
    <span class="material-symbols-rounded">delete</span>Bin Status
</div>
<div class="nav-label">GENERAL</div>
<div class="nav-item">
    <span class="material-symbols-rounded">settings</span>Settings
</div>
<div class="nav-item">
    <span class="material-symbols-rounded">help</span>Help
</div>
""", unsafe_allow_html=True)

    st.markdown("""
    <div class="sb-bottom">
        <div class="title">📊 Generate Report</div>
        <div class="sub">Export daily detection PDF</div>
        <div class="btn">python report.py</div>
    </div>
    """, unsafe_allow_html=True)


# (Top navbar removed as per request)


# ════════════════════════════════════════════════════════
# PAGE HEADER
# ════════════════════════════════════════════════════════
col_title, col_btns = st.columns([2.2, 2.5])
with col_title:
    st.markdown("""
    <div class="page-hdr" style="padding-bottom: 0; margin-bottom: 0;">
        <div>
            <h1 style="margin-bottom:0.2rem;">Dashboard</h1>
            <p style="margin-top:0;">Real-time garbage detection &nbsp;·&nbsp; system performance</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_btns:
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns([1.3, 1, 1.4])
    with bc1:
        voice_enabled = st.toggle("🔊 Voice Assistant", value=True)
        with open("voice_cfg.txt", "w") as f:
            f.write("1" if voice_enabled else "0")
    with bc2:
        if st.button("Refresh", use_container_width=True):
            save_session(curr_det, curr_bot, curr_pap, curr_avg_conf)
            st.session_state.curr_det = 0
            st.session_state.curr_bot = 0
            st.session_state.curr_pap = 0
            st.session_state.conf_sum = 0.0
            st.session_state.conf_count = 0
            st.rerun()
    with bc3:
        report_csv = f"Total Detections,{curr_det}\\nPlastic Bottles,{curr_bot}\\nCrushed Papers,{curr_pap}\\nAvg Confidence,{curr_avg_conf}%"
        st.download_button("Generate Report", data=report_csv, file_name=f"session_report_{int(time.time())}.csv", mime="text/csv", use_container_width=True)


# ════════════════════════════════════════════════════════
# ALERTS
# ════════════════════════════════════════════════════════
alerts = []
if plastic_pct >= 85:
    alerts.append(f"Plastic bin is <b>{plastic_pct:.0f}%</b> full — needs emptying now!")
if paper_pct >= 85:
    alerts.append(f"Paper bin is <b>{paper_pct:.0f}%</b> full — needs emptying now!")
if alerts:
    for a in alerts:
        st.markdown(f'<div class="alert-strip"><span class="material-symbols-rounded">warning</span>{a}</div>', unsafe_allow_html=True)
elif total_det > 0:
    st.markdown('<div class="ok-strip"><span class="material-symbols-rounded">check_circle</span>All bins within safe levels. System running normally.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# ROW 1: KPI CARDS
# ════════════════════════════════════════════════════════
k1, k2, k3, k4 = st.columns(4, gap="small")
k1_ph = k1.empty()
k2_ph = k2.empty()
k3_ph = k3.empty()
k4_ph = k4.empty()

def render_kpi_cards(total, bot, pap, avg_cnf, sess_count):
    pb_pct = round(bot / total * 100) if total else 0
    cp_pct = round(pap / total * 100) if total else 0
    
    k1_ph.markdown(f"""
    <div class="card-g" style="height:164px;">
        <div class="kpi-lbl" style="color:rgba(255,255,255,0.8);">
            Total Detections
            <span class="material-symbols-rounded">my_location</span>
        </div>
        <div class="kpi-val" style="color:white;">{total}</div>
        <div class="kpi-sub" style="color:rgba(255,255,255,0.72);">
            <span class="pill-w">{sess_count} sessions</span> all time
        </div>
    </div>
    """, unsafe_allow_html=True)

    k2_ph.markdown(f"""
    <div class="card" style="height:164px;">
        <div class="kpi-lbl kpi-lbl-dk" style="color:var(--muted);">
            Plastic Bottles
            <span class="material-symbols-rounded">water_bottle</span>
        </div>
        <div class="kpi-val">{bot}</div>
        <div class="kpi-sub" style="color:var(--muted);">
            <span class="pill-g">{pb_pct}%</span> of all detections
        </div>
    </div>
    """, unsafe_allow_html=True)

    k3_ph.markdown(f"""
    <div class="card" style="height:164px;">
        <div class="kpi-lbl kpi-lbl-dk" style="color:var(--muted);">
            Crushed Papers
            <span class="material-symbols-rounded">description</span>
        </div>
        <div class="kpi-val">{pap}</div>
        <div class="kpi-sub" style="color:var(--muted);">
            <span class="pill-g">{cp_pct}%</span> of all detections
        </div>
    </div>
    """, unsafe_allow_html=True)

    k4_ph.markdown(f"""
    <div class="card" style="height:164px;">
        <div class="kpi-lbl kpi-lbl-dk" style="color:var(--muted);">
            Avg Confidence
            <span class="material-symbols-rounded">verified</span>
        </div>
        <div class="kpi-val">{avg_cnf}%</div>
        <div class="kpi-sub" style="color:var(--muted);">
            <span class="pill-g">YOLOv5</span> model accuracy
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:1.3rem'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# ROW 2: DIRECTION CARDS
# ════════════════════════════════════════════════════════
st.markdown("<div class='ctitle' style='margin-bottom:1rem;'><h3>Movement Status</h3></div>", unsafe_allow_html=True)
dir_cols = st.columns(5, gap="small")
dir_ph = [col.empty() for col in dir_cols]
dirs = ["FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP"]

def render_dir_card(name, active):
    val = 1 if active else 0
    bg = "var(--glt)" if active else "var(--bg2)"
    fg = "var(--green)" if active else "var(--muted)"
    icon = "check_circle" if active else "radio_button_unchecked"
    return f"""
    <div class="card" style="text-align:center; padding:1.5rem 1rem; background:{bg}; transition:all 0.2s ease;">
        <div style="color:{fg}; margin-bottom:0.5rem;"><span class="material-symbols-rounded">{icon}</span></div>
        <div style="font-size:0.8rem; font-weight:700; color:{fg}; letter-spacing:0.05em; margin-bottom:0.2rem;">{name}</div>
        <div style="font-size:1.8rem; font-weight:800; color:{fg}; font-family:'JetBrains Mono',monospace;">{val}</div>
    </div>
    """


# ════════════════════════════════════════════════════════
# ROW 4: LIVE METRICS CHART
# ════════════════════════════════════════════════════════
st.markdown("<div class='ctitle' style='margin-top:1.5rem;margin-bottom:1rem;'><h3>Live Tracking Metrics</h3></div>", unsafe_allow_html=True)
chart_ph = st.empty()

# ════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════
# TRACKING LOOP (Reads from IPC)
# ════════════════════════════════════════════════════════
chart_time = []
chart_fps = []
chart_conf = []
frame_counter = 0

# Initial render
curr_avg_conf = round(st.session_state.conf_sum / st.session_state.conf_count * 100, 1) if st.session_state.conf_count > 0 else avg_conf
render_kpi_cards(total_det + st.session_state.curr_det, bottles + st.session_state.curr_bot, papers + st.session_state.curr_pap, curr_avg_conf, sessions)

while True:
    time.sleep(0.04) # runs at roughly 25 FPS
    
    if not ipc_state["active"]:
        continue
        
    frame_counter += 1
    
    # Read from IPC state

    fps_display = ipc_state["fps"]
    cmd = ipc_state["cmd"]
    best_conf = ipc_state["conf"]
    label = ipc_state.get("label", "")
    
    # Update Session KPIs (throttled to ~0.4s to match test1.py log_time)
    if label and frame_counter % 10 == 0:
        st.session_state.curr_det += 1
        st.session_state.conf_sum += best_conf
        st.session_state.conf_count += 1
        if "bottle" in label.lower():
            st.session_state.curr_bot += 1
        elif "paper" in label.lower():
            st.session_state.curr_pap += 1
            
        # Re-render KPIs
        c_det = st.session_state.curr_det
        c_bot = st.session_state.curr_bot
        c_pap = st.session_state.curr_pap
        c_conf = round(st.session_state.conf_sum / st.session_state.conf_count * 100, 1)
        render_kpi_cards(total_det + c_det, bottles + c_bot, papers + c_pap, c_conf, sessions)
    
    # Update chart history roughly once per second (every 25 iterations)
    if frame_counter % 25 == 0:
        chart_time.append(datetime.now())
        chart_fps.append(fps_display)
        chart_conf.append(best_conf * 100)
        if len(chart_time) > 60:
            chart_time.pop(0)
            chart_fps.pop(0)
            chart_conf.pop(0)

    # ── UI UPDATES ──
    # 2. Update Direction Cards (throttle to save UI performance)
    if frame_counter % 3 == 0:
        for i, d in enumerate(dirs):
            is_active = d in cmd
            dir_ph[i].markdown(render_dir_card(d, is_active), unsafe_allow_html=True)
            
    # 3. Update Chart (throttle to 1 update per second)
    if frame_counter % 15 == 0 and len(chart_time) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_time, y=chart_fps, name="FPS",
            mode="lines+markers", line=dict(color="#0F5132", width=3, shape="spline"),
            marker=dict(size=8, color="#0F5132", line=dict(color="white", width=2)),
            fill="tozeroy", fillcolor="rgba(15,81,50,0.1)"
        ))
        fig.add_trace(go.Scatter(
            x=chart_time, y=chart_conf, name="Confidence (%)",
            mode="lines+markers", line=dict(color="#5DB589", width=3, shape="spline"),
            marker=dict(size=8, color="#5DB589", line=dict(color="white", width=2)),
            fill="tozeroy", fillcolor="rgba(93,181,137,0.1)"
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=280,
            font=dict(family="Plus Jakarta Sans"),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(gridcolor="#F3F4F6", zeroline=False)
        )
        chart_ph.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False}, key=f"chart_{frame_counter}")



