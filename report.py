"""
report.py  —  PDF Report Generator
=====================================
Generates a professional PDF report from the SQLite database.

Usage
-----
  python report.py              → daily report (today)
  python report.py --period weekly   → last 7 days
  python report.py --period monthly  → last 30 days
  python report.py --output my_report.pdf  → custom output name

Output
------
  garbage_report_YYYY-MM-DD.pdf  in the project directory
"""

import argparse
import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# ENSURE logger.py is importable
# ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logger

# ─────────────────────────────────────────────
# COLOUR PALETTE  (RGB tuples) - CLICKUP LIGHT MODE
# ─────────────────────────────────────────────
C_BG        = (255, 255, 255)  # white
C_PRIMARY   = (0,   200, 117)  # clickup green
C_ACCENT    = (21,  101, 192)  # blue
C_PURPLE    = (123, 104, 238)  # clickup purple
C_AMBER     = (245, 166, 35)   # amber
C_WHITE     = (42,  46,  52)   # dark grey text (kept var name for compatibility)
C_MUTED     = (127, 133, 143)  # slate grey
C_CARD      = (247, 248, 249)  # faint card bg
C_DANGER    = (232, 61,  70)   # red

# ─────────────────────────────────────────────
# MATPLOTLIB CHART BUILDERS
# ─────────────────────────────────────────────
def _mpl_bar_chart(labels, values, colors, title, ylabel, save_path):
    """Render a styled bar chart and save as PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    bars = ax.bar(labels, values, color=colors, width=0.55,
                  edgecolor="#e2e8f0", linewidth=0.8, zorder=3)

    # Value labels on bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.02,
                str(int(val)),
                ha="center", va="bottom",
                color="#2a2e34", fontsize=9, fontweight="bold"
            )

    ax.set_title(title, color="#2a2e34", fontsize=11, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel, color="#7f858f", fontsize=9)
    ax.tick_params(colors="#7f858f", labelsize=8)
    ax.spines[:].set_color("#e2e8f0")
    ax.yaxis.grid(True, color="#f1f5f9", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#ffffff", edgecolor="none")
    plt.close()


def _mpl_line_chart(dates, values_dict, title, ylabel, save_path):
    """Render a styled line chart and save as PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    LINE_COLORS = ["#00c875", "#1565c0", "#7b68ee", "#f5a623"]

    fig, ax = plt.subplots(figsize=(7, 3.2))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    for i, (label, vals) in enumerate(values_dict.items()):
        color = LINE_COLORS[i % len(LINE_COLORS)]
        ax.plot(dates, vals, color=color, linewidth=2, label=label,
                marker="o", markersize=3)
        ax.fill_between(dates, vals, alpha=0.08, color=color)

    ax.set_title(title, color="#2a2e34", fontsize=11, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel, color="#7f858f", fontsize=9)
    ax.tick_params(colors="#7f858f", labelsize=7)
    ax.spines[:].set_color("#e2e8f0")
    ax.yaxis.grid(True, color="#f1f5f9", linewidth=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.legend(fontsize=8, facecolor="#ffffff", edgecolor="#e2e8f0",
               labelcolor="#2a2e34")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#ffffff", edgecolor="none")
    plt.close()


def _mpl_pie_chart(labels, values, colors, title, save_path):
    """Render a styled pie (donut) chart and save as PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 3.5))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    wedges, texts, autotexts = ax.pie(
        values if sum(values) > 0 else [1, 1],
        labels=labels,
        colors=colors,
        autopct="%1.1f%%" if sum(values) > 0 else None,
        startangle=140,
        wedgeprops=dict(width=0.55, edgecolor="#ffffff", linewidth=2),
        pctdistance=0.8,
    )
    for t in texts:
        t.set(color="#7f858f", fontsize=8)
    for at in autotexts:
        at.set(color="#ffffff", fontsize=8, fontweight="bold")

    ax.set_title(title, color="#2a2e34", fontsize=11, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#ffffff", edgecolor="none")
    plt.close()


# ─────────────────────────────────────────────
# QUERY HELPERS (with date filter)
# ─────────────────────────────────────────────
def _query(sql: str, params=()) -> list[dict]:
    conn = sqlite3.connect(logger.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_detections_for_period(since: datetime) -> list[dict]:
    return _query(
        "SELECT * FROM detections WHERE timestamp >= ? ORDER BY timestamp",
        (since.strftime("%Y-%m-%d %H:%M:%S"),)
    )


def get_fills_for_period(since: datetime) -> list[dict]:
    return _query(
        "SELECT * FROM bins WHERE timestamp >= ? ORDER BY timestamp",
        (since.strftime("%Y-%m-%d %H:%M:%S"),)
    )


# ─────────────────────────────────────────────
# PDF BUILDER
# ─────────────────────────────────────────────
def generate_report(period: str = "daily", output_path: str | None = None) -> str:
    """
    Generate a PDF report.

    Args:
        period      : 'daily', 'weekly', or 'monthly'
        output_path : full path to output PDF (auto-generated if None)

    Returns:
        str : path to the generated PDF file
    """
    try:
        from fpdf import FPDF, XPos, YPos
    except ImportError:
        print("[ERROR] fpdf2 not installed. Run: pip install fpdf2")
        sys.exit(1)

    try:
        import matplotlib
    except ImportError:
        print("[ERROR] matplotlib not installed. Run: pip install matplotlib")
        sys.exit(1)

    logger.init()

    # ── Period calculation ──
    now   = datetime.now()
    PERIOD_MAP = {"daily": 1, "weekly": 7, "monthly": 30}
    days  = PERIOD_MAP.get(period, 1)
    since = now - timedelta(days=days)
    period_label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}.get(period, "Daily")

    print(f"[Report] Generating {period_label} report ({since.strftime('%Y-%m-%d')} -> {now.strftime('%Y-%m-%d')})")

    # ── Fetch data ──
    detections = get_detections_for_period(since)
    fills      = get_fills_for_period(since)

    # ── Compute stats ──
    total       = len(detections)
    bottle_cnt  = sum(1 for d in detections if d["class"] == "Small_Bottle")
    paper_cnt   = sum(1 for d in detections if d["class"] == "Crushed_Paper")
    avg_conf    = (sum(d["confidence"] for d in detections) / total * 100) if total > 0 else 0
    avg_fps     = (sum(d["fps"]        for d in detections) / total)       if total > 0 else 0
    max_plastic = max((f["plastic_pct"] for f in fills), default=0)
    max_paper   = max((f["paper_pct"]   for f in fills), default=0)
    fill_reads  = len(fills)

    # ── Generate charts to temp files ──
    tmpdir = tempfile.mkdtemp()

    # Bar chart: detections by class
    bar_path = os.path.join(tmpdir, "bar.png")
    _mpl_bar_chart(
        ["Plastic Bottle", "Crushed Paper"],
        [bottle_cnt, paper_cnt],
        ["#00ff88", "#3b82f6"],
        "Detections by Class",
        "Count",
        bar_path,
    )

    # Pie chart: class distribution
    pie_path = os.path.join(tmpdir, "pie.png")
    _mpl_pie_chart(
        ["Plastic Bottle", "Crushed Paper"],
        [bottle_cnt, paper_cnt],
        ["#00ff88", "#3b82f6"],
        "Class Distribution",
        pie_path,
    )

    # Line chart: detections over time (by day)
    line_path = None
    if detections:
        from collections import defaultdict
        day_bottle  = defaultdict(int)
        day_paper   = defaultdict(int)
        for d in detections:
            day = datetime.strptime(d["timestamp"][:10], "%Y-%m-%d")
            if d["class"] == "Small_Bottle":
                day_bottle[day] += 1
            else:
                day_paper[day]  += 1
        all_days = sorted(set(list(day_bottle.keys()) + list(day_paper.keys())))
        if len(all_days) >= 2:
            line_path = os.path.join(tmpdir, "line.png")
            _mpl_line_chart(
                all_days,
                {
                    "Plastic Bottle": [day_bottle.get(d, 0) for d in all_days],
                    "Crushed Paper":  [day_paper.get(d, 0)  for d in all_days],
                },
                "Daily Detection Trend",
                "Detections",
                line_path,
            )

    # Bin fill line chart
    fill_path = None
    if len(fills) >= 2:
        fill_dates   = [datetime.strptime(f["timestamp"][:16], "%Y-%m-%d %H:%M") for f in fills]
        fill_plastic = [f["plastic_pct"] for f in fills]
        fill_paper   = [f["paper_pct"]   for f in fills]
        fill_path    = os.path.join(tmpdir, "fill.png")
        _mpl_line_chart(
            fill_dates,
            {"Plastic Bin": fill_plastic, "Paper Bin": fill_paper},
            "Bin Fill Level Over Time (%)",
            "Fill %",
            fill_path,
        )

    # ── Build PDF ──
    class GarbAIPDF(FPDF):
        def header(self):
            pass  # custom header on first page only

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*C_MUTED)
            self.cell(0, 5, f"GarbAI Detection System  |  Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Page {self.page_no()}", align="C")

    pdf = GarbAIPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    PAGE_W = pdf.w
    MARGIN = 15
    INNER_W = PAGE_W - 2 * MARGIN

    # ──────────────────────────────────────────
    # COVER / TITLE SECTION
    # ──────────────────────────────────────────
    # Dark background bar
    pdf.set_fill_color(*C_BG)
    pdf.rect(0, 0, PAGE_W, 52, "F")

    # Accent stripe
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 49, PAGE_W, 3, "F")

    pdf.set_xy(MARGIN, 10)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, "GarbAI Detection System", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 7, f"{period_label} Analytics Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(0, 6,
             f"Period: {since.strftime('%d %b %Y')} to {now.strftime('%d %b %Y')}   |   "
             f"Generated: {now.strftime('%d %b %Y  %H:%M:%S')}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(12)

    # ──────────────────────────────────────────
    # KPI SUMMARY CARDS  (2×2 grid)
    # ──────────────────────────────────────────
    def kpi_box(x, y, w, h, icon, value, label, color):
        # Card background
        pdf.set_fill_color(*C_CARD)
        pdf.rect(x, y, w, h, "F")
        # Left accent bar
        pdf.set_fill_color(*color)
        pdf.rect(x, y, 3, h, "F")
        # Icon + Value
        pdf.set_xy(x + 7, y + 4)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*color)
        pdf.cell(w - 10, 9, f"{icon}  {value}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x + 7, y + 14)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(w - 10, 5, label.upper())

    card_w = (INNER_W - 8) / 2
    card_h = 26
    row1_y  = pdf.get_y()

    kpi_box(MARGIN,              row1_y, card_w, card_h, "[T]", str(total),              "Total Detections",     C_PRIMARY)
    kpi_box(MARGIN + card_w + 8, row1_y, card_w, card_h, "[B]", str(bottle_cnt),         "Plastic Bottles",      C_ACCENT)

    pdf.ln(card_h + 6)
    row2_y = pdf.get_y()

    kpi_box(MARGIN,              row2_y, card_w, card_h, "[P]", str(paper_cnt),           "Crushed Papers",       C_PURPLE)
    kpi_box(MARGIN + card_w + 8, row2_y, card_w, card_h, "[%]", f"{avg_conf:.1f}%",       "Avg Confidence",       C_AMBER)

    pdf.ln(card_h + 10)

    # ──────────────────────────────────────────
    # PERFORMANCE STATS TABLE
    # ──────────────────────────────────────────
    def section_title(text, color=C_PRIMARY):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*color)
        pdf.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Underline
        y = pdf.get_y()
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.5)
        pdf.line(MARGIN, y, MARGIN + INNER_W, y)
        pdf.set_line_width(0.2)
        pdf.ln(4)

    section_title("Performance Summary")

    table_data = [
        ("Metric",                   "Value",              "Notes"),
        ("Total Detections",         str(total),           f"Over {days} day(s)"),
        ("Plastic Bottles",          str(bottle_cnt),      f"{bottle_cnt/total*100:.1f}% of total" if total else "N/A"),
        ("Crushed Papers",           str(paper_cnt),       f"{paper_cnt/total*100:.1f}% of total"  if total else "N/A"),
        ("Avg Detection Confidence", f"{avg_conf:.1f}%",   ">70% = reliable"),
        ("Avg FPS",                  f"{avg_fps:.1f}",     "Frames per second"),
        ("Bin Fill Readings",        str(fill_reads),      "From ESP32-WROOM ultrasonic sensor"),
        ("Max Plastic Bin Fill",     f"{max_plastic:.1f}%","Peak level in period"),
        ("Max Paper Bin Fill",       f"{max_paper:.1f}%",  "Peak level in period"),
    ]

    col_w = [INNER_W * 0.38, INNER_W * 0.22, INNER_W * 0.40]
    row_h = 7

    for i, row in enumerate(table_data):
        x = MARGIN
        # Alternate row shading
        if i == 0:
            pdf.set_fill_color(*C_CARD)
        elif i % 2 == 1:
            pdf.set_fill_color(248, 249, 250)
        else:
            pdf.set_fill_color(*C_BG)
        pdf.rect(x, pdf.get_y(), INNER_W, row_h, "F")

        for j, (cell, cw) in enumerate(zip(row, col_w)):
            pdf.set_xy(x + 2, pdf.get_y())
            if i == 0:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(*C_MUTED)
            elif j == 0:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(*C_WHITE)
            elif j == 1:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*C_PRIMARY)
            else:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*C_MUTED)
            pdf.cell(cw, row_h, cell)
            x += cw

        pdf.ln(row_h)

    pdf.ln(10)

    # ──────────────────────────────────────────
    # CHARTS PAGE
    # ──────────────────────────────────────────
    section_title("Detection Analytics")

    # Bar + Pie side by side
    if os.path.exists(bar_path) and os.path.exists(pie_path):
        half_w = (INNER_W - 6) / 2
        chart_h = 55
        pdf.image(bar_path, x=MARGIN,              y=pdf.get_y(), w=half_w, h=chart_h)
        pdf.image(pie_path, x=MARGIN + half_w + 6, y=pdf.get_y(), w=half_w, h=chart_h)
        pdf.ln(chart_h + 8)

    # Line chart (trend over days) — only if multi-day data
    if line_path and os.path.exists(line_path):
        section_title("Daily Trend")
        pdf.image(line_path, x=MARGIN, y=pdf.get_y(), w=INNER_W, h=55)
        pdf.ln(60)

    # Bin fill chart
    if fill_path and os.path.exists(fill_path):
        section_title("Bin Fill Level History", color=C_ACCENT)
        pdf.image(fill_path, x=MARGIN, y=pdf.get_y(), w=INNER_W, h=55)
        pdf.ln(60)

    # ──────────────────────────────────────────
    # RECENT DETECTIONS LOG TABLE
    # ──────────────────────────────────────────
    section_title("Recent Detections (Last 20)", color=C_PURPLE)

    log_headers = ["Timestamp", "Class", "Confidence", "Direction", "FPS"]
    log_widths  = [INNER_W*0.30, INNER_W*0.22, INNER_W*0.17, INNER_W*0.19, INNER_W*0.12]

    # Header row
    x = MARGIN
    pdf.set_fill_color(*C_CARD)
    pdf.rect(x, pdf.get_y(), INNER_W, 7, "F")
    for hdr, cw in zip(log_headers, log_widths):
        pdf.set_xy(x + 1, pdf.get_y())
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(cw, 7, hdr)
        x += cw
    pdf.ln(7)

    for i, d in enumerate(reversed(detections[-20:])):
        if pdf.get_y() > pdf.h - 30:
            pdf.add_page()
        x = MARGIN
        row_data = [
            d["timestamp"][:16],
            d["class"].replace("_", " "),
            f"{d['confidence']*100:.1f}%",
            d.get("direction", "N/A"),
            f"{d.get('fps', 0):.1f}",
        ]
        if i % 2 == 0:
            pdf.set_fill_color(248, 249, 250)
        else:
            pdf.set_fill_color(*C_BG)
        pdf.rect(MARGIN, pdf.get_y(), INNER_W, 6, "F")
        for val, cw in zip(row_data, log_widths):
            pdf.set_xy(x + 1, pdf.get_y())
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*C_WHITE)
            pdf.cell(cw, 6, str(val))
            x += cw
        pdf.ln(6)

    # ──────────────────────────────────────────
    # RECOMMENDATIONS
    # ──────────────────────────────────────────
    pdf.ln(8)
    section_title("Recommendations", color=C_AMBER)

    recs = []
    if total == 0:
        recs.append("[!] No detections in this period. Verify ESP32-CAM is connected and fina-v2.py is running.")
    if avg_conf < 70 and total > 0:
        recs.append("[!] Average confidence below 70%. Consider retraining with more images or adjusting lighting.")
    if max_plastic >= 85:
        recs.append(f"[!] Plastic bin reached {max_plastic:.0f}% fill. Schedule more frequent emptying.")
    if max_paper >= 85:
        recs.append(f"[!] Paper bin reached {max_paper:.0f}% fill. Schedule more frequent emptying.")
    if not recs:
        recs.append("[OK] All metrics are within normal range. System performing well.")
        recs.append(f"[OK] Detected {total} objects with {avg_conf:.1f}% average confidence. Excellent performance.")

    for rec in recs:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*C_WHITE)
        pdf.multi_cell(INNER_W, 6, rec, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    # ──────────────────────────────────────────
    # SAVE PDF
    # ──────────────────────────────────────────
    if output_path is None:
        base_dir    = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(base_dir, f"garbage_report_{now.strftime('%Y-%m-%d')}_{period}.pdf")

    pdf.output(output_path)
    print(f"[Report] PDF saved -> {output_path}")
    return output_path


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GarbAI PDF Report Generator")
    parser.add_argument(
        "--period",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Report period (default: daily)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PDF file path (default: auto-named in project directory)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  GARB AI  --  PDF REPORT GENERATOR")
    print("=" * 55)

    path = generate_report(period=args.period, output_path=args.output)

    print(f"\nReport generated: {path}")
    print("   Open with any PDF viewer.\n")
