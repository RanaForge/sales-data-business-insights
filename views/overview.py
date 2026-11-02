"""
Overview page.

Layout:
    header (title + one-sentence insight)
    4 KPI cards (value, change vs previous period, weekly sparkline)
    sales trend (daily / weekly / monthly)   |  order outcomes
    sales by category                        |  top states
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import ui
from utils.analytics import (
    WEEK_RULE,
    period_label,
    prepare_sales,
    previous_period_summary,
    summarize,
    weekly_series,
)

STATUS_ORDER = ["delivered", "shipped", "processing", "returned", "cancelled"]
STATUS_COLORS = {
    "delivered": ui.INDIGO,
    "shipped": ui.TEAL,
    "processing": ui.BLUE,
    "returned": ui.CORAL,
    "cancelled": ui.AMBER,
}


# ==================================================
# 1. DATA PREPARATION
# ==================================================
def build_trend(delivered, mode, start, end):
    """Aggregate delivered amounts per day / week / month over [start, end]."""
    days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
    daily = (
        delivered.assign(Day=delivered["Order_Date"].dt.normalize())
        .groupby("Day")["Total_Amount"].sum()
        .reindex(days, fill_value=0.0)
    )

    if mode == "Daily":
        amounts, window = daily, 7
        partial = pd.Series(False, index=amounts.index)
        ma_label = "7-day moving average"
    elif mode == "Weekly":
        amounts, window = daily.resample(**WEEK_RULE).sum(), 4
        partial = (amounts.index < days[0]) | (amounts.index + pd.Timedelta(days=6) > days[-1])
        partial = pd.Series(partial, index=amounts.index)
        ma_label = "4-week moving average"
    else:
        amounts, window = daily.resample("MS").sum(), 3
        month_end = amounts.index + pd.offsets.MonthEnd(0)
        partial = pd.Series((amounts.index < days[0]) | (month_end > days[-1]), index=amounts.index)
        ma_label = "3-month moving average"

    trend = pd.DataFrame({"Period": amounts.index, "Amount": amounts.values, "Partial": partial.values})
    complete = trend["Amount"].where(~trend["Partial"])
    trend["Average"] = complete.rolling(window, min_periods=1).mean()
    return trend, ma_label


# ==================================================
# 2. PAGE HEADER
# ==================================================
def render_header(df, delivered, start, end):
    n_states = df["State"].nunique() if "State" in df.columns else None
    scope = f"{ui.format_date(start)} to {ui.format_date(end)}"
    if n_states:
        scope += f" across {n_states} state{'s' if n_states != 1 else ''}"

    lead = f"Delivered sales for {scope}."

    if "Category" in delivered.columns and not delivered.empty:
        by_cat = delivered.groupby("Category")["Total_Amount"].sum()
        total = by_cat.sum()
        if total > 0:
            lead += f" {by_cat.idxmax()} drives {by_cat.max() / total * 100:.0f}% of it."

    st.markdown(ui.page_header("Business overview", lead), unsafe_allow_html=True)


# ==================================================
# 3. KPI CARDS
# ==================================================
def render_kpis(df, context):
    current = summarize(df)
    previous = previous_period_summary(context)
    weekly = weekly_series(df)

    if previous:
        prev_summary, n_days = previous
        period_text = period_label(n_days)
    else:
        prev_summary, period_text = None, "Weekly trend"

    def chip(key, kind="pct", good_when="up"):
        if prev_summary is None:
            return None, "flat"
        return ui.change_chip(current[key], prev_summary[key], kind=kind, good_when=good_when)

    cards = [
        dict(label="Delivered sales", value=ui.format_crore(current["sales"]),
             chip=chip("sales"), spark=weekly["sales"], color=ui.INDIGO,
             help="Recorded Total_Amount of delivered orders."),
        dict(label="Total orders", value=f"{current['orders']:,}",
             chip=chip("orders"), spark=weekly["orders"], color=ui.INDIGO,
             help="All orders that match the current filters."),
        dict(label="Average order value", value=f"₹{current['aov']:,.0f}",
             chip=chip("aov"), spark=weekly["aov"], color=ui.INDIGO,
             help="Delivered sales divided by delivered orders."),
        dict(label="Return rate", value=f"{current['return_rate']:.2f}%",
             chip=chip("return_rate", kind="pp", good_when="down"),
             spark=weekly["return_rate"], color=ui.CORAL,
             help="Returned orders divided by all filtered orders."),
    ]

    for column, card in zip(st.columns(4, gap="medium"), cards):
        delta_text, tone = card["chip"]
        with column:
            st.markdown(
                ui.kpi_card(
                    card["label"], card["value"],
                    delta_text=delta_text, tone=tone, context=period_text,
                    spark=card["spark"], color=card["color"], help=card["help"],
                ),
                unsafe_allow_html=True,
            )


# ==================================================
# 4. SALES TREND
# ==================================================
def trend_options(days):
    """Only offer granularities that give a meaningful chart for the range."""
    if days < 14:
        return ["Daily"]
    if days < 60:
        return ["Daily", "Weekly"]
    return ["Daily", "Weekly", "Monthly"]


def granularity_picker(days):
    """Segmented control that always fits its column; returns the chosen mode."""
    options = trend_options(days)
    if len(options) == 1:                  # nothing to choose from
        return options[0]

    default = "Daily" if days <= 45 else "Weekly"
    choice = st.segmented_control(
        "Trend granularity",
        options,
        default=default,
        # A different set of options gets its own widget, so an old selection
        # (e.g. "Monthly") never survives into a range that cannot show it.
        key=f"overview_trend_mode_{len(options)}",
        label_visibility="collapsed",
        width="stretch",
    )
    return choice or default


def trend_figure(trend, mode, ma_label, average):
    maximum = float(trend["Amount"].max())
    divisor, unit = (1e7, "Cr") if maximum >= 1e7 else (1e5, "lakh")

    values = trend["Amount"] / divisor
    averages = trend["Average"] / divisor
    series_name = {"Daily": "Daily amount", "Weekly": "Weekly amount", "Monthly": "Monthly amount"}[mode]

    fig = go.Figure()

    # 1) the amounts: pale bars (or a pale line for daily) so the lines on top stay visible
    if mode == "Daily":
        fig.add_trace(go.Scatter(
            x=trend["Period"], y=values, mode="lines", name=series_name,
            line=dict(color=ui.LIGHT_INDIGO, width=1.5),
            hovertemplate=f"₹%{{y:.2f}} {unit}<extra>{series_name}</extra>",
        ))
    else:
        fills = ["#E0E7FF" if p else ui.LIGHT_INDIGO for p in trend["Partial"]]
        outlines = [ui.LIGHT_INDIGO if p else "rgba(0,0,0,0)" for p in trend["Partial"]]
        fig.add_trace(go.Bar(
            x=trend["Period"], y=values, name=series_name,
            marker=dict(color=fills, line=dict(color=outlines, width=1)),
            hovertemplate=f"₹%{{y:.2f}} {unit}<extra>{series_name}</extra>",
        ))

    # 2) moving average
    fig.add_trace(go.Scatter(
        x=trend["Period"], y=averages, mode="lines", name=ma_label,
        line=dict(color=ui.TEAL, width=3),
        hovertemplate=f"₹%{{y:.2f}} {unit}<extra>{ma_label}</extra>",
    ))

    # 3) overall average: a dark dashed line drawn last (on top), with its value in the legend
    fig.add_trace(go.Scatter(
        x=[trend["Period"].min(), trend["Period"].max()],
        y=[average / divisor] * 2,
        mode="lines",
        name=f"Average ₹{average / divisor:.2f} {unit}",
        line=dict(color=ui.NAVY, width=2, dash="dash"),
        hoverinfo="skip",
    ))

    ui.style_chart(fig, height=330)
    fig.update_layout(bargap=0.25)
    span_days = (trend["Period"].max() - trend["Period"].min()).days
    if mode == "Monthly":
        tick_format = "%b %y"
    elif span_days <= 130:                 # short ranges: day + month, so labels never repeat
        tick_format = "%d %b"
    else:
        tick_format = "%b %Y"
    fig.update_xaxes(tickformat=tick_format, nticks=8)
    fig.update_yaxes(title_text=f"₹ {unit}")
    if mode != "Daily":
        fig.update_yaxes(rangemode="tozero")
    return fig


def trend_insight(pool, mode):
    """One plain-language takeaway about how much the amount moves."""
    if len(pool) < 4:
        return None, ""
    average = float(pool["Amount"].mean())
    if average <= 0:
        return None, ""

    low, high = float(pool["Amount"].min()), float(pool["Amount"].max())
    spread = max(high - average, average - low) / average * 100
    adjective, noun = {"Daily": ("Daily", "day"), "Weekly": ("Weekly", "week"), "Monthly": ("Monthly", "month")}[mode]

    text = (
        f"{adjective} sales stayed within ±{spread:.0f}% of the {ui.format_compact_inr(average)} average. "
        f"The lowest {noun} was {ui.format_compact_inr(low)} and the highest {ui.format_compact_inr(high)}."
    )
    lead = "Steady sales." if mode != "Daily" and spread <= 12 else ""
    return lead, text


def show_chart(fig, key):
    """Full-width chart (Streamlit 1.65 stretches charts by default)."""
    st.plotly_chart(fig, key=key, config={"displayModeBar": False})


def render_trend(delivered, start, end):
    with st.container(key="sv_panel_trend"):
        days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
        title_col, picker_col = st.columns([2, 3], vertical_alignment="center")

        with picker_col:
            mode = granularity_picker(days)

        subtitle = {
            "Daily": "Recorded amount per day",
            "Weekly": "Recorded amount per week, weeks start on Monday",
            "Monthly": "Recorded amount per month",
        }[mode]
        with title_col:
            st.markdown(ui.panel_title("Sales trend", subtitle), unsafe_allow_html=True)

        if delivered.empty:
            st.info("No delivered orders match the selected filters.")
            return

        trend, ma_label = build_trend(delivered, mode, start, end)
        pool = trend[~trend["Partial"]]
        if pool.empty:
            pool = trend

        noun = {"Daily": "day", "Weekly": "week", "Monthly": "month"}[mode]
        label_fmt = {"Daily": "%d %b %Y", "Weekly": "Week of %d %b %Y", "Monthly": "%b %Y"}[mode]
        best = pool.loc[pool["Amount"].idxmax()]
        worst = pool.loc[pool["Amount"].idxmin()]
        average = float(pool["Amount"].mean())

        st.markdown(
            ui.stat_row([
                (f"Average per {noun}", ui.format_compact_inr(average), ""),
                (f"Best {noun}", ui.format_compact_inr(best["Amount"]), best["Period"].strftime(label_fmt)),
                (f"Lowest {noun}", ui.format_compact_inr(worst["Amount"]), worst["Period"].strftime(label_fmt)),
            ]),
            unsafe_allow_html=True,
        )

        show_chart(trend_figure(trend, mode, ma_label, average), "overview_trend_chart")

        lead, insight = trend_insight(pool, mode)
        if insight:
            st.markdown(ui.insight_note(insight, lead), unsafe_allow_html=True)

        if trend["Partial"].any() and mode != "Daily":
            st.caption(f"Lighter bars cover only part of a {noun}, so they are left out of the average.")


# ==================================================
# 5. ORDER OUTCOMES
# ==================================================
def render_outcomes(df):
    with st.container(key="sv_panel_outcomes"):
        st.markdown(ui.panel_title("Order outcomes", "Share of all filtered orders"), unsafe_allow_html=True)

        total = len(df)
        if total == 0:
            st.info("No orders match the selected filters.")
            return

        counts = df["Order_Status"].value_counts()
        ordered = [s for s in STATUS_ORDER if s in counts.index]
        ordered += [s for s in counts.index if s not in STATUS_ORDER]

        delivered_share = counts.get("delivered", 0) / total * 100

        segments = "".join(
            f'<span style="width:{counts[s] / total * 100:.3f}%;'
            f'background:{STATUS_COLORS.get(s, "#94A3B8")}"></span>'
            for s in ordered
        )
        rows = "".join(
            '<div class="sv-legend-row">'
            f'<div class="sv-dot" style="background:{STATUS_COLORS.get(s, "#94A3B8")}"></div>'
            f"<div>{ui.esc(s.title())}</div>"
            f'<div class="sv-num">{counts[s]:,}</div>'
            f'<div class="sv-pct">{counts[s] / total * 100:.1f}%</div>'
            "</div>"
            for s in ordered
        )

        in_flight = (counts.get("shipped", 0) + counts.get("processing", 0)) / total * 100
        lost = (counts.get("returned", 0) + counts.get("cancelled", 0)) / total * 100
        notes = ""
        if in_flight:
            notes += f"<div><b>{in_flight:.1f}%</b> still shipped or processing</div>"
        if lost:
            notes += f"<div><b>{lost:.1f}%</b> returned or cancelled</div>"
        notes_html = f'<div class="sv-notes">{notes}</div>' if notes else ""

        st.markdown(
            ui._html(
                f'<div class="sv-big">{delivered_share:.1f}%</div>'
                '<div class="sv-big-sub">of orders delivered</div>'
                f'<div class="sv-stack">{segments}</div>'
                f'<div class="sv-legend">{rows}</div>'
                f"{notes_html}"
            ),
            unsafe_allow_html=True,
        )


# ==================================================
# 6. CATEGORY AND STATE RANKINGS
# ==================================================
def ranked_panel(delivered, column, key, title, subtitle, limit=None):
    with st.container(key=key):
        st.markdown(ui.panel_title(title, subtitle), unsafe_allow_html=True)

        if delivered.empty or column not in delivered.columns:
            st.info("No delivered orders match the selected filters.")
            return

        grouped = (
            delivered.groupby(column)["Total_Amount"].sum()
            .sort_values(ascending=False)
        )
        total = grouped.sum()
        if total <= 0:
            st.info("No delivered amount to rank.")
            return

        shown = grouped.head(limit) if limit else grouped
        top = shown.iloc[0]
        rows = [
            (str(name), ui.format_crore(amount), amount / total * 100, amount / top * 100)
            for name, amount in shown.items()
        ]
        st.markdown(ui.ranked_bars(rows), unsafe_allow_html=True)

        if limit and len(grouped) > limit:
            rest = grouped.iloc[limit:].sum() / total * 100
            st.caption(f"The other {len(grouped) - limit} together make up {rest:.1f}%.")


# ==================================================
# 7. MAIN ENTRY POINT
# ==================================================
def render(sales, customers, products, context=None):
    """
    Render the Overview page.

    `context` is optional and lets the page compare with the previous period:
        {"full_sales": sales, "start": start_date, "end": end_date, "states": selected_states}
    """
    if sales.empty:
        st.warning("No sales records match the selected date and state filters.")
        return

    if not {"Order_Status", "Total_Amount"}.issubset(sales.columns):
        st.error("The sales data must contain Order_Status and Total_Amount.")
        return

    df = prepare_sales(sales)
    delivered = df[df["Order_Status"].eq("delivered")]

    valid_dates = df["Order_Date"].dropna()
    if valid_dates.empty:
        st.warning("No valid order dates were found for the selected filters.")
        return

    start = context["start"] if context and context.get("start") else valid_dates.min()
    end = context["end"] if context and context.get("end") else valid_dates.max()

    render_header(df, delivered, start, end)
    render_kpis(df, context)

    left, right = st.columns([2.1, 1], gap="medium")
    with left:
        render_trend(delivered, start, end)
    with right:
        render_outcomes(df)

    left, right = st.columns(2, gap="medium")
    with left:
        ranked_panel(delivered, "Category", "sv_panel_category",
                     "Sales by category", "Share of delivered sales")
    with right:
        n_categories = delivered["Category"].nunique() if "Category" in delivered.columns else 5
        ranked_panel(delivered, "State", "sv_panel_states",
                     "Top states", "Share of delivered sales",
                     limit=max(5, min(n_categories, 8)))

    st.caption(
        "Amounts are recorded Total Amount from delivered orders, not profit or audited revenue. "
        "Changes compare with the period of equal length before the selected dates."
    )
