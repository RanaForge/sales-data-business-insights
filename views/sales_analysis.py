
import pandas as pd
import plotly.express as px
import streamlit as st

# ==================================================
# 1. SALESVISION COLORS
# ==================================================
NAVY = "#172554"
INDIGO = "#4F46E5"
TEAL = "#0F9FA8"
LIGHT_INDIGO = "#A5B4FC"
CORAL = "#F97373"
AMBER = "#F59E0B"
BLUE = "#0EA5E9"
SLATE = "#64748B"

CHART_COLORS = [INDIGO, TEAL, BLUE, AMBER, CORAL, "#8B5CF6", "#14B8A6"]


# ==================================================
# 2. SHARED CHART STYLING
# ==================================================
def style_chart(fig, height=380):
    """Apply a consistent SalesVision chart theme."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, sans-serif", color=NAVY, size=12),
        margin=dict(l=25, r=35, t=65, b=40),
        height=height,
        hoverlabel=dict(bgcolor=NAVY, font_color="#FFFFFF", font_size=12),
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
# 3. FORMATTING HELPERS
# ==================================================
def format_inr(value):
    return f"₹{float(value):,.2f}"


def format_crore(value):
    return f"₹{float(value) / 1e7:.2f} Cr"


def format_compact_inr(value):
    """Format amounts compactly for KPI cards."""
    value = float(value)

    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} lakh"
    if abs(value) >= 1e3:
        return f"₹{value / 1e3:.1f} K"

    return f"₹{value:,.0f}"


# ==================================================
# 4. DATA PREPARATION
# ==================================================
def prepare_sales(sales):
    """Prepare a copy of the filtered sales data."""
    df = sales.copy()

    if "Order_Date" in df.columns:
        df["Order_Date"] = pd.to_datetime(
            df["Order_Date"], errors="coerce"
        )

    if "Total_Amount" in df.columns:
        df["Total_Amount"] = pd.to_numeric(
            df["Total_Amount"], errors="coerce"
        )

    if "Order_Status" in df.columns:
        df["Order_Status"] = (
            df["Order_Status"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .str.title()
        )

    for column in ["Category", "Payment_Mode", "State"]:
        if column in df.columns:
            df[column] = (
                df[column]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
                .replace("", "Unknown")
            )

    return df


# ==================================================
# 5. RENDER SALES ANALYSIS
# ==================================================
def render(sales, customers, products):
    """Render the interactive Sales Analysis page."""

    st.markdown("## Sales Analysis")
    st.caption(
        "Explore recorded order amounts, category performance, "
        "payment preferences and state-level comparisons."
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
            "Sales data must contain Order_Status and Total_Amount."
        )
        return

    # --------------------------------------------------
    # Selected date range
    # --------------------------------------------------
    if "Order_Date" in df.columns:
        valid_dates = df["Order_Date"].dropna()
        if not valid_dates.empty:
            st.caption(
                f"Showing data from {valid_dates.min():%d %b %Y} "
                f"to {valid_dates.max():%d %b %Y}"
            )

    # ==================================================
    # 6. SALES PERFORMANCE KPIs
    # ==================================================
    total_orders = len(df)
    total_amount = df["Total_Amount"].sum()
    average_order_amount = (
        total_amount / total_orders if total_orders else 0
    )

    cancelled_orders = df["Order_Status"].eq("Cancelled").sum()
    cancellation_rate = (
        cancelled_orders / total_orders * 100 if total_orders else 0
    )

    st.markdown("### Sales Performance")
    k1, k2, k3, k4 = st.columns(4, gap="medium")

    k1.metric("Total Orders", f"{total_orders:,}")
    k2.metric(
        "Recorded Order Amount",
        format_crore(total_amount),
        help="Sum of recorded Total_Amount for the filtered records.",
    )
    k3.metric(
        "Average Order Amount",
        format_compact_inr(average_order_amount),
        help="Recorded order amount divided by the number of orders.",
    )
    k4.metric("Cancellation Rate", f"{cancellation_rate:.2f}%")

    st.caption(
        "Recorded order amounts are based on Total Amount. "
        "They are not profit or verified accounting revenue."
    )
    st.divider()

    # ==================================================
    # 7. DAILY / MONTHLY SALES TREND
    # ==================================================
    st.markdown("### Sales Trend")

    trend_mode = st.radio(
        "Trend frequency",
        options=["Daily", "Monthly"],
        horizontal=True,
        key="sales_analysis_trend_frequency",
    )

    if "Order_Date" in df.columns:
        trend_source = df.dropna(subset=["Order_Date"]).copy()

        if not trend_source.empty:
            if trend_mode == "Daily":
                trend_source["Period"] = (
                    trend_source["Order_Date"].dt.normalize()
                )
                moving_window = 7
                moving_label = "7-Day Moving Average"
                date_format = "%b %d\n%Y"
                period_format = "%d %b %Y"
            else:
                trend_source["Period"] = (
                    trend_source["Order_Date"]
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )
                moving_window = 3
                moving_label = "3-Month Moving Average"
                date_format = "%b %Y"
                period_format = "%b %Y"

            order_count_column = (
                "Order_ID"
                if "Order_ID" in trend_source.columns
                else "Total_Amount"
            )

            trend = (
                trend_source.groupby("Period", as_index=False)
                .agg(
                    Total_Amount=("Total_Amount", "sum"),
                    Orders=(order_count_column, "count"),
                )
                .sort_values("Period")
            )

            frequency = "D" if trend_mode == "Daily" else "MS"
            complete_periods = pd.date_range(
                start=trend["Period"].min(),
                end=trend["Period"].max(),
                freq=frequency,
            )

            trend = (
                trend.set_index("Period")
                .reindex(complete_periods, fill_value=0)
                .rename_axis("Period")
                .reset_index()
            )

            trend["Moving_Average"] = (
                trend["Total_Amount"]
                .rolling(moving_window, min_periods=1)
                .mean()
            )

            highest = trend.loc[trend["Total_Amount"].idxmax()]
            lowest = trend.loc[trend["Total_Amount"].idxmin()]

            st.markdown("#### Trend Highlights")
            c1, c2, c3 = st.columns(3, gap="small")

            c1.metric(
                f"Average {trend_mode} Amount",
                format_compact_inr(trend["Total_Amount"].mean()),
            )
            c2.metric(
                f"Highest-Sales {'Day' if trend_mode == 'Daily' else 'Month'}",
                pd.Timestamp(highest["Period"]).strftime(period_format),
                help=(
                    "Recorded amount: "
                    + format_compact_inr(highest["Total_Amount"])
                ),
            )
            c3.metric(
                f"Lowest-Sales {'Day' if trend_mode == 'Daily' else 'Month'}",
                pd.Timestamp(lowest["Period"]).strftime(period_format),
                help=(
                    "Recorded amount: "
                    + format_compact_inr(lowest["Total_Amount"])
                ),
            )

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
                    "value": "Recorded Order Amount (₹)",
                    "variable": "Series",
                },
            )

            fig.update_traces(
                selector=dict(name="Total_Amount"),
                name=f"{trend_mode} Recorded Amount",
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
                title="Recorded Order Amount (₹)",
                tickformat="~s",
            )
            fig.update_xaxes(
                title="Order Date",
                nticks=9,
                tickformat=date_format,
            )

            style_chart(fig, height=400)
            st.plotly_chart(
                fig,
                use_container_width=True,
                key="sales_analysis_trend_chart",
            )
            st.caption(
                f"The lighter line shows the {trend_mode.lower()} "
                f"recorded amount. The teal line shows the "
                f"{moving_label.lower()}."
            )
        else:
            st.info("No valid order dates are available.")

    st.divider()

    # ==================================================
    # 8. AMOUNT BY PRODUCT CATEGORY
    # ==================================================
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("### Amount by Product Category")

        if "Category" in df.columns:
            order_count_column = (
                "Order_ID" if "Order_ID" in df.columns
                else "Total_Amount"
            )

            category_data = (
                df.groupby("Category", dropna=False)
                .agg(
                    Total_Amount=("Total_Amount", "sum"),
                    Orders=(order_count_column, "count"),
                )
                .reset_index()
            )

            category_data["Category"] = (
                category_data["Category"].fillna("Unknown").astype(str)
            )
            category_data = category_data.sort_values(
                "Total_Amount", ascending=True
            )

            if not category_data.empty:
                top_category = category_data.loc[
                    category_data["Total_Amount"].idxmax(), "Category"
                ]

                category_data["Bar_Color"] = category_data["Category"].apply(
                    lambda category: (
                        "Leading category"
                        if category == top_category
                        else "Other categories"
                    )
                )
                category_data["Sales_Cr"] = (
                    category_data["Total_Amount"] / 1e7
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
                    custom_data=["Total_Amount", "Orders"],
                    labels={
                        "Sales_Cr": "Recorded Order Amount (₹ Cr)",
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
                        "<br>Orders: %{customdata[1]:,}"
                        "<extra></extra>"
                    ),
                )

                max_sales = max(category_data["Sales_Cr"].max(), 0)
                fig.update_layout(
                    showlegend=False,
                    margin=dict(l=15, r=95, t=25, b=50),
                )
                fig.update_xaxes(
                    title="Recorded Order Amount (₹ Cr)",
                    range=[
                        0,
                        max_sales * 1.25 if max_sales > 0 else 1,
                    ],
                )
                fig.update_yaxes(
                    title="",
                    categoryorder="total ascending",
                )

                style_chart(fig, height=400)
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="sales_analysis_category_chart",
                )
                st.caption(
                    f"Teal highlights {top_category}, the category with "
                    "the highest recorded amount. Amounts are not profit."
                )

    # ==================================================
    # 9. PAYMENT MODE
    # ==================================================
    with right:
        st.markdown("### Payment Mode")

        if "Payment_Mode" in df.columns:
            payment_data = (
                df["Payment_Mode"]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .rename_axis("Payment Mode")
                .reset_index(name="Orders")
            )

            if not payment_data.empty:
                fig = px.pie(
                    payment_data,
                    names="Payment Mode",
                    values="Orders",
                    hole=0.62,
                    color="Payment Mode",
                    color_discrete_sequence=CHART_COLORS,
                )

                total_payment_orders = int(payment_data["Orders"].sum())
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    textfont=dict(color="#FFFFFF", size=12),
                    hovertemplate=(
                        "Payment mode: %{label}"
                        "<br>Orders: %{value:,}"
                        "<br>Share: %{percent}"
                        "<extra></extra>"
                    ),
                )
                fig.update_layout(
                    legend=dict(
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
                                f"<b>{total_payment_orders:,}</b>"
                                "<br><span style='font-size:12px'>Orders</span>"
                            ),
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                            font=dict(size=19, color=NAVY),
                        )
                    ],
                )

                style_chart(fig, height=400)
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="sales_analysis_payment_chart",
                )
                st.caption(
                    "Payment-mode percentages represent order counts, "
                    "not payment amount."
                )

    st.divider()

    # ==================================================
    # 10. ORDER STATUS BREAKDOWN
    # ==================================================
    st.markdown("### Order Status Breakdown")

    status_data = (
        df["Order_Status"]
        .value_counts()
        .rename_axis("Order Status")
        .reset_index(name="Orders")
    )

    status_colors = {
        "Delivered": TEAL,
        "Processing": BLUE,
        "Shipped": INDIGO,
        "Cancelled": AMBER,
        "Returned": CORAL,
        "Unknown": SLATE,
    }

    if not status_data.empty:
        status_data["Share"] = (
            status_data["Orders"] / status_data["Orders"].sum() * 100
        )

        fig = px.bar(
            status_data,
            x="Order Status",
            y="Orders",
            color="Order Status",
            color_discrete_map=status_colors,
            text="Orders",
            custom_data=["Share"],
            labels={"Orders": "Number of Orders"},
        )
        fig.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "Status: %{x}"
                "<br>Orders: %{y:,}"
                "<br>Share: %{customdata[0]:.2f}%"
                "<extra></extra>"
            ),
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=25, t=25, b=40),
        )
        fig.update_yaxes(title="Number of Orders")

        style_chart(fig, height=350)
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="sales_analysis_status_chart",
        )

    st.divider()

    # ==================================================
    # 11. DYNAMIC STATE AMOUNT CHART
    # ==================================================
    if "State" in df.columns:
        displayed_states = sorted(
            df["State"].dropna().astype(str).unique().tolist()
        )

        if len(displayed_states) == 1:
            chart_title = (
                f"Recorded Order Amount — {displayed_states[0]}"
            )
        elif not displayed_states:
            chart_title = "Recorded Order Amount by State"
        else:
            chart_title = "Recorded Order Amount by Selected States"

        st.markdown(f"### {chart_title}")

        order_count_column = (
            "Order_ID" if "Order_ID" in df.columns
            else "Total_Amount"
        )

        state_data = (
            df.groupby("State", dropna=False)
            .agg(
                Total_Amount=("Total_Amount", "sum"),
                Orders=(order_count_column, "count"),
            )
            .reset_index()
        )

        state_data["State"] = (
            state_data["State"].fillna("Unknown").astype(str)
        )
        state_data = state_data.sort_values(
            "Total_Amount", ascending=True
        )

        if not state_data.empty:
            state_data["Amount_Cr"] = (
                state_data["Total_Amount"] / 1e7
            )
            max_state_amount = max(state_data["Amount_Cr"].max(), 0)

            fig = px.bar(
                state_data,
                x="Amount_Cr",
                y="State",
                orientation="h",
                color_discrete_sequence=[TEAL],
                custom_data=["Total_Amount", "Orders"],
                labels={
                    "Amount_Cr": "Recorded Order Amount (₹ Cr)",
                    "State": "",
                },
            )
            fig.update_traces(
                texttemplate="₹%{x:.2f} Cr",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "<b>%{y}</b>"
                    "<br>Recorded amount: ₹%{customdata[0]:,.2f}"
                    "<br>Orders: %{customdata[1]:,}"
                    "<extra></extra>"
                ),
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(l=20, r=100, t=25, b=50),
            )
            fig.update_xaxes(
                title="Recorded Order Amount (₹ Cr)",
                range=[
                    0,
                    max_state_amount * 1.25
                    if max_state_amount > 0 else 1,
                ],
            )
            fig.update_yaxes(
                title="",
                categoryorder="total ascending",
            )

            chart_height = max(
                350,
                min(800, 45 * len(state_data) + 100),
            )
            style_chart(fig, height=chart_height)
            st.plotly_chart(
                fig,
                use_container_width=True,
                key="sales_analysis_state_chart",
            )
            st.caption(
                f"Showing {len(state_data)} state(s) represented in the "
                "filtered data. Amounts are recorded Total Amount, not profit."
            )

    st.divider()

    
    # ==================================================
    # 12. DETAILED SALES DATA TABLE
    # ==================================================

    with st.expander(
        "📋 View sales data used in this analysis",
        expanded=False,
    ):
        # Select only columns available in the filtered sales data.
        display_columns = [
            column
            for column in [
                "Order_ID",
                "Order_Date",
                "State",
                "Category",
                "Payment_Mode",
                "Order_Status",
                "Total_Amount",
            ]
            if column in df.columns
        ]

        if not display_columns:
            st.info("No columns are available to display.")
        else:
            display_df = df[display_columns].copy()

            # Format order dates for display.
            if "Order_Date" in display_df.columns:
                display_df["Order_Date"] = (
                    pd.to_datetime(
                        display_df["Order_Date"],
                        errors="coerce",
                    ).dt.strftime("%d %b %Y")
                )

            # Friendly column headers.
            column_config = {}

            if "Order_ID" in display_df.columns:
                column_config["Order_ID"] = (
                    st.column_config.TextColumn("Order ID")
                )

            if "Order_Date" in display_df.columns:
                column_config["Order_Date"] = (
                    st.column_config.TextColumn("Order Date")
                )

            if "State" in display_df.columns:
                column_config["State"] = (
                    st.column_config.TextColumn("State")
                )

            if "Category" in display_df.columns:
                column_config["Category"] = (
                    st.column_config.TextColumn("Product Category")
                )

            if "Payment_Mode" in display_df.columns:
                column_config["Payment_Mode"] = (
                    st.column_config.TextColumn("Payment Mode")
                )

            if "Order_Status" in display_df.columns:
                column_config["Order_Status"] = (
                    st.column_config.TextColumn("Order Status")
                )

            if "Total_Amount" in display_df.columns:
                column_config["Total_Amount"] = (
                    st.column_config.NumberColumn(
                        "Recorded Amount (₹)",
                        format="₹%.2f",
                    )
                )

            # Limit displayed rows to keep the dashboard responsive.
            max_rows = 5000
            rows_to_display = display_df.head(max_rows)

            st.dataframe(
                rows_to_display,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                height=400,
            )

            # Explain the row limit and amount definition.
            if len(display_df) > max_rows:
                st.caption(
                    f"Showing the first {max_rows:,} of "
                    f"{len(display_df):,} filtered records. "
                    "Amounts represent recorded Total Amount, "
                    "not profit or verified accounting revenue."
                )
            else:
                st.caption(
                    f"Displaying {len(display_df):,} filtered records. "
                    "Amounts represent recorded Total Amount, "
                    "not profit or verified accounting revenue."
                )

