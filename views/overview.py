
import pandas as pd
import plotly.express as px
import streamlit as st


# ==================================================
# 1. SALESVISION THEME
# ==================================================
NAVY = "#172554"
INDIGO = "#4F46E5"
TEAL = "#0F9FA8"
LIGHT_INDIGO = "#A5B4FC"
CORAL = "#F97373"
AMBER = "#F59E0B"
BLUE = "#0EA5E9"

CHART_COLORS = [
    INDIGO, TEAL, BLUE, AMBER, CORAL, "#8B5CF6", "#14B8A6"
]


# ==================================================
# 2. PAGE-SPECIFIC CSS
# ==================================================
def apply_overview_styles():
    """Style KPI values so they remain visible in narrow columns."""

    st.markdown(
        """
        <style>
        /* Keep KPI labels readable */
        div[data-testid="stMetricLabel"] {
            font-size: 13px !important;
            line-height: 1.4 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        /* Prevent metric values from being clipped */
        div[data-testid="stMetricValue"] {
            font-size: clamp(18px, 1.6vw, 28px) !important;
            line-height: 1.3 !important;
            white-space: normal !important;
            overflow: visible !important;
            overflow-wrap: anywhere !important;
            word-break: normal !important;
        }

        div[data-testid="stMetric"] {
            min-width: 0 !important;
            height: 100%;
            padding: 16px !important;
            box-sizing: border-box !important;
        }

        /* Consistent chart panels */
        div[data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================
# 3. CHART STYLING
# ==================================================
def style_chart(fig, height=380):
    """Apply the shared SalesVision chart appearance."""

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            color=NAVY,
            size=12,
        ),
        margin=dict(l=20, r=25, t=65, b=35),
        height=height,
        hoverlabel=dict(
            bgcolor=NAVY,
            font_color="#FFFFFF",
            font_size=12,
        ),
        legend=dict(
            title_text="",
            font=dict(color=NAVY, size=11),
            bgcolor="rgba(255,255,255,0)",
        ),
    )

    fig.update_xaxes(
        gridcolor="#E8EDF4",
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        title_font=dict(color=NAVY),
        zeroline=False,
    )

    fig.update_yaxes(
        gridcolor="#E8EDF4",
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        title_font=dict(color=NAVY),
        zeroline=False,
    )

    return fig


# ==================================================
# 4. INR FORMATTING
# ==================================================
def format_inr(value):
    """Format an amount in Indian rupees."""

    return f"₹{value:,.2f}"


def format_crore(value):
    """Convert rupees to crore."""

    return f"₹{value / 1e7:,.2f} Cr"


def format_compact_inr(value):
    """Compact INR values for dashboard KPI cards."""

    value = float(value)

    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"

    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} lakh"

    if abs(value) >= 1e3:
        return f"₹{value / 1e3:.1f} K"

    return f"₹{value:,.0f}"


# ==================================================
# 5. PREPARE DATA
# ==================================================
def prepare_sales(sales):
    """Normalize the columns used by the Overview page."""

    df = sales.copy()

    if "Order_Status" in df.columns:
        df["Order_Status"] = (
            df["Order_Status"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    if "Total_Amount" in df.columns:
        df["Total_Amount"] = pd.to_numeric(
            df["Total_Amount"],
            errors="coerce",
        ).fillna(0)

    if "Order_Date" in df.columns:
        df["Order_Date"] = pd.to_datetime(
            df["Order_Date"],
            errors="coerce",
        )

    if "Category" in df.columns:
        df["Category"] = (
            df["Category"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )

    return df


# ==================================================
# 6. SALES TREND
# ==================================================
def render_sales_trend(delivered):
    """Render daily/monthly recorded amounts and highlights."""

    st.markdown("### Sales Trend")

    trend_mode = st.radio(
        "Trend frequency",
        options=["Daily", "Monthly"],
        horizontal=True,
        key="overview_sales_trend_mode",
    )

    if delivered.empty:
        st.info("No delivered sales match the selected filters.")
        return

    source = delivered.dropna(subset=["Order_Date"]).copy()

    if source.empty:
        st.info("No valid order dates are available.")
        return

    # --------------------------------------------------
    # DAILY AGGREGATION
    # --------------------------------------------------
    if trend_mode == "Daily":
        source["Period"] = source["Order_Date"].dt.normalize()

        trend = (
            source.groupby("Period", as_index=False)
            .agg(Total_Amount=("Total_Amount", "sum"))
            .sort_values("Period")
        )

        all_periods = pd.date_range(
            start=trend["Period"].min(),
            end=trend["Period"].max(),
            freq="D",
        )

        trend = (
            trend.set_index("Period")
            .reindex(all_periods, fill_value=0)
            .rename_axis("Period")
            .reset_index()
        )

        trend["Moving_Average"] = (
            trend["Total_Amount"]
            .rolling(window=7, min_periods=1)
            .mean()
        )

        average_label = "Average Daily Amount"
        highest_label = "Highest-Sales Day"
        lowest_label = "Lowest-Sales Day"
        moving_label = "7-Day Moving Average"
        average_value = format_compact_inr(
            trend["Total_Amount"].mean()
        )

        period_format = "%d %b %Y"
        axis_format = "%b %d\n%Y"

    # --------------------------------------------------
    # MONTHLY AGGREGATION
    # --------------------------------------------------
    else:
        source["Period"] = (
            source["Order_Date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

        trend = (
            source.groupby("Period", as_index=False)
            .agg(Total_Amount=("Total_Amount", "sum"))
            .sort_values("Period")
        )

        all_periods = pd.date_range(
            start=trend["Period"].min(),
            end=trend["Period"].max(),
            freq="MS",
        )

        trend = (
            trend.set_index("Period")
            .reindex(all_periods, fill_value=0)
            .rename_axis("Period")
            .reset_index()
        )

        trend["Moving_Average"] = (
            trend["Total_Amount"]
            .rolling(window=3, min_periods=1)
            .mean()
        )

        average_label = "Average Monthly Amount"
        highest_label = "Highest-Sales Month"
        lowest_label = "Lowest-Sales Month"
        moving_label = "3-Month Moving Average"
        average_value = format_compact_inr(
            trend["Total_Amount"].mean()
        )

        period_format = "%b %Y"
        axis_format = "%b %Y"

    if trend.empty:
        st.info("No trend data is available.")
        return

    # --------------------------------------------------
    # FIND HIGHEST AND LOWEST PERIODS
    # --------------------------------------------------
    highest_row = trend.loc[trend["Total_Amount"].idxmax()]
    lowest_row = trend.loc[trend["Total_Amount"].idxmin()]

    highest_date = pd.Timestamp(highest_row["Period"])
    lowest_date = pd.Timestamp(lowest_row["Period"])

    highest_text = highest_date.strftime(period_format)
    lowest_text = lowest_date.strftime(period_format)

    # --------------------------------------------------
    # RESPONSIVE KPI CARDS
    # Use custom HTML to avoid Streamlit metric truncation.
    # --------------------------------------------------
    st.markdown("#### Trend Highlights")

    k1, k2, k3 = st.columns([1.1, 1, 1], gap="small")

    with k1:
        st.markdown(
            f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:16px;
                padding:18px 16px;
                min-height:112px;
                box-sizing:border-box;
                box-shadow:0 4px 16px rgba(30,41,59,0.05);
            ">
                <div style="
                    color:#475569;
                    font-size:13px;
                    line-height:1.4;
                    margin-bottom:12px;
                ">{average_label}</div>
                <div style="
                    color:{NAVY};
                    font-size:clamp(18px,1.6vw,27px);
                    font-weight:750;
                    line-height:1.3;
                    overflow-wrap:anywhere;
                ">{average_value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:16px;
                padding:18px 16px;
                min-height:112px;
                box-sizing:border-box;
                box-shadow:0 4px 16px rgba(30,41,59,0.05);
            ">
                <div style="
                    color:#475569;
                    font-size:13px;
                    line-height:1.4;
                    margin-bottom:12px;
                ">{highest_label}</div>
                <div style="
                    color:{NAVY};
                    font-size:clamp(17px,1.4vw,24px);
                    font-weight:750;
                    line-height:1.3;
                    overflow-wrap:anywhere;
                ">{highest_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Amount: {format_compact_inr(highest_row['Total_Amount'])}"
        )

    with k3:
        st.markdown(
            f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:16px;
                padding:18px 16px;
                min-height:112px;
                box-sizing:border-box;
                box-shadow:0 4px 16px rgba(30,41,59,0.05);
            ">
                <div style="
                    color:#475569;
                    font-size:13px;
                    line-height:1.4;
                    margin-bottom:12px;
                ">{lowest_label}</div>
                <div style="
                    color:{NAVY};
                    font-size:clamp(17px,1.4vw,24px);
                    font-weight:750;
                    line-height:1.3;
                    overflow-wrap:anywhere;
                ">{lowest_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Amount: {format_compact_inr(lowest_row['Total_Amount'])}"
        )

    # --------------------------------------------------
    # TREND CHART
    # --------------------------------------------------
    fig = px.line(
        trend,
        x="Period",
        y=["Total_Amount", "Moving_Average"],
        color_discrete_map={
            "Total_Amount": LIGHT_INDIGO,
            "Moving_Average": TEAL,
        },
        labels={
            "Period": "Order Date",
            "value": "Recorded Amount (₹)",
            "variable": "Series",
        },
    )

    fig.update_traces(
        selector=dict(name="Total_Amount"),
        name=(
            "Daily Recorded Amount"
            if trend_mode == "Daily"
            else "Monthly Recorded Amount"
        ),
        line=dict(color=LIGHT_INDIGO, width=2),
        hovertemplate=(
            "Period: %{x|%d %b %Y}"
            "<br>Recorded amount: ₹%{y:,.2f}"
            "<extra></extra>"
        ),
    )

    fig.update_traces(
        selector=dict(name="Moving_Average"),
        name=moving_label,
        line=dict(color=TEAL, width=3.5),
        hovertemplate=(
            "Period: %{x|%d %b %Y}"
            "<br>Moving average: ₹%{y:,.2f}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )

    fig.update_yaxes(
        title="Recorded Amount (₹)",
        tickformat="~s",
    )

    fig.update_xaxes(
        title="Order Date",
        nticks=9,
        tickformat=axis_format,
    )

    style_chart(fig, height=400)

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="overview_sales_trend_chart",
    )

    st.caption(
        f"Legend: the lighter line shows recorded amounts; "
        f"the teal line shows the {moving_label.lower()}. "
        "Amounts are recorded Total Amount, not profit."
    )


# ==================================================
# 7. ORDER STATUS DONUT
# ==================================================
def render_order_status(sales):
    """Display the distribution of all filtered orders."""

    st.markdown("### Order Status")

    if sales.empty:
        st.info("No order status data is available.")
        return

    status_data = (
        sales["Order_Status"]
        .fillna("unknown")
        .astype(str)
        .str.strip()
        .str.title()
        .value_counts()
        .rename_axis("Order Status")
        .reset_index(name="Orders")
    )

    status_colors = {
        "Delivered": INDIGO,
        "Processing": BLUE,
        "Shipped": TEAL,
        "Cancelled": AMBER,
        "Returned": CORAL,
        "Unknown": "#94A3B8",
    }

    fig = px.pie(
        status_data,
        names="Order Status",
        values="Orders",
        hole=0.62,
        color="Order Status",
        color_discrete_map=status_colors,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        textfont=dict(color="#FFFFFF", size=12),
        hovertemplate=(
            "Status: %{label}"
            "<br>Orders: %{value:,}"
            "<br>Share: %{percent}"
            "<extra></extra>"
        ),
    )

    total_orders = int(status_data["Orders"].sum())

    fig.update_layout(
        showlegend=True,
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color=NAVY),
        ),
        margin=dict(l=10, r=10, t=65, b=15),
        annotations=[
            dict(
                text=(
                    f"<b>{total_orders:,}</b>"
                    "<br><span style='font-size:12px'>Orders</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20, color=NAVY),
            )
        ],
    )

    style_chart(fig, height=400)

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="overview_order_status_chart",
    )

    st.caption(
        "Order counts and percentages are based on all filtered orders."
    )


# ==================================================
# 8. CATEGORY SALES CHART
# ==================================================
def render_category_sales(delivered):
    """Compare recorded delivered amounts by category."""

    st.markdown("### Delivered Sales by Product Category")

    if delivered.empty or "Category" not in delivered.columns:
        st.info("No category sales data is available.")
        return

    category_data = (
        delivered.groupby("Category", dropna=False)
        .agg(Total_Amount=("Total_Amount", "sum"))
        .reset_index()
    )

    category_data["Category"] = (
        category_data["Category"]
        .fillna("Unknown")
        .astype(str)
    )

    category_data = category_data.sort_values(
        "Total_Amount",
        ascending=True,
    )

    if category_data.empty:
        st.info("No category sales data is available.")
        return

    total_amount = category_data["Total_Amount"].sum()

    category_data["Sales_Cr"] = (
        category_data["Total_Amount"] / 1e7
    )

    category_data["Sales_Share"] = (
        category_data["Total_Amount"] / total_amount * 100
        if total_amount
        else 0
    )

    top_category = category_data.loc[
        category_data["Total_Amount"].idxmax(),
        "Category",
    ]

    category_data["Bar_Color"] = category_data["Category"].apply(
        lambda category: (
            "Leading category"
            if category == top_category
            else "Other categories"
        )
    )

    fig = px.bar(
        category_data,
        x="Sales_Cr",
        y="Category",
        orientation="h",
        color="Bar_Color",
        color_discrete_map={
            "Leading category": TEAL,
            "Other categories": LIGHT_INDIGO,
        },
        custom_data=["Total_Amount", "Sales_Share"],
        labels={
            "Sales_Cr": "Delivered Sales (₹ Cr)",
            "Category": "",
            "Bar_Color": "",
        },
    )

    fig.update_traces(
        texttemplate="₹%{x:.2f} Cr",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b>"
            "<br>Recorded amount: ₹%{customdata[0]:,.2f}"
            "<br>Share of delivered amount: %{customdata[1]:.2f}%"
            "<extra></extra>"
        ),
    )

    max_sales = max(category_data["Sales_Cr"].max(), 0)

    fig.update_layout(
        margin=dict(l=20, r=100, t=20, b=45),
        showlegend=False,
    )

    fig.update_xaxes(
        title="Delivered Sales (₹ Cr)",
        range=[0, max_sales * 1.20 if max_sales > 0 else 1],
        tickformat=".0f",
    )

    fig.update_yaxes(
        title="",
        categoryorder="total ascending",
    )

    style_chart(fig, height=360)

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="overview_category_sales_chart",
    )

    st.caption(
        "Teal highlights the leading category. "
        "Amounts represent recorded Total Amount, not profit."
    )


# ==================================================
# 9. MAIN OVERVIEW PAGE
# ==================================================
def render(sales, customers, products):
    """Render the complete SalesVision Overview dashboard."""

    apply_overview_styles()

    st.markdown("## Business Performance")

    st.caption(
        "Monitor recorded order amounts, delivery performance, "
        "order status and product category performance."
    )

    if sales.empty:
        st.warning(
            "No sales records match the selected date and state filters."
        )
        return

    df = prepare_sales(sales)

    required_columns = {"Order_Status", "Total_Amount"}

    if not required_columns.issubset(df.columns):
        st.error(
            "The sales data must contain Order_Status and Total_Amount."
        )
        return

    # --------------------------------------------------
    # TOP KPI CALCULATIONS
    # --------------------------------------------------
    total_orders = len(df)

    status = df["Order_Status"]

    delivered = df[status == "delivered"].copy()

    delivered_orders = len(delivered)
    delivered_amount = delivered["Total_Amount"].sum()

    delivery_rate = (
        delivered_orders / total_orders * 100
        if total_orders
        else 0
    )

    return_rate = (
        status.eq("returned").sum() / total_orders * 100
        if total_orders
        else 0
    )

    # --------------------------------------------------
    # BUSINESS PERFORMANCE CARDS
    # --------------------------------------------------
    st.markdown("### Key Performance Indicators")

    c1, c2, c3, c4 = st.columns(4, gap="medium")

    c1.metric(
        "Delivered Sales Amount",
        format_crore(delivered_amount),
        help="Recorded Total_Amount for delivered orders.",
    )

    c2.metric(
        "Total Orders",
        f"{total_orders:,}",
        help="All orders matching the current dashboard filters.",
    )

    c3.metric(
        "Order Delivery Rate",
        f"{delivery_rate:.2f}%",
        help="Delivered orders divided by all filtered orders.",
    )

    c4.metric(
        "Order Return Rate",
        f"{return_rate:.2f}%",
        help="Returned orders divided by all filtered orders.",
    )

    st.caption(
        "Amounts represent recorded Total Amount. "
        "They are not profit or verified accounting revenue."
    )

    st.divider()

    # --------------------------------------------------
    # TREND + ORDER STATUS
    # --------------------------------------------------
    left, right = st.columns([1.65, 1], gap="large")

    with left:
        render_sales_trend(delivered)

    with right:
        render_order_status(df)

    st.divider()

    # --------------------------------------------------
    # CATEGORY SALES
    # --------------------------------------------------
    render_category_sales(delivered)
