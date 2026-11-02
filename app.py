
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.styles import apply_theme
from utils import ui

from views import overview
from views import sales_analysis
from views import india_sales_map
from views import forecasting
from utils.filters import render_date_filter, render_state_filter


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="SalesVision | Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
        /* Keep the main content clear of Streamlit's top toolbar */
        [data-testid="stMainBlockContainer"] {
            padding-top: 2rem;
        }

        /* Keep the Streamlit header transparent and unobtrusive */
        [data-testid="stHeader"] {
            background: rgba(244, 247, 251, 0.95);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 2. Apply shared dashboard theme
# --------------------------------------------------
apply_theme()
ui.inject_css()


# --------------------------------------------------
# 3. Load shared data
# --------------------------------------------------
try:
    sales, customers, products = load_data()
except Exception as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.info(
        "Check that sales.csv, customers.csv and products.csv "
        "are available in the project's data folder."
    )
    st.stop()


# --------------------------------------------------
# 4. Sidebar navigation
# --------------------------------------------------
with st.sidebar:
    st.markdown("# 📊 SalesVision")
    st.caption("BUSINESS INTELLIGENCE")
    st.divider()

    selected_page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Sales Analysis",
            "India Sales Map",
            "Forecasting",
        ],
        key="main_navigation",
    )

    st.divider()
    st.markdown("### Filters")

    valid_dates = sales["Order_Date"].dropna()

    if valid_dates.empty:
        st.error("No valid order dates were found.")
        st.stop()

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    # Quick-range pills + calendar popup
    start_date, end_date = render_date_filter(
        min_date=min_date,
        max_date=max_date,
    )

    # Compact state selector (opens a popover with toggle chips)
    all_states = sorted(
        sales["State"].dropna().astype(str).unique().tolist()
    )
    selected_states = render_state_filter(all_states)

    st.divider()
    st.caption("Indian E-Commerce Analytics | 2026")


# --------------------------------------------------
# 5. Apply shared date and state filters
# --------------------------------------------------
date_mask = (
    sales["Order_Date"] >= pd.Timestamp(start_date)
) & (
    sales["Order_Date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)
)
state_mask = sales["State"].astype(str).isin(selected_states)

filtered_sales = sales.loc[date_mask & state_mask]


# --------------------------------------------------
# 6. Route to the selected page
# --------------------------------------------------
# Lets pages compare the selected period with the one before it.
context = {
    "full_sales": sales,
    "start": start_date,
    "end": end_date,
    "states": selected_states,
}

if selected_page == "Overview":
    overview.render(filtered_sales, customers, products, context=context)

elif selected_page == "Sales Analysis":
    sales_analysis.render(filtered_sales, customers, products, context=context)

elif selected_page == "India Sales Map":
    india_sales_map.render(filtered_sales, customers, products, context=context)

elif selected_page == "Forecasting":
    forecasting.render(filtered_sales, customers, products, context=context)
