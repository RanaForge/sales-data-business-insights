"""
India Sales Map page.

Layout:
    header (title + one-sentence insight)
    4 KPI cards (delivered sales, delivered orders, average order, top state)
    map of India (coloured by sales / orders / average order)  |  state ranking
    state table (collapsed)

Design notes
    * One calm indigo colour scale. A green-to-red scale reads as good-to-bad,
      which is wrong for "how much did this state buy".
    * States with no delivered orders in the current filter are grey, so they
      are never mistaken for "low".
    * Small states such as Delhi are hard to see on a map, so the ranking list
      next to it shows every state.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import ui
from utils.analytics import (
    WEEK_RULE,
    period_label,
    prepare_sales,
    previous_period_slice,
    weekly_series,
)

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "india_states_simplified.geojson"
GEO_NAME_KEY = "NAME_1"

# Dataset state names that differ from the GeoJSON names.
STATE_ALIASES = {
    "UP": "Uttar Pradesh", "MP": "Madhya Pradesh", "MH": "Maharashtra",
    "TN": "Tamil Nadu", "WB": "West Bengal", "KA": "Karnataka",
    "GJ": "Gujarat", "RJ": "Rajasthan", "HR": "Haryana", "PB": "Punjab",
    "DL": "Delhi", "KL": "Kerala", "AP": "Andhra Pradesh", "TS": "Telangana",
    "BR": "Bihar", "OD": "Odisha", "OR": "Odisha", "JH": "Jharkhand",
    "CG": "Chhattisgarh", "UK": "Uttarakhand", "UT": "Uttarakhand",
    "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir", "AS": "Assam",
}

METRICS = ["Sales", "Orders", "Avg order"]
METRIC_COLUMN = {"Sales": "sales", "Orders": "orders", "Avg order": "avg"}

# light -> dark indigo, ending on the dashboard's navy
COLOR_SCALE = [
    [0.00, "#E0E7FF"],
    [0.35, "#A5B4FC"],
    [0.70, "#4F46E5"],
    [1.00, "#172554"],
]
NO_DATA_GREY = "#E5E7EB"

MAP_SUBTITLES = {
    "Sales": "Colour shows delivered sales per state",
    "Orders": "Colour shows delivered orders per state",
    "Avg order": "Colour shows the average delivered order per state",
}


# ==================================================
# 1. DATA
# ==================================================
@st.cache_resource(show_spinner=False)
def load_india_geojson(path):
    """Read the GeoJSON once and share it between reruns (cache_resource avoids a copy)."""
    with open(path, "r", encoding="utf-8") as file:
        geojson = json.load(file)
    names = [
        str(feature.get("properties", {}).get(GEO_NAME_KEY, "")).strip()
        for feature in geojson.get("features", [])
    ]
    return geojson, [n for n in dict.fromkeys(names) if n]


def delivered_with_map_state(df):
    """Delivered orders with a Map_State column matching the GeoJSON names."""
    delivered = df[df["Order_Status"].eq("delivered")].copy()
    delivered["Map_State"] = (
        delivered["State"].astype(str).str.strip().replace(STATE_ALIASES)
    )
    return delivered


def summarize_states(delivered):
    grouped = (
        delivered.groupby("Map_State")["Total_Amount"]
        .agg(sales="sum", orders="size")
        .reset_index()
    )
    grouped["avg"] = grouped["sales"] / grouped["orders"].where(grouped["orders"] > 0)
    grouped["sales_share"] = grouped["sales"] / grouped["sales"].sum() * 100
    grouped["orders_share"] = grouped["orders"] / grouped["orders"].sum() * 100
    return grouped


def delivered_stats(d):
    n = len(d)
    total = float(d["Total_Amount"].sum())
    return {"sales": total, "orders": n, "aov": total / n if n else 0.0}


def weekly_amount(d):
    """Weekly delivered sales of a slice, for a KPI sparkline."""
    series = d.dropna(subset=["Order_Date"]).set_index("Order_Date")["Total_Amount"]
    weekly = series.resample(**WEEK_RULE).sum()
    return weekly.iloc[1:-1] if len(weekly) >= 6 else weekly


# ==================================================
# 2. HEADER AND KPI CARDS
# ==================================================
def top_share_text(summary, column, label, count=3):
    """'UP, Rajasthan and Haryana bring in 38% of delivered sales.'"""
    if len(summary) <= count:
        return None
    top = summary.sort_values(column, ascending=False).head(count)
    share = top[column].sum() / summary[column].sum() * 100
    names = ", ".join(top["Map_State"].tolist()[:-1]) + f" and {top['Map_State'].iloc[-1]}"
    return f"{names} bring in {share:.0f}% of {label}."


def render_header(summary, stats):
    lead = (
        f"Delivered sales of {ui.format_crore(stats['sales'])} across "
        f"{len(summary)} state{'s' if len(summary) != 1 else ''}."
    )
    insight = top_share_text(summary, "sales", "delivered sales")
    if insight:
        lead += " " + insight
    st.markdown(ui.page_header("India sales map", lead), unsafe_allow_html=True)


def render_kpis(delivered, summary, stats, previous, n_days, weekly):
    top = summary.sort_values("sales", ascending=False).iloc[0]
    top_name = top["Map_State"]
    top_spark = weekly_amount(delivered[delivered["Map_State"] == top_name])
    period_text = period_label(n_days) if previous else "Weekly trend"

    cards = [
        dict(label="Delivered sales", value=ui.format_crore(stats["sales"]),
             key="sales", spark=weekly["sales"], context=None,
             help="Recorded Total_Amount of delivered orders."),
        dict(label="Delivered orders", value=f"{stats['orders']:,}",
             key="orders", spark=weekly["delivered_n"], context=None,
             help="Orders with status Delivered."),
        dict(label="Average order", value=f"₹{stats['aov']:,.0f}",
             key="aov", spark=weekly["aov"], context=None,
             help="Delivered sales divided by delivered orders."),
        dict(label="Top state", value=str(top_name), key=None, spark=top_spark,
             context=f"{top['sales_share']:.1f}% of delivered sales",
             help="State with the highest delivered sales."),
    ]

    for column, card in zip(st.columns(4, gap="medium"), cards):
        delta_text, tone = None, "flat"
        if previous and card["key"]:
            delta_text, tone = ui.change_chip(stats[card["key"]], previous[card["key"]])
        with column:
            st.markdown(
                ui.kpi_card(
                    card["label"], card["value"],
                    delta_text=delta_text, tone=tone,
                    context=card["context"] or period_text,
                    spark=card["spark"], help=card["help"],
                ),
                unsafe_allow_html=True,
            )


# ==================================================
# 3. MAP
# ==================================================
def tick_text(metric, value):
    if metric == "Sales":
        return f"₹{value / 1e7:.1f} Cr" if value >= 1e7 else ui.format_compact_inr(value)
    if metric == "Orders":
        return f"{value / 1000:.1f}K" if value >= 1000 else f"{value:,.0f}"
    return ui.format_compact_inr(value)


def build_map(geojson, geo_names, summary, metric):
    column = METRIC_COLUMN[metric]
    values = summary[column].astype(float)

    zmin, zmax = float(values.min()), float(values.max())
    if zmax <= zmin:                       # one state, or all equal
        zmin = 0.0
        zmax = zmax if zmax > 0 else 1.0
    tickvals = np.linspace(zmin, zmax, 5)

    hover = np.array([
        [ui.format_crore(r.sales), f"{int(r.orders):,}",
         f"₹{r.avg:,.0f}", f"{r.sales_share:.1f}%"]
        for r in summary.itertuples()
    ])

    with_data = set(summary["Map_State"])
    no_data = [name for name in geo_names if name not in with_data]

    fig = go.Figure()

    if no_data:                            # grey: not in the current filter
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey=f"properties.{GEO_NAME_KEY}",
            locations=no_data, z=[0] * len(no_data),
            colorscale=[[0, NO_DATA_GREY], [1, NO_DATA_GREY]],
            showscale=False,
            marker_line_color="#FFFFFF", marker_line_width=0.8,
            hovertemplate="<b>%{location}</b><br>No delivered orders in this filter<extra></extra>",
        ))

    fig.add_trace(go.Choropleth(
        geojson=geojson, featureidkey=f"properties.{GEO_NAME_KEY}",
        locations=summary["Map_State"], z=values, zmin=zmin, zmax=zmax,
        colorscale=COLOR_SCALE,
        customdata=hover,
        marker_line_color="#FFFFFF", marker_line_width=0.8,
        colorbar=dict(
            orientation="h", thickness=10, len=0.55,
            x=0.5, xanchor="center", y=-0.02, yanchor="top",
            outlinewidth=0,
            tickvals=tickvals,
            ticktext=[tick_text(metric, v) for v in tickvals],
            tickfont=dict(size=11, color=ui.MUTED),
        ),
        hovertemplate=(
            "<b>%{location}</b><br>"
            "Delivered sales: %{customdata[0]}<br>"
            "Delivered orders: %{customdata[1]}<br>"
            "Average order: %{customdata[2]}<br>"
            "Share of sales: %{customdata[3]}<extra></extra>"
        ),
    ))

    fig.update_geos(
        fitbounds="locations", visible=False,
        showcountries=False, showcoastlines=False, showland=False,
        showframe=False, bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        height=540,
        margin=dict(l=0, r=0, t=0, b=56),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=ui.FONT_STACK, color=ui.NAVY, size=12),
        hoverlabel=dict(bgcolor=ui.NAVY, font_color="#FFFFFF", font_size=12),
        dragmode=False,
    )
    return fig


def metric_picker():
    return st.segmented_control(
        "Colour states by", METRICS, default="Sales",
        key="map_metric", label_visibility="collapsed", width="stretch",
    ) or "Sales"


def render_map_body(metric, summary):
    """The map itself (the panel title and picker are drawn by render())."""
    try:
        geojson, geo_names = load_india_geojson(str(GEOJSON_PATH))
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"The map file could not be read: {exc}")
        return
    if not geo_names:
        st.error("The map file has no state names.")
        return

    st.plotly_chart(
        build_map(geojson, geo_names, summary, metric),
        key="india_map",
        config={"displayModeBar": False, "scrollZoom": False, "responsive": True},
    )

    unmatched_names = sorted(set(summary["Map_State"]) - set(geo_names))
    if unmatched_names:
        st.warning(
            "These states in the sales data did not match the map: "
            + ", ".join(unmatched_names)
        )


# ==================================================
# 4. RANKING
# ==================================================
def ranking_rows(summary, metric):
    column = METRIC_COLUMN[metric]
    ordered = summary.sort_values(column, ascending=False)
    top = float(ordered[column].iloc[0]) or 1.0

    rows = []
    for r in ordered.itertuples():
        if metric == "Sales":
            value, share, extra = ui.format_crore(r.sales), r.sales_share, ui.format_compact_inr(r.avg)
        elif metric == "Orders":
            value, share, extra = f"{int(r.orders):,}", r.orders_share, ui.format_crore(r.sales)
        else:
            value, share, extra = ui.format_compact_inr(r.avg), r.sales_share, f"{int(r.orders):,}"
        rows.append((r.Map_State, value, share, float(getattr(r, column)) / top * 100, extra))
    return rows


def ranking_insight(summary, metric):
    if len(summary) < 2:
        return None
    if metric == "Sales":
        return top_share_text(summary, "sales", "delivered sales")
    if metric == "Orders":
        return top_share_text(summary, "orders", "delivered orders")

    low = summary.loc[summary["avg"].idxmin()]
    high = summary.loc[summary["avg"].idxmax()]
    spread = (high["avg"] - low["avg"]) / low["avg"] * 100 if low["avg"] else 0
    text = (
        f"Average order ranges from {ui.format_compact_inr(low['avg'])} ({low['Map_State']}) "
        f"to {ui.format_compact_inr(high['avg'])} ({high['Map_State']})"
    )
    return text + (", a spread of under 10%." if spread < 10 else f", a spread of {spread:.0f}%.")


def render_ranking_panel(metric, summary):
    subtitle = {
        "Sales": "Share of delivered sales",
        "Orders": "Share of delivered orders",
        "Avg order": "Share shown is of delivered sales",
    }[metric]
    st.markdown(ui.panel_title("State ranking", subtitle), unsafe_allow_html=True)
    st.markdown(ui.ranked_bars(ranking_rows(summary, metric), compact=True), unsafe_allow_html=True)

    insight = ranking_insight(summary, metric)
    if insight:
        st.markdown(ui.insight_note(insight), unsafe_allow_html=True)


# ==================================================
# 5. TABLE
# ==================================================
def render_table(summary):
    with st.expander("View the state table", expanded=False):
        table = summary.sort_values("sales", ascending=False).copy()
        table["sales_cr"] = table["sales"] / 1e7
        table = table[["Map_State", "sales_cr", "sales_share", "orders", "avg"]]

        st.dataframe(
            table,
            column_config={
                "Map_State": st.column_config.TextColumn("State"),
                "sales_cr": st.column_config.NumberColumn("Delivered sales", format="₹%.2f Cr"),
                "sales_share": st.column_config.ProgressColumn(
                    "Share of sales", format="%.1f%%", min_value=0,
                    max_value=float(max(table["sales_share"].max(), 1)),
                ),
                "orders": st.column_config.NumberColumn("Delivered orders", format="%d"),
                "avg": st.column_config.NumberColumn("Average order", format="₹%.0f"),
            },
            hide_index=True,
            width="stretch",
        )


# ==================================================
# 6. MAIN ENTRY POINT
# ==================================================
def render(sales, customers, products, context=None):
    """
    Render the India Sales Map page.

    `context` lets the KPI cards compare with the previous period:
        {"full_sales": sales, "start": start_date, "end": end_date, "states": selected_states}
    """
    required = {"State", "Order_Status", "Total_Amount"}
    missing = required - set(sales.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(sorted(missing))}")
        return
    if sales.empty:
        st.warning("No records match the selected dashboard filters.")
        return

    df = prepare_sales(sales)
    delivered = delivered_with_map_state(df)
    if delivered.empty:
        st.warning("No delivered orders match the selected filters.")
        return

    summary = summarize_states(delivered)
    stats = delivered_stats(delivered)

    previous_stats, n_days = None, 0
    previous = previous_period_slice(context)
    if previous:
        raw_rows, n_days = previous
        previous_delivered = delivered_with_map_state(prepare_sales(raw_rows))
        if not previous_delivered.empty:
            previous_stats = delivered_stats(previous_delivered)

    render_header(summary, stats)
    render_kpis(delivered, summary, stats, previous_stats, n_days, weekly_series(df))

    left, right = st.columns([5, 3], gap="medium")
    with left:
        with st.container(key="sv_panel_map"):
            title_col, picker_col = st.columns([1, 1], vertical_alignment="center")
            with picker_col:
                metric = metric_picker()
            with title_col:
                st.markdown(
                    ui.panel_title("Sales by state", MAP_SUBTITLES[metric]),
                    unsafe_allow_html=True,
                )
            render_map_body(metric, summary)
    with right:
        with st.container(key="sv_panel_ranking"):
            render_ranking_panel(metric, summary)

    render_table(summary)

    st.caption(
        "Delivered orders only. Amounts are recorded Total Amount, not profit. "
        "Colours run from the lowest to the highest state in the current filter. "
        "Grey states have no delivered orders in it."
    )
