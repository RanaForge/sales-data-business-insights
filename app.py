
import streamlit as st

from utils.data_loader import load_data
from utils.styles import apply_theme

from views import overview
from views import sales_analysis
from views import india_sales_map
from views import forecasting
from utils.date_filter import render_date_filter


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

        /* Avoid clipping the dashboard banner */
        .hero {
            position: relative;
            margin-top: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 2. Apply shared dashboard theme
# --------------------------------------------------
apply_theme()


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
# 4. Dashboard header
# --------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>SalesVision Dashboard</h1>
        <p>
            Business intelligence for e-commerce sales,
            customer orders and forecasting.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 5. Sidebar navigation
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

   # Modern custom date-range calendar
    start_date, end_date = render_date_filter(
        min_date=min_date,
        max_date=max_date,
    )

    all_states = sorted(
        sales["State"].dropna().astype(str).unique().tolist()
    )

    
    selected_states = st.multiselect(
        "States",
        options=all_states,
        default=all_states,
        key="state_filter",
        placeholder="Select states...",
        help="Select one or more states to filter the dashboard.",
    )


    st.divider()
    st.caption("Indian E-Commerce Analytics | 2026")


# --------------------------------------------------
# 6. Apply shared date and state filters
# --------------------------------------------------
filtered_sales = sales.copy()

# Apply the selected date range from the custom calendar
filtered_sales = filtered_sales[
    filtered_sales["Order_Date"].dt.date.between(
        start_date,
        end_date,
    )
]

# Apply the selected states
filtered_sales = filtered_sales[
    filtered_sales["State"]
    .astype(str)
    .isin(selected_states)
]


# --------------------------------------------------
# 7. Route to the selected page
# --------------------------------------------------
if selected_page == "Overview":
    overview.render(filtered_sales, customers, products)

elif selected_page == "Sales Analysis":
    sales_analysis.render(filtered_sales, customers, products)

elif selected_page == "India Sales Map":
    india_sales_map.render(filtered_sales, customers, products)

elif selected_page == "Forecasting":
    forecasting.render(filtered_sales, customers, products)
