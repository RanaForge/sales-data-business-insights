
import streamlit as st


def apply_theme():
    """Apply the shared SalesVision dashboard theme."""

    st.markdown(
        """
        <style>
        /* Main application */
        .stApp,
        [data-testid="stAppViewContainer"] {
            background-color: #F4F7FB;
            color: #24324B;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1600px;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #172554;
        }

        [data-testid="stSidebar"] * {
            color: #F8FAFC;
        }

        [data-testid="stSidebar"] hr {
            border-color: #334477;
        }

        /* Main-page headings */
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] h4 {
            color: #172554 !important;
        }

        /* Main-page text */
        [data-testid="stMain"] p,
        [data-testid="stMain"] label {
            color: #334155;
        }

        /* Hero banner */
        .hero {
            padding: 26px 30px;
            border-radius: 18px;
            background: linear-gradient(
                115deg,
                #172554 0%,
                #4338CA 68%,
                #0F9FA8 100%
            );
            margin-bottom: 26px;
            box-shadow: 0 8px 24px rgba(23, 37, 84, 0.12);
        }

        .hero h1 {
            color: #FFFFFF !important;
            font-size: 32px;
            line-height: 1.2;
            margin: 0 0 10px 0;
        }

        .hero p {
            color: #E0E7FF !important;
            margin: 0;
            font-size: 15px;
        }

        /* KPI cards */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            padding: 18px 20px;
            border-radius: 16px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 16px rgba(30, 41, 59, 0.05);
        }

        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] *,
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] * {
            color: #172554 !important;
            opacity: 1 !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 14px;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 750;
        }

        /* Plotly chart panels */
        [data-testid="stPlotlyChart"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 8px;
            box-shadow: 0 3px 12px rgba(30, 41, 59, 0.035);
        }

        /* Alerts */
        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        /* Sidebar expand/collapse toggle */
        [data-testid="stAppViewContainer"] button[kind="header"],
        [data-testid="stAppViewContainer"] [data-testid="stHeader"] button,
        [data-testid="stSidebarCollapsedControl"] button {
            background: #4F46E5 !important;
            color: #FFFFFF !important;
            border: 1px solid #4338CA !important;
            border-radius: 9px !important;
            opacity: 1 !important;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25) !important;
        }

        [data-testid="stAppViewContainer"] button[kind="header"] svg,
        [data-testid="stAppViewContainer"] [data-testid="stHeader"] button svg,
        [data-testid="stSidebarCollapsedControl"] button svg {
            color: #FFFFFF !important;
            stroke: #FFFFFF !important;
            opacity: 1 !important;
        }

        [data-testid="stAppViewContainer"] button[kind="header"]:hover,
        [data-testid="stAppViewContainer"] [data-testid="stHeader"] button:hover,
        [data-testid="stSidebarCollapsedControl"] button:hover {
            background: #3730A3 !important;
        }

        /* Sidebar multiselect */
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] {
            width: 100%;
        }

        [data-testid="stSidebar"] [data-testid="stMultiSelect"]
        [data-baseweb="select"] {
            min-height: 44px;
            height: auto !important;
        }

        [data-testid="stSidebar"] [data-testid="stMultiSelect"]
        [data-baseweb="select"] > div {
            min-height: 44px;
            height: auto !important;
            align-items: center;
        }

        [data-testid="stSidebar"] [data-testid="stMultiSelect"]
        [data-baseweb="select"] > div > div:first-child {
            flex-wrap: wrap !important;
            max-height: none !important;
            overflow: visible !important;
        }

        /* Sales trend radio selector */
        div[data-testid="stRadio"] {
            margin: 8px 0 18px 0;
        }

        div[data-testid="stRadio"] > label {
            color: #172554 !important;
            font-weight: 600 !important;
        }

        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 12px !important;
            flex-wrap: wrap !important;
        }

        div[data-testid="stRadio"] div[role="radiogroup"] label {
            background-color: #FFFFFF !important;
            color: #172554 !important;
            border: 1px solid #94A3B8 !important;
            border-radius: 10px !important;
            padding: 9px 18px !important;
            min-height: 42px !important;
            cursor: pointer !important;
            opacity: 1 !important;
        }

        div[data-testid="stRadio"] div[role="radiogroup"] label * {
            color: #172554 !important;
            opacity: 1 !important;
        }

        div[data-testid="stRadio"] div[role="radiogroup"] label:has(
            input[type="radio"]:checked
        ) {
            background-color: #4338CA !important;
            border-color: #4338CA !important;
            color: #FFFFFF !important;
        }

        div[data-testid="stRadio"] div[role="radiogroup"] label:has(
            input[type="radio"]:checked
        ) * {
            color: #FFFFFF !important;
        }

        div[data-testid="stRadio"] input[type="radio"] {
            accent-color: #4338CA !important;
        }
        
        /* Detailed sales table: light theme */
        [data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid #DCE4F0 !important;
            border-radius: 12px !important;
            overflow: hidden;
        }

        /* Expander header */
        [data-testid="stExpander"] summary {
            background-color: #FFFFFF !important;
            color: #172554 !important;
            font-weight: 600 !important;
            padding: 16px 20px !important;
        }

        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span,
        [data-testid="stExpander"] summary svg {
            color: #172554 !important;
            fill: #172554 !important;
        }

        /* Table container */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
        }

        /* Caption beneath table */
        [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
            color: #64748B !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
