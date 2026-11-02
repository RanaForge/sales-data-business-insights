"""
Forecasting page.

What changed and why
    * The forecast always uses ALL states and ALL dates. The saved model was
      trained on all-state daily totals, so feeding it a one-state subset
      gives nonsense. The sidebar filters do not apply here (the page says so).
    * A single number is never shown alone. Every forecast comes with a likely
      range (80%), because daily sales swing by about +-12%.
    * "How good is it?" compares the model with simple averages on days it had
      not seen. The saved model was trained on all history, so for this check
      the same recipe is refit on the first 80% of days (the notebook's own
      protocol) and scored on the last 20%.
    * Beyond one day the forecast is the 365-day average with a bootstrap range:
      the model was only ever validated one day ahead.

Layout
    header and horizon switch
    4 KPI cards
    forecast chart
    backtest chart   |   model vs simple averages and verdict
    recent-days table and model details (collapsed)
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression

from utils import ui
from utils.analytics import prepare_sales

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "sales_forecasting_cyclic_model.pkl"

DEFAULT_FEATURES = [
    "Day_Of_Week_Sin", "Day_Of_Week_Cos", "Day_Of_Year_Sin", "Day_Of_Year_Cos",
    "Sales_Lag_1", "Sales_Lag_7", "Sales_Lag_14", "Sales_Lag_30",
    "Rolling_Mean_7", "Rolling_Mean_30",
]
TRAIN_FRACTION = 0.80          # same chronological split as the notebook
LEVEL_DAYS = 365               # window for the long-run average
LOW_Q, HIGH_Q = 0.10, 0.90     # 80% range
MIN_HISTORY_DAYS = 90
HORIZONS = ["Next day", "Next 30 days", "Next 3 months"]
HISTORY_WINDOWS = {"30 days": 30, "90 days": 90, "180 days": 180}


# ==================================================
# 1. DATA AND MODEL
# ==================================================
@st.cache_resource(show_spinner=False)
def load_model_artifact(path):
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or "model" not in artifact or "features" not in artifact:
        raise ValueError("The saved file must contain 'model' and 'features'.")
    return artifact


def try_load_artifact():
    try:
        return load_model_artifact(str(MODEL_PATH)), None
    except Exception as exc:                       # missing file, bad pickle, version clash
        return None, f"{type(exc).__name__}: {exc}"


@st.cache_data(show_spinner=False)
def load_history(_sales, version):
    """Daily delivered sales and delivered order counts over every day in the data."""
    df = prepare_sales(_sales)
    delivered = df[df["Order_Status"].eq("delivered")].dropna(subset=["Order_Date"])
    grouped = (
        delivered.assign(Day=delivered["Order_Date"].dt.normalize())
        .groupby("Day")["Total_Amount"].agg(["sum", "size"])
    )
    days = pd.date_range(grouped.index.min(), grouped.index.max(), freq="D")
    grouped = grouped.reindex(days, fill_value=0)
    return grouped["sum"].astype(float).rename("Daily_Sales"), grouped["size"].astype(float).rename("Orders")


def build_features(daily):
    """
    The model's input features for every day of `daily`, using earlier days only.
    Same definitions as the notebook (cyclic calendar + lags + rolling means).
    Add a NaN row at the end to get the features for the next day.
    """
    index = daily.index
    previous = daily.shift(1)
    return pd.DataFrame({
        "Day_Of_Week_Sin": np.sin(2 * np.pi * index.dayofweek / 7),
        "Day_Of_Week_Cos": np.cos(2 * np.pi * index.dayofweek / 7),
        "Day_Of_Year_Sin": np.sin(2 * np.pi * index.dayofyear / 365.25),
        "Day_Of_Year_Cos": np.cos(2 * np.pi * index.dayofyear / 365.25),
        "Sales_Lag_1": daily.shift(1),
        "Sales_Lag_7": daily.shift(7),
        "Sales_Lag_14": daily.shift(14),
        "Sales_Lag_30": daily.shift(30),
        "Rolling_Mean_7": previous.rolling(7).mean(),
        "Rolling_Mean_30": previous.rolling(30).mean(),
    }, index=index)


def error_metrics(actual, predicted):
    error = np.asarray(predicted, dtype=float) - np.asarray(actual, dtype=float)
    actual = np.asarray(actual, dtype=float)
    return {
        "MAE": float(np.abs(error).mean()),
        "RMSE": float(np.sqrt((error ** 2).mean())),
        "MAPE": float((np.abs(error) / actual).mean() * 100),
    }


# ==================================================
# 2. BACKTEST (days the model had not seen)
# ==================================================
def run_backtest(daily, features, model_label):
    """Refit the model recipe on the first 80% of usable days, score on the rest."""
    frame = build_features(daily)[features]
    usable = frame.assign(target=daily).dropna()
    split = int(len(usable) * TRAIN_FRACTION)
    train, test = usable.iloc[:split], usable.iloc[split:]

    refit = LinearRegression().fit(train[features], train["target"])
    predicted = pd.Series(np.clip(refit.predict(usable[features]), 0, None), index=usable.index)

    previous = daily.shift(1)
    candidates = {
        model_label: predicted,
        "Previous day": previous,
        "30-day average": previous.rolling(30).mean(),
        "Long-run average": previous.expanding().mean(),
    }

    actual = test["target"]
    metrics = {name: error_metrics(actual, series.loc[actual.index]) for name, series in candidates.items()}

    # honest range check: band from TRAINING residuals, applied to the unseen test days
    train_residual = train["target"] - predicted.loc[train.index]
    low_res, high_res = np.quantile(train_residual, [LOW_Q, HIGH_Q])
    test_pred = predicted.loc[actual.index]
    inside = (actual >= test_pred + low_res) & (actual <= test_pred + high_res)

    return {
        "actual": actual,
        "predicted": test_pred,
        "band": (float(low_res), float(high_res)),
        "coverage": float(inside.mean() * 100),
        "metrics": metrics,
        "model_label": model_label,
        "n_test": len(actual),
        "all_predicted": predicted,
        "usable_actual": usable["target"],
    }


def production_band(backtest):
    """Residual range for live forecasts: the last 365 usable days."""
    residual = (backtest["usable_actual"] - backtest["all_predicted"]).tail(LEVEL_DAYS)
    low, high = np.quantile(residual, [LOW_Q, HIGH_Q])
    return float(low), float(high)


# ==================================================
# 3. FORECASTS
# ==================================================
def next_day_forecast(daily, artifact, band):
    date = daily.index[-1] + pd.Timedelta(days=1)
    level = float(daily.tail(LEVEL_DAYS).mean())
    avg30 = float(daily.tail(30).mean())

    point, used_model = level, False
    if artifact is not None:
        features = list(artifact["features"])
        extended = pd.concat([daily, pd.Series([np.nan], index=[date])])
        row = build_features(extended).loc[[date], features]
        point = max(0.0, float(artifact["model"].predict(row)[0]))
        used_model = True

    return {
        "date": date, "point": point, "level": level, "avg30": avg30,
        "low": max(0.0, point + band[0]), "high": point + band[1], "used_model": used_model,
    }


def level_day_range(daily):
    """Range for a single day around the 365-day average."""
    recent = daily.tail(LEVEL_DAYS)
    level = float(recent.mean())
    low, high = np.quantile(recent - level, [LOW_Q, HIGH_Q])
    return level, max(0.0, level + float(low)), level + float(high)


def bootstrap_total(values, n_days, n=10_000, seed=42):
    """Expected total and 80% range for `n_days` days, resampling past days."""
    rng = np.random.default_rng(seed)
    sums = rng.choice(np.asarray(values, dtype=float), size=(n, n_days)).sum(axis=1)
    return float(sums.mean()), float(np.quantile(sums, LOW_Q)), float(np.quantile(sums, HIGH_Q))


def month_periods(last_date, count=3):
    """The next `count` calendar months; the first may be the rest of this month."""
    periods, cursor = [], last_date + pd.Timedelta(days=1)
    for _ in range(count):
        end = cursor + pd.offsets.MonthEnd(0)
        days = (end - cursor).days + 1
        label = cursor.strftime("%b %Y") + ("" if cursor.day == 1 else " (rest)")
        periods.append({"label": label, "start": cursor, "end": end, "days": days})
        cursor = end + pd.Timedelta(days=1)
    return periods


def monthly_backtest(daily):
    """How far off 'daily average x days' was for each complete past month."""
    totals, counts = daily.resample("MS").sum(), daily.resample("MS").size()
    errors = []
    for start, total in totals.items():
        if counts[start] != start.days_in_month or total <= 0:
            continue
        before = daily[: start - pd.Timedelta(days=1)]
        if len(before) < 90:
            continue
        predicted = before.tail(LEVEL_DAYS).mean() * start.days_in_month
        errors.append(abs(predicted - total) / total * 100)
    return (float(np.mean(errors)), len(errors)) if errors else (None, 0)


def range_text(low, high):
    if high >= 1e7:
        return f"₹{low / 1e7:.2f} to ₹{high / 1e7:.2f} Cr"
    return f"₹{low / 1e5:.1f} to ₹{high / 1e5:.1f} lakh"


# ==================================================
# 4. CHARTS
# ==================================================
def _finish(fig, unit, height=360):
    ui.style_chart(fig, height=height)
    fig.update_yaxes(title_text=unit)
    return fig


def next_day_figure(daily, window, fc):
    scale = 1e5
    recent = daily.tail(window)
    average = fc["avg30"] / scale

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recent.index, y=recent / scale, mode="lines", name="Actual daily sales",
        line=dict(color=ui.INDIGO, width=2),
        hovertemplate="₹%{y:.2f} lakh<extra>Actual</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[recent.index[0], fc["date"]], y=[average, average], mode="lines",
        name=f"30-day average ₹{average:.2f} lakh",
        line=dict(color=ui.NAVY, width=2, dash="dash"), hoverinfo="skip",
    ))
    label = "Forecast with 80% range"
    fig.add_trace(go.Scatter(
        x=[fc["date"]], y=[fc["point"] / scale], mode="markers", name=label,
        marker=dict(color=ui.TEAL, size=13, symbol="diamond", line=dict(color="#FFFFFF", width=2)),
        error_y=dict(
            type="data", symmetric=False,
            array=[(fc["high"] - fc["point"]) / scale],
            arrayminus=[(fc["point"] - fc["low"]) / scale],
            color=ui.TEAL, thickness=3, width=7,
        ),
        hovertemplate=(
            f"₹{fc['point'] / scale:.2f} lakh (range ₹{fc['low'] / scale:.1f} "
            f"to ₹{fc['high'] / scale:.1f} lakh)<extra>Forecast</extra>"
        ),
    ))
    _finish(fig, "₹ lakh")
    pad = pd.Timedelta(days=max(2, window // 25))
    fig.update_xaxes(range=[recent.index[0], fc["date"] + pad], tickformat="%d %b")
    return fig


def next_30_figure(daily, window, level, day_low, day_high):
    scale = 1e5
    recent = daily.tail(window)
    future = pd.date_range(daily.index[-1] + pd.Timedelta(days=1), periods=30, freq="D")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recent.index, y=recent / scale, mode="lines", name="Actual daily sales",
        line=dict(color=ui.INDIGO, width=2),
        hovertemplate="₹%{y:.2f} lakh<extra>Actual</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=list(future) + list(future[::-1]),
        y=[day_high / scale] * len(future) + [day_low / scale] * len(future),
        fill="toself", fillcolor="rgba(15, 159, 168, 0.16)", line=dict(width=0),
        name="Where a single day is likely to land (80%)", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=future, y=[level / scale] * len(future), mode="lines",
        name=f"Expected daily sales ₹{level / scale:.2f} lakh",
        line=dict(color=ui.TEAL, width=3),
        hovertemplate="₹%{y:.2f} lakh<extra>Expected</extra>",
    ))
    _finish(fig, "₹ lakh")
    fig.update_xaxes(tickformat="%d %b")
    return fig


def months_figure(daily, periods):
    scale = 1e7
    totals, counts = daily.resample("MS").sum(), daily.resample("MS").size()
    complete = totals[[counts[m] == m.days_in_month for m in totals.index]].tail(12)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[m.strftime("%b %Y") for m in complete.index], y=complete / scale,
        name="Actual month", marker_color=ui.LIGHT_INDIGO,
        hovertemplate="₹%{y:.2f} Cr<extra>Actual</extra>",
    ))
    fig.add_trace(go.Bar(
        x=[p["label"] for p in periods], y=[p["expected"] / scale for p in periods],
        name="Forecast with 80% range", marker_color=ui.TEAL,
        error_y=dict(
            type="data", symmetric=False,
            array=[(p["high"] - p["expected"]) / scale for p in periods],
            arrayminus=[(p["expected"] - p["low"]) / scale for p in periods],
            color=ui.NAVY, thickness=2, width=6,
        ),
        hovertemplate="₹%{y:.2f} Cr<extra>Forecast</extra>",
    ))
    _finish(fig, "₹ Cr")
    fig.update_layout(bargap=0.25)
    fig.update_yaxes(rangemode="tozero")
    return fig


def backtest_figure(bt):
    scale = 1e5
    dates = bt["actual"].index
    low_res, high_res = bt["band"]
    upper = (bt["predicted"] + high_res) / scale
    lower = (bt["predicted"] + low_res).clip(lower=0) / scale

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(dates) + list(dates[::-1]), y=list(upper) + list(lower[::-1]),
        fill="toself", fillcolor="rgba(15, 159, 168, 0.16)", line=dict(width=0),
        name="80% range", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=bt["actual"] / scale, mode="lines", name="Actual",
        line=dict(color=ui.INDIGO, width=1.8),
        hovertemplate="₹%{y:.2f} lakh<extra>Actual</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=bt["predicted"] / scale, mode="lines", name="Model forecast",
        line=dict(color=ui.TEAL, width=2.5),
        hovertemplate="₹%{y:.2f} lakh<extra>Forecast</extra>",
    ))
    _finish(fig, "₹ lakh", height=330)
    fig.update_xaxes(tickformat="%d %b")
    return fig


# ==================================================
# 5. PAGE SECTIONS
# ==================================================
def filters_active(context):
    if not context or context.get("full_sales") is None:
        return False
    full = context["full_sales"]
    dates = full["Order_Date"].dropna()
    if context.get("start") != dates.min().date() or context.get("end") != dates.max().date():
        return True
    all_states = set(full["State"].dropna().astype(str))
    return set(context.get("states") or []) != all_states


def spark(daily, rolling=None):
    series = daily.rolling(rolling).mean() if rolling else daily
    return series.tail(60)


def render_kpis(horizon, ctx):
    daily, fc = ctx["daily"], ctx["fc"]
    cards = []

    if horizon == "Next day":
        half = (fc["high"] - fc["low"]) / 2
        gap = (fc["point"] - fc["avg30"]) / fc["avg30"] * 100 if fc["avg30"] else 0
        last_value = float(daily.iloc[-1])
        inside = fc["low"] <= last_value <= fc["high"]
        cards = [
            dict(label=f"Forecast for {ui.format_date(fc['date'])}", value=ui.format_compact_inr(fc["point"]),
                 context="Saved model" if fc["used_model"] else "365-day average",
                 spark=spark(daily), help="The model's estimate for the next day."),
            dict(label="Likely range (80%)", value=f"±{ui.format_compact_inr(half)}",
                 context=range_text(fc["low"], fc["high"]), spark=None,
                 help="On 8 days out of 10 the actual number lands inside this range."),
            dict(label="30-day average", value=ui.format_compact_inr(fc["avg30"]),
                 delta_text=f"{gap:+.1f}%", tone="flat", context="forecast vs average",
                 spark=spark(daily, 7), help="Mean daily sales of the last 30 days."),
            dict(label=f"Last actual ({ui.format_date(daily.index[-1])})", value=ui.format_compact_inr(last_value),
                 context="Inside the usual range" if inside else "Outside the usual range",
                 spark=spark(daily), help="Most recent day in the data."),
        ]

    elif horizon == "Next 30 days":
        total, low, high = ctx["total30"]
        previous = float(daily.tail(30).sum())
        change = (total - previous) / previous * 100 if previous else 0
        half_pct = (high - low) / 2 / total * 100 if total else 0
        day_half = (ctx["day_high"] - ctx["day_low"]) / 2
        cards = [
            dict(label="Expected sales, next 30 days", value=ui.format_crore(total),
                 context=f"About {ui.format_compact_inr(ctx['level'])} a day", spark=spark(daily, 7),
                 help="30 days at the 365-day daily average."),
            dict(label="Likely range (80%)", value=f"±{half_pct:.1f}%",
                 context=range_text(low, high), spark=None,
                 help="Range for the 30-day total, from resampling past days."),
            dict(label="Previous 30 days", value=ui.format_crore(previous),
                 delta_text=f"{change:+.1f}%", tone="flat", context="forecast vs previous 30 days",
                 spark=spark(daily, 7), help="Actual total of the last 30 days."),
            dict(label="Any single day (80%)", value=f"±{ui.format_compact_inr(day_half)}",
                 context=range_text(ctx["day_low"], ctx["day_high"]), spark=None,
                 help="Individual days are far less predictable than the total."),
        ]

    else:
        periods, (t_total, t_low, t_high) = ctx["periods"], ctx["total3"]
        first = periods[0]
        half_pct = (first["high"] - first["low"]) / 2 / first["expected"] * 100 if first["expected"] else 0
        mape, n_months = ctx["month_error"]
        cards = [
            dict(label=first["label"], value=ui.format_crore(first["expected"]),
                 context=f"{first['days']} days at the daily average", spark=spark(daily, 7),
                 help="Daily average times the number of days."),
            dict(label="Likely range (80%)", value=f"±{half_pct:.1f}%",
                 context=range_text(first["low"], first["high"]), spark=None,
                 help="Range for that month's total."),
            dict(label="Next 3 months", value=ui.format_crore(t_total),
                 context=range_text(t_low, t_high), spark=spark(daily, 7),
                 help="All three months together."),
            dict(label="Past monthly error", value=f"{mape:.1f}%" if mape is not None else "n/a",
                 context=f"average miss over {n_months} months" if n_months else "not enough months",
                 spark=None, help="How far this method was from each completed month."),
        ]

    for column, card in zip(st.columns(4, gap="medium"), cards):
        with column:
            st.markdown(
                ui.kpi_card(
                    card["label"], card["value"],
                    delta_text=card.get("delta_text"), tone=card.get("tone", "flat"),
                    context=card["context"], spark=card["spark"], help=card["help"],
                    reserve_space=True,
                ),
                unsafe_allow_html=True,
            )


def render_forecast_panel(horizon, ctx):
    daily = ctx["daily"]
    with st.container(key="sv_panel_fc_chart"):
        title_col, picker_col = st.columns([1, 1], vertical_alignment="center")

        window = 90
        if horizon != "Next 3 months":
            with picker_col:
                label = st.segmented_control(
                    "History shown", list(HISTORY_WINDOWS), default="90 days",
                    key="fc_window", label_visibility="collapsed", width="stretch",
                ) or "90 days"
                window = HISTORY_WINDOWS[label]

        title, subtitle = {
            "Next day": ("Next-day forecast", "The diamond is the forecast, the bar is the likely range"),
            "Next 30 days": ("Next 30 days", "The shaded band is where a single day is likely to land"),
            "Next 3 months": ("Next 3 months", "Monthly totals with the likely range; the last 12 months for context"),
        }[horizon]
        with title_col:
            st.markdown(ui.panel_title(title, subtitle), unsafe_allow_html=True)

        if horizon == "Next day":
            fig = next_day_figure(daily, window, ctx["fc"])
        elif horizon == "Next 30 days":
            fig = next_30_figure(daily, window, ctx["level"], ctx["day_low"], ctx["day_high"])
        else:
            fig = months_figure(daily, ctx["periods"])
        st.plotly_chart(fig, key="fc_forecast_chart", config={"displayModeBar": False})


def verdict_text(bt):
    label = bt["model_label"]
    metrics = bt["metrics"]
    baselines = {k: v for k, v in metrics.items() if k != label}
    best_name = min(baselines, key=lambda k: baselines[k]["MAE"])
    best = baselines[best_name]["MAE"]
    mine = metrics[label]["MAE"]
    gap = (best - mine) / best * 100 if best else 0

    if gap >= 3:
        return "The model adds value.", (
            f"Its typical daily miss is {gap:.0f}% smaller than the best simple average "
            f"({best_name.lower()})."
        )
    if gap > -3:
        return "No real edge over an average.", (
            f"The model misses by {ui.format_compact_inr(mine)} a day, about the same as the "
            f"{best_name.lower()} ({ui.format_compact_inr(best)}). Extra complexity buys nothing here."
        )
    return "A simple average does better.", (
        f"The {best_name.lower()} misses by {ui.format_compact_inr(best)} a day against "
        f"{ui.format_compact_inr(mine)} for the model."
    )


def why_text(daily, orders):
    a1, a7 = daily.autocorr(1), daily.autocorr(7)
    mean_orders = orders.mean()
    ratio = orders.var() / mean_orders if mean_orders else np.nan

    if abs(a1) < 0.15 and abs(a7) < 0.15:
        text = (
            f"One day says almost nothing about the next: the correlation with the previous day is "
            f"{a1:.2f}, and {a7:.2f} a week apart."
        )
        if np.isfinite(ratio):
            text += (
                f" Daily order counts vary almost exactly like random arrivals "
                f"(variance divided by mean is {ratio:.2f})."
            )
        return text
    return (
        f"Sales show some day-to-day pattern (correlation {a1:.2f} with the previous day), "
        "so recent days carry useful information."
    )


def render_performance(ctx):
    bt, daily = ctx["bt"], ctx["daily"]
    metrics = bt["metrics"]

    left, right = st.columns([3, 2], gap="medium")
    with left:
        with st.container(key="sv_panel_fc_backtest"):
            st.markdown(
                ui.panel_title(
                    "How well did it do?",
                    f"{bt['n_test']} days the model had not seen, "
                    f"{ui.format_date(bt['actual'].index[0])} to {ui.format_date(bt['actual'].index[-1])}",
                ),
                unsafe_allow_html=True,
            )
            st.plotly_chart(backtest_figure(bt), key="fc_backtest_chart", config={"displayModeBar": False})
            st.markdown(
                ui.insight_note(
                    f"The 80% range contained the actual sales on {bt['coverage']:.0f}% of these days "
                    "(a well-calibrated range gives about 80%)."
                ),
                unsafe_allow_html=True,
            )

    with right:
        with st.container(key="sv_panel_fc_models"):
            st.markdown(
                ui.panel_title("Model vs simple averages", "Typical daily miss and % error. Lower is better"),
                unsafe_allow_html=True,
            )
            ranked = sorted(metrics.items(), key=lambda kv: kv[1]["MAE"])
            worst = max(m["MAE"] for _, m in ranked) or 1.0
            rows = [
                (name, ui.format_compact_inr(m["MAE"]), m["MAPE"], m["MAE"] / worst * 100)
                for name, m in ranked
            ]
            st.markdown(ui.ranked_bars(rows, highlight=0, compact=True), unsafe_allow_html=True)

            lead, text = verdict_text(bt)
            st.markdown(ui.insight_note(text, lead), unsafe_allow_html=True)
            st.markdown(ui.insight_note(why_text(daily, ctx["orders"]), "Why:"), unsafe_allow_html=True)


def render_details(ctx):
    daily, fc, artifact = ctx["daily"], ctx["fc"], ctx["artifact"]

    with st.expander("Recent days and the forecast", expanded=False):
        recent = daily.tail(14)
        table = pd.DataFrame({
            "Date": list(recent.index) + [fc["date"]],
            "Type": ["Actual"] * len(recent) + ["Forecast"],
            "Sales": list(recent / 1e5) + [fc["point"] / 1e5],
            "Low": [None] * len(recent) + [fc["low"] / 1e5],
            "High": [None] * len(recent) + [fc["high"] / 1e5],
        })
        st.dataframe(
            table.iloc[::-1],
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "Type": st.column_config.TextColumn("Type"),
                "Sales": st.column_config.NumberColumn("Sales", format="₹%.2f lakh"),
                "Low": st.column_config.NumberColumn("Range low", format="₹%.1f lakh"),
                "High": st.column_config.NumberColumn("Range high", format="₹%.1f lakh"),
            },
            hide_index=True, width="stretch",
        )

    with st.expander("How the forecast is made", expanded=False):
        name = artifact.get("model_name", "Linear regression") if artifact else "not loaded"
        features = ", ".join(artifact["features"]) if artifact else ", ".join(DEFAULT_FEATURES)
        st.markdown(
            f"**Next day:** the saved model ({name}) uses the day of the week, the day of the year, sales "
            "1, 7, 14 and 30 days ago, and the 7-day and 30-day averages.  \n"
            f"**Features:** {features}  \n"
            f"**Longer horizons:** the average of the last {LEVEL_DAYS} days, with a range from resampling past days. "
            "The model was only validated one day ahead.  \n"
            "**Accuracy check:** the same recipe is refit on the first 80% of days and scored on the last 20%, "
            "because the saved model has already seen every day."
        )


# ==================================================
# 6. MAIN ENTRY POINT
# ==================================================
def render(sales, customers, products, context=None):
    """
    Render the Forecasting page.

    `context` is {"full_sales", "start", "end", "states"} from app.py. The forecast
    uses full_sales (all states, all dates) whatever the sidebar filters say.
    """
    full = context.get("full_sales") if context and context.get("full_sales") is not None else sales
    if full is None or full.empty or not {"Order_Date", "Order_Status", "Total_Amount"}.issubset(full.columns):
        st.warning("The sales data needed for forecasting is not available.")
        return

    version = (len(full), str(full["Order_Date"].max()))
    daily, orders = load_history(full, version)
    if len(daily) < MIN_HISTORY_DAYS:
        st.warning(f"At least {MIN_HISTORY_DAYS} days of delivered sales are needed; found {len(daily)}.")
        return

    artifact, load_error = try_load_artifact()
    if artifact is not None:
        features = list(artifact["features"])
        missing = [f for f in features if f not in build_features(daily.head(40)).columns]
        if missing:
            artifact, load_error = None, f"Unknown features in the saved model: {', '.join(missing)}"
    if artifact is None:
        features = DEFAULT_FEATURES

    model_label = (artifact or {}).get("model_name", "Linear model")
    bt = run_backtest(daily, features, model_label)
    band = production_band(bt)
    fc = next_day_forecast(daily, artifact, band)
    level, day_low, day_high = level_day_range(daily)

    # ---- header and horizon switch
    lead = (
        f"Expect about {ui.format_compact_inr(level)} a day, usually between "
        f"{range_text(day_low, day_high).replace(' to ', ' and ', 1)}."
    )
    if abs(daily.autocorr(1)) < 0.15 and abs(daily.autocorr(7)) < 0.15:
        lead += " Daily sales are close to random around that level, so ranges and monthly totals are more reliable than any single-day number."

    head_col, pick_col = st.columns([5, 4], vertical_alignment="bottom")
    with head_col:
        st.markdown(ui.page_header("Sales forecast", lead), unsafe_allow_html=True)
    with pick_col:
        horizon = st.segmented_control(
            "Forecast horizon", HORIZONS, default="Next day",
            key="fc_horizon", label_visibility="collapsed", width="stretch",
        ) or "Next day"

    if artifact is None:
        st.warning(
            "The saved forecasting model could not be loaded, so the forecast uses the 365-day average "
            f"instead. Details: {load_error}"
        )
    if filters_active(context):
        st.markdown(
            ui.insight_note("Forecasts use all states and all dates. The sidebar filters do not change this page.", "Filters off."),
            unsafe_allow_html=True,
        )

    # ---- numbers for the chosen horizon
    ctx = {"daily": daily, "orders": orders, "fc": fc, "bt": bt, "artifact": artifact,
           "level": level, "day_low": day_low, "day_high": day_high}
    recent_year = daily.tail(LEVEL_DAYS).to_numpy()
    if horizon == "Next 30 days":
        ctx["total30"] = bootstrap_total(recent_year, 30)
        ctx["total30"] = (level * 30, ctx["total30"][1], ctx["total30"][2])
    elif horizon == "Next 3 months":
        periods = month_periods(daily.index[-1])
        for p in periods:
            _, p["low"], p["high"] = bootstrap_total(recent_year, p["days"])
            p["expected"] = level * p["days"]
        ctx["periods"] = periods
        _, t_low, t_high = bootstrap_total(recent_year, sum(p["days"] for p in periods))
        ctx["total3"] = (level * sum(p["days"] for p in periods), t_low, t_high)
        ctx["month_error"] = monthly_backtest(daily)

    render_kpis(horizon, ctx)
    render_forecast_panel(horizon, ctx)
    render_performance(ctx)
    render_details(ctx)

    st.caption(
        "Forecasts are estimates from past delivered sales (recorded Total Amount, not profit). Promotions, "
        "holidays and stock levels are not in the data. Ranges show where 8 out of 10 outcomes landed in the past."
    )
