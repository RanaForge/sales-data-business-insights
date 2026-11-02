"""
Shared SalesVision UI kit.

Every page imports its palette, number formats, cards and chart style from
here so the dashboard looks consistent and no page copies styling code.

    from utils import ui
    ui.inject_css()                      # once, in app.py
    ui.kpi_card(...)                     # returns HTML for st.markdown
"""
import html

import numpy as np
import pandas as pd
import streamlit as st

# --------------------------------------------------
# 1. Palette (same brand colours as before, now in one place)
# --------------------------------------------------
NAVY = "#172554"
INK = "#334155"
MUTED = "#64748B"
LINE = "#E2E8F0"
INDIGO = "#4F46E5"
TEAL = "#0F9FA8"
LIGHT_INDIGO = "#A5B4FC"
BLUE = "#0EA5E9"
AMBER = "#F59E0B"
CORAL = "#F97373"

FONT_STACK = "'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif"


# --------------------------------------------------
# 2. Number formats (Indian units)
# --------------------------------------------------
def format_crore(value):
    return f"₹{float(value) / 1e7:,.2f} Cr"


def format_compact_inr(value):
    value = float(value)
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} lakh"
    if abs(value) >= 1e3:
        return f"₹{value / 1e3:.1f}K"
    return f"₹{value:,.0f}"


def format_date(ts):
    """'1 Jun 2024' without %-d, which fails on Windows."""
    ts = pd.Timestamp(ts)
    return f"{ts.day} {ts:%b %Y}"


# --------------------------------------------------
# 3. CSS
# --------------------------------------------------
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

.stApp, .stApp p, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif;
}

/* Page header */
.sv-title {
    font-size: 28px; font-weight: 800; color: #172554;
    letter-spacing: -0.02em; line-height: 1.2; margin: 0;
}
.sv-lead {
    font-size: 15px; color: #475569; line-height: 1.55;
    margin: 6px 0 8px 0; max-width: 80ch;
}

/* Sidebar section label and value */
.sv-side-label {
    font-size: 12.5px; font-weight: 700; color: #CBD5E1;
    margin: 14px 0 2px 0;
}
.sv-side-value { font-size: 13.5px; color: #E2E8F0; margin: 0 0 8px 0; }

/* Sidebar expander: transparent on navy (overrides the light table style) */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background-color: transparent !important;
    padding: 10px 14px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    color: #F8FAFC !important; fill: #F8FAFC !important;
}

/* Sidebar chips: make the selected ones clearly stronger */
[data-testid="stSidebar"] [data-testid="stBaseButton-pillsActive"] {
    background-color: #6366F1 !important;
    border-color: #818CF8 !important;
    color: #FFFFFF !important;
}

/* KPI card */
.sv-kpi {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 16px 18px 10px 18px; height: 100%; box-sizing: border-box;
    display: flex; flex-direction: column; gap: 6px; min-width: 0;
}
.sv-kpi-label { font-size: 13px; font-weight: 600; color: #64748B; }
.sv-kpi-value {
    font-size: clamp(19px, 1.9vw, 30px); font-weight: 800; color: #172554;
    letter-spacing: -0.02em; line-height: 1.15; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
    font-variant-numeric: tabular-nums;
}
.sv-kpi-foot {
    display: flex; align-items: center; flex-wrap: wrap; gap: 2px 8px;
    font-size: 12px; color: #64748B; min-height: 22px;
}
.sv-chip {
    display: inline-flex; align-items: center; padding: 2px 8px;
    border-radius: 999px; font-weight: 700; font-size: 12px;
    white-space: nowrap; font-variant-numeric: tabular-nums;
}
.sv-chip.good { background: #DCFCE7; color: #166534; }
.sv-chip.bad  { background: #FEE2E2; color: #991B1B; }
.sv-chip.flat { background: #F1F5F9; color: #475569; }
.sv-spark { width: 100%; height: 34px; margin-top: 4px; display: block; }

/* Panels (st.container(key="sv_panel_...")) */
[class*="st-key-sv_panel"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 18px 20px 14px 20px; box-sizing: border-box;
}
[class*="st-key-sv_panel"] [data-testid="stPlotlyChart"] {
    border: 0 !important; box-shadow: none !important;
    padding: 0 !important; background: transparent !important;
}
.sv-panel-title { font-size: 16px; font-weight: 700; color: #172554; line-height: 1.3; }
.sv-panel-sub { font-size: 12.5px; color: #64748B; margin-top: 2px; }

/* Insight note */
.sv-insight {
    background: #F1F5F9; border-radius: 10px; padding: 10px 14px;
    font-size: 13.5px; line-height: 1.5; color: #334155;
}
.sv-insight b { color: #172554; }

/* Inline stats */
.sv-stats { display: flex; flex-wrap: wrap; gap: 8px 32px; }
.sv-stat-label { font-size: 12px; color: #64748B; }
.sv-stat-value {
    font-size: 18px; font-weight: 700; color: #172554;
    font-variant-numeric: tabular-nums;
}
.sv-stat-sub { font-size: 12px; color: #64748B; }

/* Order outcomes */
.sv-big {
    font-size: 34px; font-weight: 800; color: #172554;
    letter-spacing: -0.02em; line-height: 1;
}
.sv-big-sub { font-size: 13px; color: #64748B; margin: 4px 0 14px 0; }
.sv-stack {
    display: flex; gap: 2px; height: 12px; border-radius: 999px;
    overflow: hidden; background: #EEF2F7;
}
.sv-stack span { display: block; height: 100%; }
.sv-legend { display: grid; gap: 10px; margin-top: 16px; }
.sv-legend-row {
    display: grid; grid-template-columns: 10px 1fr auto 56px;
    gap: 10px; align-items: center; font-size: 13.5px; color: #334155;
}
.sv-dot { width: 10px; height: 10px; border-radius: 3px; }
.sv-notes {
    display: grid; gap: 6px; margin-top: 16px; padding-top: 14px;
    border-top: 1px solid #E2E8F0; font-size: 13px; color: #475569;
}
.sv-notes b { color: #172554; font-variant-numeric: tabular-nums; }
.sv-num { font-weight: 600; color: #172554; font-variant-numeric: tabular-nums; }
.sv-pct { text-align: right; color: #64748B; font-variant-numeric: tabular-nums; }

/* Ranked bars */
.sv-bars { display: grid; gap: 12px; }
.sv-bar-row {
    display: grid; grid-template-columns: minmax(70px, 110px) 1fr 88px 48px;
    gap: 12px; align-items: center; font-size: 13.5px;
}
.sv-bar-name {
    color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sv-bar-track { height: 10px; background: #EEF2F7; border-radius: 999px; overflow: hidden; }
.sv-bar-fill { height: 100%; border-radius: 999px; }
.sv-bar-val {
    text-align: right; font-weight: 600; color: #172554;
    font-variant-numeric: tabular-nums;
}
.sv-bar-share { text-align: right; color: #64748B; font-variant-numeric: tabular-nums; }

.sv-bars.has-extra .sv-bar-row {
    grid-template-columns: minmax(70px, 110px) 1fr 84px 46px 76px;
}
.sv-bar-extra {
    text-align: right; color: #334155; font-variant-numeric: tabular-nums;
}
.sv-bar-head { font-size: 12px; font-weight: 600; color: #64748B; }
.sv-bar-head .sv-bar-val, .sv-bar-head .sv-bar-share,
.sv-bar-head .sv-bar-extra { color: #64748B; font-weight: 600; }

/* Compact ranked bars: two lines per row, for narrow panels */
.sv-bars.compact { gap: 14px; }
.sv-rank-row { display: grid; gap: 6px; }
.sv-rank-top {
    display: grid; grid-template-columns: 1fr auto 52px;
    gap: 10px; align-items: baseline; font-size: 13.5px;
}

/* Paired bars (two measures per row) */
.sv-pair-legend {
    display: flex; flex-wrap: wrap; gap: 6px 18px;
    font-size: 12px; color: #64748B; margin-bottom: 14px;
}
.sv-pair-legend i {
    display: inline-block; width: 10px; height: 10px;
    border-radius: 3px; margin-right: 6px;
}
.sv-pair { display: grid; gap: 14px; }
.sv-pair-row {
    display: grid; grid-template-columns: minmax(80px, 120px) 1fr 70px;
    gap: 12px; align-items: center; font-size: 13.5px;
}
.sv-pair-bars { display: grid; gap: 2px; }
.sv-pair-bar { height: 10px; border-radius: 999px; }
.sv-pair-vals { text-align: right; font-variant-numeric: tabular-nums; }
.sv-pair-vals span { display: block; font-size: 11.5px; line-height: 11px; height: 11px; }
.sv-pair-vals span:first-child { color: #64748B; margin-bottom: 2px; }
.sv-pair-vals span:last-child { color: #172554; font-weight: 700; }

@media (max-width: 900px) {
    .sv-bar-row { grid-template-columns: 90px 1fr 76px; }
    .sv-bars.has-extra .sv-bar-row { grid-template-columns: 90px 1fr 76px; }
    .sv-bar-share, .sv-bar-extra { display: none; }
}
"""


def inject_css():
    """Inject the shared stylesheet. Call once from app.py."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# --------------------------------------------------
# 4. HTML components
# --------------------------------------------------
def _html(markup):
    """Remove indentation/newlines so Markdown never treats HTML as code."""
    return "".join(line.strip() for line in markup.strip().splitlines())


def esc(value):
    return html.escape(str(value), quote=True)


def page_header(title, lead=""):
    lead_html = f'<div class="sv-lead">{esc(lead)}</div>' if lead else ""
    return _html(f'<div class="sv-title">{esc(title)}</div>{lead_html}')


def panel_title(title, subtitle=""):
    sub = f'<div class="sv-panel-sub">{esc(subtitle)}</div>' if subtitle else ""
    return _html(f'<div class="sv-panel-title">{esc(title)}</div>{sub}')


def sparkline(values, color=INDIGO):
    """Tiny inline SVG trend. A flat series stays visually flat."""
    vals = np.asarray([v for v in values if pd.notna(v)], dtype=float)
    if len(vals) < 3:
        return ""

    mean = abs(vals.mean()) or 1.0
    lo, hi = vals.min(), vals.max()
    span = max(hi - lo, 0.25 * mean)      # do not blow noise up to full height
    mid = (hi + lo) / 2
    lo, hi = mid - span / 2, mid + span / 2

    xs = np.linspace(0, 100, len(vals))
    ys = 28 - (vals - lo) / (hi - lo) * 26
    points = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(xs, ys))
    area = f"0,30 {points} 100,30"

    return (
        '<svg class="sv-spark" viewBox="0 0 100 30" '
        'preserveAspectRatio="none" aria-hidden="true">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.10"/>'
        f'<polyline points="{points}" fill="none" stroke="{color}" '
        'stroke-width="2" stroke-linejoin="round" stroke-linecap="round" '
        'vector-effect="non-scaling-stroke"/></svg>'
    )


def kpi_card(label, value, *, delta_text=None, tone="flat", context="",
             spark=None, color=INDIGO, help="", reserve_space=False):
    """One KPI card. `delta_text` is the change chip, `context` the small note."""
    if delta_text:
        foot = (
            f'<span class="sv-chip {tone}">{esc(delta_text)}</span>'
            f"<span>{esc(context)}</span>"
        )
    else:
        foot = f"<span>{esc(context)}</span>"

    spark_html = sparkline(spark, color) if spark is not None else ""
    if not spark_html and reserve_space:       # keep all cards in a row the same height
        spark_html = '<div class="sv-spark"></div>'
    title_attr = f' title="{esc(help)}"' if help else ""

    return _html(
        f'<div class="sv-kpi"{title_attr}>'
        f'<div class="sv-kpi-label">{esc(label)}</div>'
        f'<div class="sv-kpi-value">{esc(value)}</div>'
        f'<div class="sv-kpi-foot">{foot}</div>'
        f"{spark_html}</div>"
    )


def change_chip(current, previous, *, kind="pct", good_when="up"):
    """Return (chip_text, tone) comparing current with previous."""
    if previous is None or (kind == "pct" and not previous):
        return None, "flat"

    if kind == "pct":
        change = (current - previous) / abs(previous) * 100
        unit = "%"
        digits = 1
    else:                                   # percentage-point change
        change = current - previous
        unit = " pp"
        digits = 2

    if abs(change) < 0.05:
        return f"– 0.0{unit}", "flat"

    arrow = "▲" if change > 0 else "▼"
    is_good = (change > 0) == (good_when == "up")
    return f"{arrow} {abs(change):.{digits}f}{unit}", ("good" if is_good else "bad")


def insight_note(text, lead=""):
    """A short plain-language takeaway shown under a chart."""
    lead_html = f"<b>{esc(lead)}</b> " if lead else ""
    return _html(f'<div class="sv-insight">{lead_html}{esc(text)}</div>')


def stat_row(items):
    """items: list of (label, value, sub) tuples."""
    cells = "".join(
        '<div>'
        f'<div class="sv-stat-label">{esc(label)}</div>'
        f'<div class="sv-stat-value">{esc(value)}</div>'
        f'<div class="sv-stat-sub">{esc(sub)}</div>'
        "</div>"
        for label, value, sub in items
    )
    return _html(f'<div class="sv-stats">{cells}</div>')


def ranked_bars(rows, leader_color=TEAL, other_color=LIGHT_INDIGO,
                highlight=0, headers=None, compact=False):
    """
    rows: (name, amount_text, share_pct, bar_pct) or the same plus a fifth
    `extra_text` shown in its own column.

    highlight: index of the row drawn in the leader colour (None for none).
    headers:   optional (amount_header, share_header[, extra_header]).
    compact:   two lines per row (name, value and share above a full-width
               bar). Use it in narrow panels; the extra column is not shown.
    """
    if compact:
        out = []
        for i, row in enumerate(rows):
            name, amount_text, share, bar_pct = row[:4]
            color = leader_color if i == highlight else other_color
            out.append(
                '<div class="sv-rank-row">'
                '<div class="sv-rank-top">'
                f'<div class="sv-bar-name" title="{esc(name)}">{esc(name)}</div>'
                f'<div class="sv-bar-val">{esc(amount_text)}</div>'
                f'<div class="sv-bar-share">{share:.1f}%</div>'
                "</div>"
                '<div class="sv-bar-track">'
                f'<div class="sv-bar-fill" style="width:{max(bar_pct, 0.8):.2f}%;'
                f'background:{color}"></div></div>'
                "</div>"
            )
        return _html(f'<div class="sv-bars compact">{"".join(out)}</div>')

    has_extra = any(len(r) > 4 for r in rows)

    head = ""
    if headers:
        h = list(headers) + [""] * 3
        extra_head = f'<div class="sv-bar-extra">{esc(h[2])}</div>' if has_extra else ""
        head = (
            '<div class="sv-bar-row sv-bar-head"><div></div><div></div>'
            f'<div class="sv-bar-val">{esc(h[0])}</div>'
            f'<div class="sv-bar-share">{esc(h[1])}</div>{extra_head}</div>'
        )

    out = []
    for i, row in enumerate(rows):
        name, amount_text, share, bar_pct = row[:4]
        color = leader_color if i == highlight else other_color
        extra = (
            f'<div class="sv-bar-extra">{esc(row[4] if len(row) > 4 else "")}</div>'
            if has_extra else ""
        )
        out.append(
            '<div class="sv-bar-row">'
            f'<div class="sv-bar-name" title="{esc(name)}">{esc(name)}</div>'
            '<div class="sv-bar-track">'
            f'<div class="sv-bar-fill" style="width:{max(bar_pct, 0.8):.2f}%;'
            f'background:{color}"></div></div>'
            f'<div class="sv-bar-val">{esc(amount_text)}</div>'
            f'<div class="sv-bar-share">{share:.1f}%</div>'
            f"{extra}</div>"
        )

    cls = "sv-bars has-extra" if has_extra else "sv-bars"
    return _html(f'<div class="{cls}">{head}{"".join(out)}</div>')


def paired_bars(rows, names=("Share of orders", "Share of sales"),
                colors=(LIGHT_INDIGO, TEAL)):
    """
    Two comparable measures per row, for example the share of orders against
    the share of sales. rows: (label, first_pct, second_pct).
    """
    peak = max([max(a, b) for _, a, b in rows] + [1e-9])
    legend = "".join(
        f'<span><i style="background:{c}"></i>{esc(n)}</span>'
        for n, c in zip(names, colors)
    )
    body = "".join(
        '<div class="sv-pair-row">'
        f'<div class="sv-bar-name" title="{esc(label)}">{esc(label)}</div>'
        '<div class="sv-pair-bars">'
        f'<div class="sv-pair-bar" style="width:{max(a / peak * 100, 0.8):.2f}%;background:{colors[0]}"></div>'
        f'<div class="sv-pair-bar" style="width:{max(b / peak * 100, 0.8):.2f}%;background:{colors[1]}"></div>'
        "</div>"
        f'<div class="sv-pair-vals"><span>{a:.1f}%</span><span>{b:.1f}%</span></div>'
        "</div>"
        for label, a, b in rows
    )
    return _html(f'<div class="sv-pair-legend">{legend}</div><div class="sv-pair">{body}</div>')


# --------------------------------------------------
# 5. Plotly style
# --------------------------------------------------
def style_chart(fig, height=340):
    """Apply the shared chart look (transparent, quiet grid, navy tooltips)."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, color=NAVY, size=12),
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=NAVY, font_color="#FFFFFF", font_size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            title_text="", font=dict(size=12, color=INK),
        ),
    )
    fig.update_xaxes(
        showgrid=False, linecolor="#CBD5E1", zeroline=False,
        tickfont=dict(color=MUTED),
    )
    fig.update_yaxes(
        gridcolor="#E8EDF4", zeroline=False, automargin=True,
        tickfont=dict(color=MUTED),
    )
    return fig
