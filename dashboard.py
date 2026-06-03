"""
dashboard.py  —  Live Analytics Dashboard
==========================================
Run with:   streamlit run dashboard.py

Features
--------
  • Real-time auto-refresh every 3 seconds
  • Animated KPI cards (total detections, avg confidence, FPS, sessions)
  • Interactive Plotly line chart — detections over time
  • Animated donut chart — class distribution
  • Bin fill level gauges (plastic & paper)
  • Historical fill-level area chart
  • Raw detection log table with colour-coded classes
  • Dark glassmorphism theme with gradient accents
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import os
import sys

# ─────────────────────────────────────────────
# ENSURE logger.py is importable from same dir
# ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logger

# ─────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GarbAI — Detection Dashboard",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GLOBAL CSS  — Dark glassmorphism theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Root variables ── */
:root {
    --bg-primary:   #0a0e1a;
    --bg-secondary: #111827;
    --bg-card:      rgba(17, 24, 39, 0.85);
    --bg-glass:     rgba(255,255,255,0.04);
    --accent-green: #00ff88;
    --accent-blue:  #3b82f6;
    --accent-purple:#a855f7;
    --accent-amber: #f59e0b;
    --accent-red:   #ef4444;
    --text-primary: #f1f5f9;
    --text-muted:   #94a3b8;
    --border:       rgba(255,255,255,0.08);
    --glow-green:   0 0 20px rgba(0,255,136,0.25);
    --glow-blue:    0 0 20px rgba(59,130,246,0.25);
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 2rem !important; max-width: 1400px; }

/* ── Animated gradient header ── */
.dashboard-header {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a0e1a 100%);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.dashboard-header::before {
    content: '';
    position: absolute;
    top: -50%;  left: -50%;
    width: 200%; height: 200%;
    background: conic-gradient(
        from 0deg at 50% 50%,
        transparent 0deg,
        rgba(0,255,136,0.06) 60deg,
        transparent 120deg,
        rgba(59,130,246,0.06) 180deg,
        transparent 240deg,
        rgba(168,85,247,0.06) 300deg,
        transparent 360deg
    );
    animation: rotateGradient 12s linear infinite;
    z-index: 0;
}
@keyframes rotateGradient {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
.dashboard-header > * { position: relative; z-index: 1; }
.header-title {
    font-size: 2.4rem;
    font-weight: 900;
    background: linear-gradient(135deg, #00ff88, #3b82f6, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0; line-height: 1.1;
}
.header-subtitle {
    color: var(--text-muted);
    font-size: 0.95rem;
    margin-top: 0.4rem;
    font-weight: 400;
}
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(0,255,136,0.12);
    border: 1px solid rgba(0,255,136,0.3);
    color: #00ff88;
    border-radius: 50px;
    padding: 4px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.live-dot {
    width: 7px; height: 7px;
    background: #00ff88;
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.4; transform:scale(0.7); }
}

/* ── KPI Cards ── */
.kpi-card {
    background: var(--bg-glass);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, border-color 0.25s ease;
    height: 100%;
}
.kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.15);
}
.kpi-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 0 0 16px 16px;
}
.kpi-green::after  { background: linear-gradient(90deg, transparent, #00ff88, transparent); }
.kpi-blue::after   { background: linear-gradient(90deg, transparent, #3b82f6, transparent); }
.kpi-purple::after { background: linear-gradient(90deg, transparent, #a855f7, transparent); }
.kpi-amber::after  { background: linear-gradient(90deg, transparent, #f59e0b, transparent); }

.kpi-icon {
    font-size: 1.8rem;
    margin-bottom: 0.6rem;
    display: block;
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.kpi-green  .kpi-value  { color: #00ff88; }
.kpi-blue   .kpi-value  { color: #60a5fa; }
.kpi-purple .kpi-value  { color: #c084fc; }
.kpi-amber  .kpi-value  { color: #fbbf24; }

.kpi-label {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.kpi-sublabel {
    font-size: 0.72rem;
    color: rgba(148,163,184,0.5);
    margin-top: 0.2rem;
}

/* ── Section headers ── */
.section-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0.5rem 0 1rem 0;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.section-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── Bin gauge card ── */
.gauge-card {
    background: var(--bg-glass);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.2rem;
    text-align: center;
    transition: transform 0.25s ease;
}
.gauge-card:hover { transform: translateY(-3px); }
.gauge-title {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 0.3rem;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }

/* ── Alert banner ── */
.alert-banner {
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    color: #fca5a5;
    font-size: 0.88rem;
    font-weight: 500;
    display: flex; align-items: center; gap: 8px;
}
.ok-banner {
    background: rgba(0,255,136,0.08);
    border: 1px solid rgba(0,255,136,0.25);
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    color: #86efac;
    font-size: 0.88rem;
    font-weight: 500;
    display: flex; align-items: center; gap: 8px;
}

/* ── Timestamp ── */
.timestamp-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-muted);
}

/* ── Divider ── */
.custom-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 1.5rem 0;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 3rem;
    color: var(--text-muted);
}
.empty-state .empty-icon { font-size: 3rem; margin-bottom: 0.8rem; }
.empty-state .empty-text { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickcolor="rgba(255,255,255,0.2)",
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickcolor="rgba(255,255,255,0.2)",
        showgrid=True,
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
    hoverlabel=dict(
        bgcolor="#1e293b",
        bordercolor="rgba(255,255,255,0.15)",
        font=dict(family="Inter", color="#f1f5f9"),
    ),
)

CLASS_COLORS = {
    "Small_Bottle":  "#00ff88",
    "Crushed_Paper": "#3b82f6",
    "unknown":       "#a855f7",
}


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=3)
def load_data():
    """Load all data from SQLite (cached for 3 seconds)."""
    logger.init()
    summary     = logger.get_summary()
    detections  = logger.get_detections(limit=1000)
    fills       = logger.get_fills(limit=300)
    return summary, detections, fills


def make_detections_df(detections: list[dict]) -> pd.DataFrame:
    if not detections:
        return pd.DataFrame()
    df = pd.DataFrame(detections)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    return df


def make_fills_df(fills: list[dict]) -> pd.DataFrame:
    if not fills:
        return pd.DataFrame()
    df = pd.DataFrame(fills)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    return df


# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────
def build_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Detections over time — grouped by minute."""
    if df.empty:
        return go.Figure()

    df["minute"] = df["timestamp"].dt.floor("1min")
    grouped = df.groupby(["minute", "class"]).size().reset_index(name="count")

    fig = go.Figure()
    for cls, color in CLASS_COLORS.items():
        sub = grouped[grouped["class"] == cls]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["minute"],
            y=sub["count"],
            name=cls.replace("_", " "),
            mode="lines+markers",
            line=dict(color=color, width=2.5, shape="spline"),
            marker=dict(size=5, color=color,
                        line=dict(color="rgba(0,0,0,0.5)", width=1)),
            fill="tozeroy",
            fillcolor=f"rgba{(*_hex_to_rgb(color), 0.08)}",
            hovertemplate=f"<b>{cls}</b><br>%{{x|%H:%M}}<br>Count: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Detections Over Time", font=dict(size=14, color="#f1f5f9"), x=0.01),
        height=320,
    )
    return fig


def build_donut_chart(summary: dict) -> go.Figure:
    """Class distribution donut."""
    labels  = ["Plastic Bottle", "Crushed Paper"]
    values  = [summary["bottle_count"], summary["paper_count"]]
    colors  = ["#00ff88", "#3b82f6"]

    if sum(values) == 0:
        values = [1, 1]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(
            colors=colors,
            line=dict(color="#0a0e1a", width=3),
        ),
        textfont=dict(size=12, color="#f1f5f9"),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))

    total = summary["total_detections"]
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px'>Total</span>",
        x=0.5, y=0.5,
        font=dict(size=22, color="#f1f5f9"),
        showarrow=False,
    )
    fig.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.05, y=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        height=300,
        title=dict(text="Class Distribution", font=dict(size=14, color="#f1f5f9"), x=0.01),
    )
    return fig


def build_gauge_chart(value: float, label: str, color: str) -> go.Figure:
    """Circular gauge for bin fill level."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        number=dict(suffix="%", font=dict(size=28, color=color)),
        delta=dict(reference=50, increasing=dict(color="#ef4444"),
                   decreasing=dict(color="#00ff88")),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=1,
                tickcolor="rgba(255,255,255,0.15)",
                tickfont=dict(size=9, color="#94a3b8"),
            ),
            bar=dict(color=color, thickness=0.6),
            bgcolor="rgba(255,255,255,0.04)",
            borderwidth=1,
            bordercolor="rgba(255,255,255,0.08)",
            steps=[
                dict(range=[0, 50],   color="rgba(0,255,136,0.06)"),
                dict(range=[50, 75],  color="rgba(245,158,11,0.08)"),
                dict(range=[75, 100], color="rgba(239,68,68,0.10)"),
            ],
            threshold=dict(
                line=dict(color="#ef4444", width=2),
                thickness=0.75,
                value=85,
            ),
        ),
    ))
    fig.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=220,
        title=dict(text=label, font=dict(size=13, color="#f1f5f9"), x=0.5, xanchor="center"),
    )
    return fig


def build_fill_history_chart(df: pd.DataFrame) -> go.Figure:
    """Area chart of bin fill history."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["plastic_pct"],
        name="Plastic Bin",
        mode="lines",
        line=dict(color="#00ff88", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,255,136,0.08)",
        hovertemplate="<b>Plastic</b><br>%{x|%H:%M:%S}<br>%{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["paper_pct"],
        name="Paper Bin",
        mode="lines",
        line=dict(color="#3b82f6", width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
        hovertemplate="<b>Paper</b><br>%{x|%H:%M:%S}<br>%{y:.1f}%<extra></extra>",
    ))

    # Alert line at 85%
    fig.add_hline(y=85, line=dict(color="#ef4444", width=1, dash="dot"),
                  annotation_text="Alert threshold",
                  annotation_font=dict(color="#ef4444", size=10))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=240,
        title=dict(text="Bin Fill History", font=dict(size=14, color="#f1f5f9"), x=0.01),
        yaxis=dict(**PLOTLY_LAYOUT["yaxis"], range=[0, 105]),
    )
    return fig


def build_confidence_hist(df: pd.DataFrame) -> go.Figure:
    """Confidence distribution histogram."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    for cls, color in CLASS_COLORS.items():
        sub = df[df["class"] == cls]
        if sub.empty:
            continue
        fig.add_trace(go.Histogram(
            x=sub["confidence"] * 100,
            name=cls.replace("_", " "),
            marker_color=color,
            opacity=0.75,
            xbins=dict(start=0, end=100, size=5),
            hovertemplate=f"<b>{cls}</b><br>Confidence: %{{x}}%<br>Count: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="overlay",
        height=280,
        title=dict(text="Confidence Distribution", font=dict(size=14, color="#f1f5f9"), x=0.01),
        xaxis=dict(**PLOTLY_LAYOUT["xaxis"], title="Confidence (%)", range=[0, 100]),
        yaxis=dict(**PLOTLY_LAYOUT["yaxis"], title="Frequency"),
    )
    return fig


def build_fps_chart(df: pd.DataFrame) -> go.Figure:
    """FPS over time line chart."""
    if df.empty or "fps" not in df.columns:
        return go.Figure()

    df_fps = df[df["fps"] > 0].copy()
    if df_fps.empty:
        return go.Figure()

    df_fps["minute"] = df_fps["timestamp"].dt.floor("1min")
    avg_fps = df_fps.groupby("minute")["fps"].mean().reset_index()

    fig = go.Figure(go.Scatter(
        x=avg_fps["minute"],
        y=avg_fps["fps"],
        mode="lines+markers",
        line=dict(color="#a855f7", width=2.5, shape="spline"),
        marker=dict(size=4, color="#a855f7"),
        fill="tozeroy",
        fillcolor="rgba(168,85,247,0.08)",
        hovertemplate="<b>FPS</b><br>%{x|%H:%M}<br>Avg: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
        title=dict(text="Average FPS Over Time", font=dict(size=14, color="#f1f5f9"), x=0.01),
        yaxis=dict(**PLOTLY_LAYOUT["yaxis"], title="FPS"),
    )
    return fig


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def kpi_card(icon: str, value, label: str, sublabel: str, color_class: str):
    st.markdown(f"""
    <div class="kpi-card {color_class}">
        <span class="kpi-icon">{icon}</span>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-sublabel">{sublabel}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(icon: str, title: str, dot_color: str):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-dot" style="background:{dot_color};
             box-shadow:0 0 8px {dot_color};"></div>
        {icon} {title}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:1rem 0 1.5rem;">
        <div style="font-size:2.5rem;">🗑️</div>
        <div style="font-size:1.1rem; font-weight:800;
             background:linear-gradient(135deg,#00ff88,#3b82f6);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;
             background-clip:text;">GarbAI</div>
        <div style="font-size:0.72rem; color:#64748b; margin-top:2px;">
            Detection Analytics
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    refresh_rate = st.selectbox(
        "🔄 Auto-refresh interval",
        options=[3, 5, 10, 30, 60],
        index=0,
        format_func=lambda x: f"Every {x}s",
    )

    time_filter = st.selectbox(
        "⏱️ Time window",
        options=["Last 15 min", "Last 1 hour", "Last 6 hours", "Last 24 hours", "All time"],
        index=1,
    )

    show_raw_log = st.checkbox("📋 Show raw log table", value=True)
    show_fps     = st.checkbox("📈 Show FPS chart", value=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#475569; line-height:1.6;">
        <b style="color:#64748b;">HOW TO USE</b><br>
        1. Start <code>fina-v2.py</code> to begin detection<br>
        2. Start <code>fill_server.py</code> for bin levels<br>
        3. This dashboard auto-refreshes
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    now_str = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
    <div class="timestamp-text" style="text-align:center;">
        Last loaded: {now_str}
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔃 Force Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
summary, detections_raw, fills_raw = load_data()
det_df  = make_detections_df(detections_raw)
fill_df = make_fills_df(fills_raw)

# Apply time filter
TIME_MAP = {
    "Last 15 min":   15,
    "Last 1 hour":   60,
    "Last 6 hours":  360,
    "Last 24 hours": 1440,
    "All time":      None,
}
minutes = TIME_MAP[time_filter]
if minutes and not det_df.empty:
    cutoff  = datetime.now() - timedelta(minutes=minutes)
    det_df  = det_df[det_df["timestamp"] >= cutoff]
if minutes and not fill_df.empty:
    cutoff  = datetime.now() - timedelta(minutes=minutes)
    fill_df = fill_df[fill_df["timestamp"] >= cutoff]


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(f"""
<div class="dashboard-header">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem;">
        <div>
            <h1 class="header-title">🗑️ GarbAI Dashboard</h1>
            <p class="header-subtitle">
                Real-time garbage detection analytics &nbsp;|&nbsp;
                ESP32-CAM + YOLO Model
            </p>
        </div>
        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:0.5rem;">
            <div class="live-badge">
                <div class="live-dot"></div>
                LIVE
            </div>
            <div class="timestamp-text">{datetime.now().strftime("%A, %d %B %Y  %H:%M:%S")}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BIN STATUS ALERTS
# ─────────────────────────────────────────────
plastic_fill = summary["latest_plastic"]
paper_fill   = summary["latest_paper"]

alert_msgs = []
if plastic_fill >= 85:
    alert_msgs.append(f"⚠️ Plastic bin is <b>{plastic_fill:.0f}%</b> full — please empty soon!")
if paper_fill >= 85:
    alert_msgs.append(f"⚠️ Paper bin is <b>{paper_fill:.0f}%</b> full — please empty soon!")

if alert_msgs:
    for msg in alert_msgs:
        st.markdown(f'<div class="alert-banner">🔴 &nbsp;{msg}</div>', unsafe_allow_html=True)
    st.markdown("")
elif summary["total_detections"] > 0:
    st.markdown('<div class="ok-banner">✅ &nbsp;All bins within normal levels. System running normally.</div>', unsafe_allow_html=True)
    st.markdown("")


# ─────────────────────────────────────────────
# KPI CARDS ROW
# ─────────────────────────────────────────────
section_header("📊", "KEY METRICS", "#00ff88")
c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    kpi_card(
        "🎯", summary["total_detections"],
        "Total Detections",
        f"{summary['bottle_count']} bottles · {summary['paper_count']} papers",
        "kpi-green"
    )
with c2:
    conf_val = f"{summary['avg_confidence']}%"
    kpi_card("🏆", conf_val, "Avg Confidence", "YOLOv5 detection accuracy", "kpi-blue")
with c3:
    fps_val = f"{summary['avg_fps']}" if summary["avg_fps"] else "—"
    kpi_card("⚡", fps_val, "Avg FPS", "Frames per second", "kpi-purple")
with c4:
    kpi_card("📁", summary["sessions_count"], "Sessions", "Total detection runs", "kpi-amber")


st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DETECTION TIMELINE + DONUT
# ─────────────────────────────────────────────
section_header("📈", "DETECTION ANALYTICS", "#3b82f6")
col_left, col_right = st.columns([2, 1], gap="medium")

with col_left:
    if det_df.empty:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-text">No detections yet.<br>Start <code>fina-v2.py</code> to begin detection.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        fig_tl = build_timeline_chart(det_df)
        st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})

with col_right:
    fig_donut = build_donut_chart(summary)
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})


st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BIN FILL LEVEL MONITORING
# ─────────────────────────────────────────────
section_header("🗑️", "BIN FILL LEVELS", "#f59e0b")
g1, g2, g3 = st.columns([1, 1, 2], gap="medium")

with g1:
    st.plotly_chart(
        build_gauge_chart(plastic_fill, "🟢 Plastic Bin", "#00ff88"),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with g2:
    st.plotly_chart(
        build_gauge_chart(paper_fill, "🔵 Paper Bin", "#3b82f6"),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with g3:
    if fill_df.empty:
        st.markdown("""
        <div class="empty-state" style="padding:2rem;">
            <div class="empty-icon">📡</div>
            <div class="empty-text">No fill readings yet.<br>
            Start <code>fill_server.py</code> and connect ESP32-WROOM.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.plotly_chart(
            build_fill_history_chart(fill_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONFIDENCE DISTRIBUTION + FPS
# ─────────────────────────────────────────────
section_header("🔬", "PERFORMANCE ANALYTICS", "#a855f7")
pa1, pa2 = st.columns(2, gap="medium")

with pa1:
    if det_df.empty:
        st.markdown('<div class="empty-state"><div class="empty-icon">📉</div><div class="empty-text">No data yet.</div></div>', unsafe_allow_html=True)
    else:
        st.plotly_chart(
            build_confidence_hist(det_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

with pa2:
    if show_fps:
        if det_df.empty:
            st.markdown('<div class="empty-state"><div class="empty-icon">⚡</div><div class="empty-text">No FPS data yet.</div></div>', unsafe_allow_html=True)
        else:
            st.plotly_chart(
                build_fps_chart(det_df),
                use_container_width=True,
                config={"displayModeBar": False},
            )
    else:
        # Show a quick stats breakdown instead
        section_header("📊", "QUICK STATS", "#f59e0b")
        stats_data = {
            "Metric": ["Total Detections", "Bottles", "Papers", "Avg Confidence", "Avg FPS", "Sessions"],
            "Value":  [
                summary["total_detections"],
                summary["bottle_count"],
                summary["paper_count"],
                f"{summary['avg_confidence']}%",
                f"{summary['avg_fps']}",
                summary["sessions_count"],
            ]
        }
        st.dataframe(pd.DataFrame(stats_data), hide_index=True, use_container_width=True)


st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# RAW LOG TABLE
# ─────────────────────────────────────────────
if show_raw_log:
    section_header("📋", "RECENT DETECTIONS LOG", "#64748b")

    if det_df.empty:
        st.markdown('<div class="empty-state"><div class="empty-icon">🗒️</div><div class="empty-text">No log entries yet.</div></div>', unsafe_allow_html=True)
    else:
        display_df = det_df.copy().sort_values("timestamp", ascending=False).head(50)
        display_df["timestamp"]  = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        display_df["confidence"] = (display_df["confidence"] * 100).round(1).astype(str) + "%"
        display_df["fps"]        = display_df["fps"].round(1)

        # Select and rename columns
        cols = ["timestamp", "class", "confidence", "direction", "center_x", "center_y", "fps"]
        cols = [c for c in cols if c in display_df.columns]
        display_df = display_df[cols].rename(columns={
            "timestamp": "Timestamp",
            "class":     "Class",
            "confidence":"Confidence",
            "direction": "Direction",
            "center_x":  "Center X",
            "center_y":  "Center Y",
            "fps":       "FPS",
        })

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            height=320,
            column_config={
                "Class": st.column_config.TextColumn("Class 🏷️"),
                "Confidence": st.column_config.TextColumn("Confidence 🎯"),
                "Direction": st.column_config.TextColumn("Direction 🧭"),
                "FPS": st.column_config.NumberColumn("FPS ⚡", format="%.1f"),
            }
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="
    text-align:center;
    padding: 1.5rem 0 0.5rem;
    color: #334155;
    font-size: 0.78rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 1rem;
">
    🗑️ <b>GarbAI Detection Dashboard</b> &nbsp;·&nbsp;
    Built with Streamlit &amp; Plotly &nbsp;·&nbsp;
    YOLO + ESP32-CAM &nbsp;·&nbsp;
    Auto-refreshes every {refresh_rate}s
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# AUTO-REFRESH
# ─────────────────────────────────────────────
time.sleep(refresh_rate)
st.rerun()
