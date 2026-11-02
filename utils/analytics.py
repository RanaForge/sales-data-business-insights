"""
Shared data preparation and period comparison for the dashboard pages.

Moved out of views/overview.py so Overview and Sales Analysis use the same
definitions (what "delivered" means, how weeks are cut, how the previous
period is found) and therefore always agree with each other.
"""
import pandas as pd

BASE_COLUMNS = ["Order_Date", "Order_Status", "Total_Amount", "Category", "State"]
WEEK_RULE = dict(rule="W-MON", label="left", closed="left")   # weeks start on Monday

_NUMERIC_EXTRA = ["Order_Value", "Coupon_Discount"]
_TEXT_EXTRA = ["Payment_Mode"]


# --------------------------------------------------
# 1. Preparation
# --------------------------------------------------
def prepare_sales(sales, extra=()):
    """
    Keep only the columns a page needs and normalise them once.

    `extra` lists additional columns (e.g. Payment_Mode, Product_ID) that are
    kept when they exist in the data.
    """
    wanted = list(dict.fromkeys(BASE_COLUMNS + list(extra)))
    cols = [c for c in wanted if c in sales.columns]
    df = sales[cols].copy()

    df["Order_Status"] = (
        df["Order_Status"].astype("string").fillna("unknown")
        .str.strip().str.lower()
    )
    df["Total_Amount"] = pd.to_numeric(df["Total_Amount"], errors="coerce").fillna(0)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")

    if "Category" in df.columns:
        df["Category"] = (
            df["Category"].fillna("Unknown").astype(str).str.strip()
            .replace("", "Unknown")
        )
    for column in _TEXT_EXTRA:
        if column in df.columns:
            df[column] = (
                df[column].fillna("Unknown").astype(str).str.strip()
                .replace("", "Unknown")
            )
    for column in _NUMERIC_EXTRA:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    if "Delivery_Date" in df.columns:
        df["Delivery_Date"] = pd.to_datetime(df["Delivery_Date"], errors="coerce")

    return df


def summarize(df):
    """Headline numbers for one slice of orders (delivered-sales definition)."""
    status = df["Order_Status"]
    delivered = df[status.eq("delivered")]
    n_orders = len(df)
    n_delivered = len(delivered)
    sales_amount = float(delivered["Total_Amount"].sum())

    return {
        "sales": sales_amount,
        "orders": n_orders,
        "aov": sales_amount / n_delivered if n_delivered else 0.0,
        "return_rate": status.eq("returned").sum() / n_orders * 100 if n_orders else 0.0,
        "delivery_rate": n_delivered / n_orders * 100 if n_orders else 0.0,
    }


# --------------------------------------------------
# 2. Previous period
# --------------------------------------------------
def previous_period_slice(context):
    """
    Raw rows of the period of equal length right before the selected dates,
    with the same state filter. Returns (rows, n_days), or None when the
    earlier period is not fully covered by the data (for example 'All').

    `context` is {"full_sales", "start", "end", "states"} built in app.py.
    """
    if not context:
        return None

    full = context.get("full_sales")
    start, end = context.get("start"), context.get("end")
    states = context.get("states")
    if full is None or start is None or end is None:
        return None

    start, end = pd.Timestamp(start), pd.Timestamp(end)
    n_days = (end - start).days + 1
    prev_end = start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=n_days - 1)

    data_min = full["Order_Date"].min()
    if pd.isna(data_min) or prev_start < data_min:
        return None

    mask = full["Order_Date"].between(prev_start, prev_end)
    if states is not None:
        mask &= full["State"].astype(str).isin(states)

    previous = full.loc[mask]
    if previous.empty:
        return None
    return previous, n_days


def previous_period_summary(context):
    """(summary, n_days) of the previous period using the delivered definition."""
    result = previous_period_slice(context)
    if result is None:
        return None
    rows, n_days = result
    return summarize(prepare_sales(rows)), n_days


def period_label(n_days):
    """'prior 30 days' / 'prior 12 months' wording for change chips."""
    if n_days <= 90:
        return f"vs prior {n_days} days"
    return f"vs prior {round(n_days / 30.44)} months"


# --------------------------------------------------
# 3. Weekly series for KPI sparklines (delivered definition)
# --------------------------------------------------
def weekly_series(df):
    """Weekly values that feed the Overview sparklines (edge weeks dropped)."""
    d = df.dropna(subset=["Order_Date"]).set_index("Order_Date")
    delivered = d[d["Order_Status"].eq("delivered")]

    weekly = pd.DataFrame({
        "sales": delivered["Total_Amount"].resample(**WEEK_RULE).sum(),
        "delivered_n": delivered["Total_Amount"].resample(**WEEK_RULE).size(),
        "orders": d["Total_Amount"].resample(**WEEK_RULE).size(),
        "returned": d["Order_Status"].eq("returned").resample(**WEEK_RULE).sum(),
    }).fillna(0)

    weekly["aov"] = weekly["sales"] / weekly["delivered_n"].where(weekly["delivered_n"] > 0)
    weekly["return_rate"] = weekly["returned"] / weekly["orders"].where(weekly["orders"] > 0) * 100

    if len(weekly) >= 6:
        weekly = weekly.iloc[1:-1]
    return weekly
