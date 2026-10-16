
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# 1. Cache the GeoJSON to avoid repeatedly reading it
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_india_geojson(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# 2. Main page
# --------------------------------------------------
def render(sales, customers, products):

    st.title("India Sales Map")
    st.caption(
        "Explore delivered sales performance across Indian states."
    )

    # --------------------------------------------------
    # 3. Validate and prepare data
    # --------------------------------------------------
    required_columns = [
        "State",
        "Order_ID",
        "Order_Status",
        "Total_Amount",
    ]

    missing = [
        column for column in required_columns
        if column not in sales.columns
    ]

    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    if sales.empty:
        st.warning("No records match the selected dashboard filters.")
        return

    df = sales.copy()

    df["State"] = df["State"].astype("string").str.strip()
    df["Order_Status"] = (
        df["Order_Status"].astype("string").str.strip()
    )
    df["Total_Amount"] = pd.to_numeric(
        df["Total_Amount"], errors="coerce"
    )

    df = df.dropna(
        subset=[
            "State",
            "Order_ID",
            "Order_Status",
            "Total_Amount",
        ]
    )

    # Match dataset state names to GeoJSON state names.
    state_mapping = {
        "UP": "Uttar Pradesh",
    }

    df["Map_State"] = df["State"].replace(state_mapping)

    # --------------------------------------------------
    # 4. Keep delivered orders
    # --------------------------------------------------
    delivered = df[
        df["Order_Status"].str.lower() == "delivered"
    ].copy()

    if delivered.empty:
        st.warning("No delivered orders match the selected filters.")
        return

    # --------------------------------------------------
    # 5. Aggregate state metrics
    # --------------------------------------------------
    state_summary = (
        delivered.groupby("Map_State", as_index=False)
        .agg(
            Delivered_Sales=("Total_Amount", "sum"),
            Delivered_Orders=("Order_ID", "nunique"),
        )
    )

    state_summary["Average_Order_Amount"] = (
        state_summary["Delivered_Sales"]
        / state_summary["Delivered_Orders"].replace(0, pd.NA)
    )

    # --------------------------------------------------
    # 6. KPI cards
    # --------------------------------------------------
    total_sales = delivered["Total_Amount"].sum()
    total_orders = delivered["Order_ID"].nunique()
    average_order = (
        total_sales / total_orders if total_orders else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Delivered Sales Amount",
        f"₹{total_sales:,.0f}",
    )

    col2.metric(
        "Delivered Orders",
        f"{total_orders:,}",
    )

    col3.metric(
        "Average Order Amount",
        f"₹{average_order:,.0f}",
    )

    st.caption(
        "These are recorded order amounts, not profit. "
        "Only Delivered orders are included."
    )

    # --------------------------------------------------
    # 7. Load GeoJSON
    # --------------------------------------------------
    geojson_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "india_states_simplified.geojson"
    )

    if not geojson_path.exists():
        st.error(f"GeoJSON file not found: {geojson_path}")
        return

    try:
        india_geojson = load_india_geojson(str(geojson_path))
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Could not read the GeoJSON file: {exc}")
        return

    features = india_geojson.get("features", [])

    if not features:
        st.error("The GeoJSON file contains no geographic features.")
        return

    geo_names = list(
        dict.fromkeys(
            str(
                feature.get("properties", {}).get("NAME_1", "")
            ).strip()
            for feature in features
        )
    )

    geo_names = [name for name in geo_names if name]

    if not geo_names:
        st.error("No state names were found in the GeoJSON.")
        return

    # --------------------------------------------------
    # 8. Metric selector
    # --------------------------------------------------
    metric_options = {
        "Delivered sales amount (₹)": "Delivered_Sales",
        "Delivered order count": "Delivered_Orders",
        "Average order amount (₹)": "Average_Order_Amount",
    }

    selected_label = st.selectbox(
        "Color states by",
        list(metric_options.keys()),
    )

    selected_metric = metric_options[selected_label]

    # --------------------------------------------------
    # 9. Prepare every geographic region
    # --------------------------------------------------
    map_base = pd.DataFrame({"Map_State": geo_names})

    map_data = map_base.merge(
        state_summary,
        on="Map_State",
        how="left",
    )

    # Missing values are treated as zero for the color scale.
    # The separate Has_Sales flag preserves hover clarity.
    map_data["Has_Sales"] = map_data[selected_metric].notna()
    map_data["Map_Value"] = map_data[selected_metric].fillna(0)

    max_value = float(map_data["Map_Value"].max())

    if max_value <= 0:
        max_value = 1.0

    unmatched = sorted(
        set(state_summary["Map_State"]) - set(geo_names)
    )

    if unmatched:
        st.warning(
            "These sales states did not match the map boundaries: "
            + ", ".join(unmatched)
        )

    # --------------------------------------------------
    # 10. Draw the styled, interactive India map
    # --------------------------------------------------

    # Palette based on your attached image:
    # dark green -> bright green -> yellow -> orange -> red
    india_sales_colors = [
        [0.00, "#008000"],
        [0.25, "#66CC00"],
        [0.50, "#FFFF00"],
        [0.75, "#FF8000"],
        [1.00, "#FF0000"],
    ]

    fig = go.Figure(
        go.Choropleth(
            geojson=india_geojson,
            locations=map_data["Map_State"],
            featureidkey="properties.NAME_1",
            z=map_data["Map_Value"],
            zmin=0,
            zmax=max_value,
            colorscale=india_sales_colors,
            customdata=map_data[
                [
                    "Has_Sales",
                    "Delivered_Sales",
                    "Delivered_Orders",
                    "Average_Order_Amount",
                ]
            ].to_numpy(),
            marker_line_color="#FFFFFF",
            marker_line_width=0.7,
            colorbar=dict(
                title=dict(
                    text=selected_label,
                    font=dict(color="#1F2937", size=13),
                ),
                tickfont=dict(color="#1F2937", size=11),
                thickness=16,
                len=0.72,
                outlinewidth=0,
            ),
            hovertemplate=(
                "<b>%{location}</b><br>"
                "Delivered sales: ₹%{customdata[1]:,.2f}<br>"
                "Delivered orders: %{customdata[2]:,.0f}<br>"
                "Average order amount: "
                "₹%{customdata[3]:,.2f}"
                "<extra></extra>"
            ),
            name="India sales",
        )
    )

    # Keep the map focused on India.
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcountries=False,
        showcoastlines=False,
        showland=False,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        title=dict(
            text=f"India — {selected_label}",
            x=0.02,
            xanchor="left",
            font=dict(
                size=20,
                color="#172554",
            ),
        ),
        height=620,
        margin=dict(l=10, r=20, t=65, b=10),
        paper_bgcolor="rgba(255,255,255,1)",
        plot_bgcolor="rgba(255,255,255,1)",
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="#1F2937",
        ),
        dragmode="pan",
    )

    # Show the toolbar for zooming and resetting the map.
    # Keep scroll-wheel zoom disabled for smoother page scrolling.
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": True,
            "scrollZoom": False,
            "responsive": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "select2d",
                "lasso2d",
            ],
        },
    )

    # --------------------------------------------------
    # 11. State-wise performance table
    # --------------------------------------------------
    st.subheader("State-wise Performance")

    table = state_summary.rename(
        columns={
            "Map_State": "State",
            "Delivered_Sales": "Delivered Sales Amount (₹)",
            "Delivered_Orders": "Delivered Orders",
            "Average_Order_Amount": "Average Order Amount (₹)",
        }
    )

    table = table.sort_values(
        "Delivered Sales Amount (₹)",
        ascending=False,
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )
