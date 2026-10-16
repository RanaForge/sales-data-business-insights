
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. CONFIGURATION
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    PROJECT_DIR
    / "models"
    / "sales_forecasting_cyclic_model.pkl"
)

MIN_HISTORY_DAYS = 30


# =========================================================
# 2. HELPER FUNCTIONS
# =========================================================

def format_inr(value):
    """Format an amount using Indian currency notation."""
    value = float(value)

    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} crore"

    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} lakh"

    if abs(value) >= 1e3:
        return f"₹{value / 1e3:.1f} K"

    return f"₹{value:,.0f}"


@st.cache_resource
def load_forecasting_artifact():
    """Load the existing trained model and its feature list."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Forecasting model not found: {MODEL_PATH}"
        )

    # Load the trusted model file created by your notebook.
    artifact = joblib.load(MODEL_PATH)

    required_keys = {
        "model",
        "features",
        "model_name",
        "target",
    }

    if not isinstance(artifact, dict):
        raise ValueError("The model artifact must be a dictionary.")

    missing_keys = required_keys - set(artifact.keys())

    if missing_keys:
        raise ValueError(
            f"Model artifact is missing keys: {missing_keys}"
        )

    model = artifact["model"]
    features = artifact["features"]

    if len(features) != model.n_features_in_:
        raise ValueError(
            "The saved feature list does not match the model."
        )

    return artifact


def prepare_daily_sales(sales):
    """
    Calculate daily delivered sales using Total_Amount.

    Missing calendar dates between the first and last observed
    dates are assigned zero delivered sales.
    """

    required_columns = {
        "Order_Date",
        "Order_Status",
        "Total_Amount",
    }

    missing_columns = required_columns - set(sales.columns)

    if missing_columns:
        raise ValueError(
            f"Sales data is missing columns: {missing_columns}"
        )

    df = sales.copy()

    df["Order_Date"] = pd.to_datetime(
        df["Order_Date"],
        errors="coerce",
    ).dt.normalize()

    df["Total_Amount"] = pd.to_numeric(
        df["Total_Amount"],
        errors="coerce",
    )

    df["Order_Status"] = (
        df["Order_Status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    df = df.dropna(
        subset=["Order_Date", "Total_Amount"]
    )

    # Only delivered orders contribute to the forecasting target.
    delivered = df[
        df["Order_Status"] == "delivered"
    ].copy()

    if delivered.empty:
        return pd.DataFrame(
            columns=["Order_Date", "Daily_Sales"]
        )

    daily = (
        delivered.groupby("Order_Date", as_index=False)
        ["Total_Amount"]
        .sum()
        .rename(
            columns={"Total_Amount": "Daily_Sales"}
        )
        .sort_values("Order_Date")
    )

    # Ensure every calendar day exists in the time series.
    full_dates = pd.date_range(
        start=daily["Order_Date"].min(),
        end=daily["Order_Date"].max(),
        freq="D",
    )

    daily = (
        daily.set_index("Order_Date")
        .reindex(full_dates, fill_value=0)
        .rename_axis("Order_Date")
        .reset_index()
    )

    daily["Daily_Sales"] = pd.to_numeric(
        daily["Daily_Sales"],
        errors="coerce",
    )

    return daily


def build_next_day_features(daily_sales, features):
    """
    Build the 10 input features in the exact order used
    when the model was trained.
    """

    history = daily_sales.copy()

    history["Order_Date"] = pd.to_datetime(
        history["Order_Date"],
        errors="coerce",
    ).dt.normalize()

    history["Daily_Sales"] = pd.to_numeric(
        history["Daily_Sales"],
        errors="coerce",
    )

    history = (
        history.dropna(
            subset=["Order_Date", "Daily_Sales"]
        )
        .sort_values("Order_Date")
        .drop_duplicates(
            subset=["Order_Date"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if len(history) < MIN_HISTORY_DAYS:
        raise ValueError(
            f"At least {MIN_HISTORY_DAYS} days of history "
            "are required."
        )

    # Ensure the lag features refer to consecutive days.
    date_differences = (
        history["Order_Date"].diff().dropna()
    )

    if not (
        date_differences == pd.Timedelta(days=1)
    ).all():
        raise ValueError(
            "Sales history must contain consecutive dates."
        )

    last_date = history["Order_Date"].iloc[-1]

    forecast_date = (
        last_date + pd.Timedelta(days=1)
    )

    day_of_week = forecast_date.dayofweek
    day_of_year = forecast_date.dayofyear

    values = history["Daily_Sales"]

    # These definitions match the forecasting notebook.
    feature_values = {
        "Day_Of_Week_Sin": np.sin(
            2 * np.pi * day_of_week / 7
        ),
        "Day_Of_Week_Cos": np.cos(
            2 * np.pi * day_of_week / 7
        ),
        "Day_Of_Year_Sin": np.sin(
            2 * np.pi * day_of_year / 365.25
        ),
        "Day_Of_Year_Cos": np.cos(
            2 * np.pi * day_of_year / 365.25
        ),
        "Sales_Lag_1": values.iloc[-1],
        "Sales_Lag_7": values.iloc[-7],
        "Sales_Lag_14": values.iloc[-14],
        "Sales_Lag_30": values.iloc[-30],
        "Rolling_Mean_7": values.tail(7).mean(),
        "Rolling_Mean_30": values.tail(30).mean(),
    }

    missing_features = [
        feature
        for feature in features
        if feature not in feature_values
    ]

    if missing_features:
        raise ValueError(
            f"Unsupported model features: {missing_features}"
        )

    # Preserve the precise training feature order.
    input_row = pd.DataFrame(
        [
            [
                feature_values[feature]
                for feature in features
            ]
        ],
        columns=features,
    )

    return forecast_date, input_row, history


# =========================================================
# 3. FORECASTING PAGE
# =========================================================

def render(sales, customers, products):
    """Render the SalesVision forecasting dashboard."""

    st.markdown("## Sales Forecasting")

    st.caption(
        "Next-day delivered sales prediction using historical "
        "sales, calendar cycles, lag features, and rolling averages."
    )

    if sales.empty:
        st.warning(
            "No sales records match the selected dashboard filters."
        )
        return

    # -----------------------------------------------------
    # Load the saved model
    # -----------------------------------------------------

    try:
        artifact = load_forecasting_artifact()

    except Exception as error:
        st.error(
            f"Unable to load the forecasting model: {error}"
        )
        return

    model = artifact["model"]
    features = artifact["features"]

    # -----------------------------------------------------
    # Prepare daily history
    # -----------------------------------------------------

    try:
        daily_sales = prepare_daily_sales(sales)

    except Exception as error:
        st.error(
            f"Unable to prepare sales history: {error}"
        )
        return

    if daily_sales.empty:
        st.warning(
            "No delivered orders are available for the selected filters."
        )
        return

    first_date = daily_sales["Order_Date"].min()
    last_date = daily_sales["Order_Date"].max()

    st.caption(
        f"History available: {first_date:%d %b %Y} "
        f"to {last_date:%d %b %Y}"
    )

    st.info(
        "The target is the recorded Total Amount of delivered orders. "
        "It represents recorded sales amount, not profit or audited revenue."
    )

    if len(daily_sales) < MIN_HISTORY_DAYS:
        st.warning(
            f"Only {len(daily_sales)} days are available. "
            f"The model requires at least {MIN_HISTORY_DAYS} days."
        )
        return

    # -----------------------------------------------------
    # Generate the forecast
    # -----------------------------------------------------

    try:
        forecast_date, input_row, history = (
            build_next_day_features(
                daily_sales,
                features,
            )
        )

        prediction = float(
            model.predict(input_row)[0]
        )

        if not np.isfinite(prediction):
            raise ValueError(
                "The model returned an invalid prediction."
            )

        # Match the original notebook's non-negative output rule.
        prediction = max(0.0, prediction)

    except Exception as error:
        st.error(
            f"Unable to generate the forecast: {error}"
        )
        return

    # -----------------------------------------------------
    # Calculate KPIs
    # -----------------------------------------------------

    latest_actual = float(
        history["Daily_Sales"].iloc[-1]
    )

    average_7d = float(
        history["Daily_Sales"].tail(7).mean()
    )

    average_30d = float(
        history["Daily_Sales"].tail(30).mean()
    )

    forecast_difference = prediction - latest_actual

    if latest_actual != 0:
        forecast_change_pct = (
            forecast_difference / abs(latest_actual)
        ) * 100
    else:
        forecast_change_pct = None

    # -----------------------------------------------------
    # KPI cards
    # -----------------------------------------------------

    st.markdown("### Next-Day Forecast")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label="Forecast Date",
        value=forecast_date.strftime("%d %b %Y"),
    )

    col2.metric(
        label="Predicted Sales",
        value=format_inr(prediction),
        help="Model-estimated delivered sales for the next calendar day.",
    )

    col3.metric(
        label="Latest Actual Sales",
        value=format_inr(latest_actual),
        help=f"Recorded delivered sales on {last_date:%d %b %Y}.",
    )

    col4.metric(
        label="30-Day Average",
        value=format_inr(average_30d),
        help="Average daily delivered sales across the latest 30 days.",
    )

    # -----------------------------------------------------
    # Historical chart
    # -----------------------------------------------------

    st.markdown("### Historical Delivered Sales")

    st.caption(
        "Purple = actual sales | Orange = forecast | "
        "Green dotted line = 30-day average"
    )

    chart_history = history.tail(90).copy()

    fig = go.Figure()

    # Actual sales history
    fig.add_trace(
        go.Scatter(
            x=chart_history["Order_Date"],
            y=chart_history["Daily_Sales"],
            mode="lines",
            name="Actual sales",
            line=dict(
                color="#635BFF",
                width=2.5,
            ),
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>"
                "Actual sales: ₹%{y:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    # Connect the last actual day to the next-day forecast
    fig.add_trace(
        go.Scatter(
            x=[last_date, forecast_date],
            y=[latest_actual, prediction],
            mode="lines+markers",
            name="Next-day forecast",
            line=dict(
                color="#F59E0B",
                width=2.5,
                dash="dash",
            ),
            marker=dict(
                color=["#635BFF", "#F59E0B"],
                size=[8, 12],
                symbol=["circle", "diamond"],
                line=dict(
                    color="white",
                    width=1.5,
                ),
            ),
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>"
                "Amount: ₹%{y:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    # Average sales reference line
    fig.add_hline(
        y=average_30d,
        line_dash="dot",
        line_width=1.5,
        line_color="#0F9D78",
        annotation_text=(
            f"30-day average: {format_inr(average_30d)}"
        ),
        annotation_position="top left",
        annotation_font=dict(
            color="#087F5B",
            size=11,
        ),
    )

    # Forecast boundary on the next calendar day
    fig.add_vline(
        x=forecast_date.strftime("%Y-%m-%d"),
        line_dash="dash",
        line_width=1.2,
        line_color="#F59E0B",
    )

    # Label the forecast point, offset away from the boundary
    fig.add_annotation(
        x=forecast_date.strftime("%Y-%m-%d"),
        y=prediction,
        text=(
            f"<b>Forecast<br>{format_inr(prediction)}</b>"
        ),
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.5,
        arrowcolor="#D97706",
        ax=-65,
        ay=-45,
        bgcolor="#FFF7ED",
        bordercolor="#F59E0B",
        borderwidth=1,
        borderpad=6,
        font=dict(
            color="#9A3412",
            size=11,
        ),
    )

    fig.update_layout(
        template="plotly_white",
        height=440,
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="#334155",
        ),
        margin=dict(
            l=20,
            r=25,
            t=45,
            b=20,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(
                color="#334155",
                size=12,
            ),
            bgcolor="rgba(255,255,255,0)",
        ),
    )

    fig.update_xaxes(
        title_text="Date",
        showgrid=False,
        showline=True,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        title_font=dict(color="#334155"),
    )

    fig.update_yaxes(
        title_text="Delivered sales (₹)",
        tickformat="~s",
        rangemode="tozero",
        showgrid=True,
        gridcolor="#E2E8F0",
        zeroline=False,
        tickfont=dict(color="#475569"),
        title_font=dict(color="#334155"),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": True,
            "scrollZoom": False,
            "responsive": True,
        },
    )

    # -----------------------------------------------------
    # Business interpretation
    # -----------------------------------------------------

    st.markdown("### Forecast Interpretation")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Forecast vs Latest Actual",
            value=format_inr(abs(forecast_difference)),
            delta=(
                f"{forecast_change_pct:+.2f}%"
                if forecast_change_pct is not None
                else "No baseline available"
            ),
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="7-Day Average Sales",
            value=format_inr(average_7d),
        )

    if forecast_difference < 0:
        st.write(
            f"The predicted sales amount is "
            f"{format_inr(abs(forecast_difference))} below "
            "the latest recorded daily amount."
        )
    elif forecast_difference > 0:
        st.write(
            f"The predicted sales amount is "
            f"{format_inr(forecast_difference)} above "
            "the latest recorded daily amount."
        )
    else:
        st.write(
            "The predicted sales amount matches the latest "
            "recorded daily amount."
        )

    # -----------------------------------------------------
    # Recent daily sales table
    # -----------------------------------------------------

    with st.expander("View recent daily sales and forecast"):

        recent = history.tail(14).copy()

        recent["Date"] = recent["Order_Date"].dt.strftime(
            "%d %b %Y"
        )

        recent["Actual Delivered Sales"] = (
            recent["Daily_Sales"].map(
                lambda value: f"₹{value:,.2f}"
            )
        )

        recent = recent[
            ["Date", "Actual Delivered Sales"]
        ]

        forecast_row = pd.DataFrame(
            [{
                "Date": forecast_date.strftime("%d %b %Y"),
                "Actual Delivered Sales": "—",
            }]
        )

        recent = pd.concat(
            [recent, forecast_row],
            ignore_index=True,
        )

        recent["Predicted Sales"] = "—"

        recent.loc[
            recent.index[-1],
            "Predicted Sales",
        ] = f"₹{prediction:,.2f}"

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )

    # -----------------------------------------------------
    # Model information
    # -----------------------------------------------------

    with st.expander("Model information and input features"):

        st.write(
            "**Model:**",
            artifact["model_name"],
        )

        st.write(
            "**Target:**",
            artifact["target"],
        )

        st.write(
            "**Algorithm:**",
            type(model).__name__,
        )

        st.write(
            "**Number of input features:**",
            len(features),
        )

        st.write(
            "**Forecast horizon:**",
            "One calendar day",
        )

        st.markdown("**Input features**")

        for feature in features:
            st.markdown(f"- `{feature}`")

    # -----------------------------------------------------
    # Limitations
    # -----------------------------------------------------

    st.markdown("### Forecast Limitations")

    st.markdown(
        """
        - This is a one-day-ahead estimate, not a confirmed sales result.
        - The model uses calendar cycles, historical sales lags, and
          rolling averages.
        - The historical development evaluation reported an MAE of
          approximately ₹5.70 lakh per day. This is not a guaranteed
          error bound.
        - The evaluation used actual preceding-day observations, so it
          does not establish multi-day recursive forecast accuracy.
        - Promotions, holidays, stock availability, and unusual order
          patterns can affect actual sales.
        """
    )

    st.caption(
        "Forecasts are estimates for analysis and planning, not guarantees."
    )
