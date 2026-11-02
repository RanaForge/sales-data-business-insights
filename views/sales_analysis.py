"""
Sales Analysis page: a deeper look than the Overview.

The Overview answers "how are we doing?". This page answers:
    what sells            category and top products / brands
    how big are orders    order-size bands, median vs average
    how customers pay     payment modes and coupons
    where                 states
    how orders are fulfilled   delivery time and outcome check

A scope switch (Delivered / All orders) controls every number on the page
except the delivery-time and outcome panels, which have their own definition.
Delivered is the default so the totals agree with the Overview.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils import ui
from utils.analytics import (
    WEEK_RULE,
    period_label,
    prepare_sales,
    previous_period_slice,
)

EXTRA_COLUMNS = [
    "Order_ID", "Payment_Mode", "Product_ID", "Delivery_Date",
    "Order_Value", "Coupon_Discount",
]
SCOPES = ["Delivered", "All orders"]

# (lower edge, upper edge, label) in rupees
SIZE_BANDS = [
    (0, 1_000, "Under ₹1K"),
    (1_000, 5_000, "₹1K to ₹5K"),
    (5_000, 20_000, "₹5K to ₹20K"),
    (20_000, 50_000, "₹20K to ₹50K"),
    (50_000, 100_000, "₹50K to ₹1L"),
    (100_000, np.inf, "Over ₹1L"),
]


# ==================================================
# 1. DATA HELPERS
# ==================================================
def apply_scope(df, scope):
    """Delivered orders only, or every order."""
    if scope == "Delivered":
        return df[df["Order_Status"].eq("delivered")]
    return df


def scope_stats(d):
    n = len(d)
    total = float(d["Total_Amount"].sum())
    return {
        "sales": total,
        "orders": n,
        "mean": total / n if n else 0.0,
        "median": float(d["Total_Amount"].median()) if n else 0.0,
    }


def weekly_scope_series(d):
    """Weekly sales, orders, mean and median order for the KPI sparklines."""
    amounts = d.dropna(subset=["Order_Date"]).set_index("Order_Date")["Total_Amount"]
    grouped = amounts.resample(**WEEK_RULE)
    weekly = pd.DataFrame({
        "sales": grouped.sum(),
        "orders": grouped.size(),
        "mean": grouped.mean(),
        "median": grouped.median(),
    })
    if len(weekly) >= 6:                      # drop partial weeks at both ends
        weekly = weekly.iloc[1:-1]
    return weekly


def top_decile_share(d):
    """Share of total amount that comes from the largest 10% of orders."""
    amounts = np.sort(d["Total_Amount"].to_numpy())[::-1]
    total = amounts.sum()
    if len(amounts) == 0 or total <= 0:
        return 0.0
    k = max(1, int(np.ceil(len(amounts) * 0.10)))
    return float(amounts[:k].sum() / total * 100)


def ranked_rows(grouped_amount, grouped_orders, limit):
    """Rows for ui.ranked_bars from per-group amount and order count."""
    order = grouped_amount.sort_values(ascending=False)
    total = float(grouped_amount.sum())
    top = order.iloc[0] if len(order) else 0
    rows = []
    for name in order.index[:limit]:
        amount = float(grouped_amount[name])
        orders = int(grouped_orders[name])
        rows.append((
            str(name),
            ui.format_crore(amount),
            amount / total * 100 if total else 0.0,
            amount / top * 100 if top else 0.0,
            ui.format_compact_inr(amount / orders) if orders else "–",
        ))
    return rows


# ==================================================
# 2. HEADER AND KPI CARDS
# ==================================================
def scope_picker():
    choice = st.segmented_control(
        "Order scope",
        SCOPES,
        default="Delivered",
        key="sa_scope",
        label_visibility="collapsed",
        width="stretch",
    )
    return choice or "Delivered"


def render_header(scope, stats, decile):
    amount_text = ui.format_crore(stats["sales"])
    if scope == "Delivered":
        lead = f"Delivered sales of {amount_text} from {stats['orders']:,} orders."
    else:
        lead = (
            f"Order value of {amount_text} across all {stats['orders']:,} orders, "
            "including cancelled, returned and unfinished ones."
        )
    lead += (
        f" The typical order is {ui.format_compact_inr(stats['median'])}, "
        f"but the largest 10% of orders bring in {decile:.0f}% of the total."
    )
    st.markdown(ui.page_header("Sales analysis", lead), unsafe_allow_html=True)


def render_kpis(scope, current, previous, n_days, weekly):
    sales_label = "Delivered sales" if scope == "Delivered" else "Order value"
    period_text = period_label(n_days) if previous else "Weekly trend"

    cards = [
        (sales_label, ui.format_crore(current["sales"]), "sales",
         "Sum of Total_Amount for the orders in scope."),
        ("Orders", f"{current['orders']:,}", "orders",
         "Number of orders in scope."),
        ("Average order", f"₹{current['mean']:,.0f}", "mean",
         "Total amount divided by orders. Pulled up by a few very large orders."),
        ("Median order", f"₹{current['median']:,.0f}", "median",
         "Half of all orders are smaller than this."),
    ]

    for column, (label, value, key, help_text) in zip(st.columns(4, gap="medium"), cards):
        delta_text, tone = (None, "flat")
        if previous:
            delta_text, tone = ui.change_chip(current[key], previous[key])
        with column:
            st.markdown(
                ui.kpi_card(
                    label, value, delta_text=delta_text, tone=tone,
                    context=period_text, spark=weekly[key], help=help_text,
                ),
                unsafe_allow_html=True,
            )


# ==================================================
# 3. WHAT SELLS
# ==================================================
def render_categories(d, scope):
    amount_header = "Sales" if scope == "Delivered" else "Value"
    with st.container(key="sv_panel_sa_category"):
        st.markdown(
            ui.panel_title("Sales by category", "Share of the total, with the average order size"),
            unsafe_allow_html=True,
        )
        if "Category" not in d.columns or d.empty:
            st.info("No category data for this selection.")
            return

        grouped = d.groupby("Category")["Total_Amount"].agg(["sum", "size"])
        rows = ranked_rows(grouped["sum"], grouped["size"], limit=8)
        st.markdown(
            ui.ranked_bars(rows, headers=(amount_header, "Share", "Avg order")),
            unsafe_allow_html=True,
        )


def render_top_items(d, products, scope):
    with st.container(key="sv_panel_sa_top"):
        title_col, picker_col = st.columns([1, 1], vertical_alignment="center")
        with picker_col:
            mode = st.segmented_control(
                "Rank by", ["Products", "Brands"], default="Products",
                key="sa_top_mode", label_visibility="collapsed", width="stretch",
            ) or "Products"
        with title_col:
            st.markdown(
                ui.panel_title(f"Top {mode.lower()}", "Highest sales in this selection"),
                unsafe_allow_html=True,
            )

        needed = {"Product_ID", "Product_Name", "Brand"}
        if "Product_ID" not in d.columns or products is None or not needed.issubset(products.columns):
            st.info("Product details are not available.")
            return
        if d.empty:
            st.info("No orders for this selection.")
            return

        info = products.drop_duplicates("Product_ID").set_index("Product_ID")
        label_column = "Product_Name" if mode == "Products" else "Brand"

        per_product = d.groupby("Product_ID")["Total_Amount"].agg(["sum", "size"])
        labels = per_product.index.map(info[label_column])
        grouped = (
            pd.DataFrame(
                {"sum": per_product["sum"].to_numpy(), "size": per_product["size"].to_numpy()},
                index=labels,
            )
            .groupby(level=0).sum()
        )
        if grouped.empty:
            st.info("No matching product details.")
            return

        rows = ranked_rows(grouped["sum"], grouped["size"], limit=7)
        amount_header = "Sales" if scope == "Delivered" else "Value"
        st.markdown(
            ui.ranked_bars(rows, headers=(amount_header, "Share", "Avg order")),
            unsafe_allow_html=True,
        )


# ==================================================
# 4. ORDER SIZE AND PAYMENT
# ==================================================
def render_order_size(d, stats, decile):
    with st.container(key="sv_panel_sa_size"):
        st.markdown(
            ui.panel_title("Order size", "How orders and sales are spread across order values"),
            unsafe_allow_html=True,
        )
        if d.empty or stats["sales"] <= 0:
            st.info("No orders for this selection.")
            return

        edges = [low for low, _, _ in SIZE_BANDS] + [np.inf]
        labels = [label for _, _, label in SIZE_BANDS]
        bands = pd.cut(d["Total_Amount"], bins=edges, labels=labels, right=False)

        orders_share = bands.value_counts(normalize=True).reindex(labels).fillna(0) * 100
        sales_share = (
            d.groupby(bands, observed=False)["Total_Amount"].sum()
            .reindex(labels).fillna(0) / stats["sales"] * 100
        )

        rows = [(label, float(orders_share[label]), float(sales_share[label])) for label in labels]
        st.markdown(ui.paired_bars(rows), unsafe_allow_html=True)
        st.markdown(
            ui.insight_note(
                f"The largest 10% of orders account for {decile:.0f}% of sales. "
                f"The median order is {ui.format_compact_inr(stats['median'])} "
                f"against an average of {ui.format_compact_inr(stats['mean'])}.",
            ),
            unsafe_allow_html=True,
        )


def render_payment(d):
    with st.container(key="sv_panel_sa_payment"):
        st.markdown(
            ui.panel_title("How customers pay", "Share of orders against share of sales"),
            unsafe_allow_html=True,
        )
        if "Payment_Mode" not in d.columns or d.empty:
            st.info("No payment data for this selection.")
            return

        grouped = d.groupby("Payment_Mode")["Total_Amount"].agg(["size", "sum"])
        grouped = grouped.sort_values("size", ascending=False)
        orders_share = grouped["size"] / grouped["size"].sum() * 100
        sales_share = grouped["sum"] / grouped["sum"].sum() * 100 if grouped["sum"].sum() > 0 else grouped["sum"] * 0

        rows = [(mode, float(orders_share[mode]), float(sales_share[mode])) for mode in grouped.index]
        st.markdown(ui.paired_bars(rows), unsafe_allow_html=True)

        if {"Coupon_Discount", "Order_Value"}.issubset(d.columns):
            used = (d["Coupon_Discount"] > 0).mean() * 100
            order_value = d["Order_Value"].sum()
            cost = d["Coupon_Discount"].sum() / order_value * 100 if order_value > 0 else 0.0
            st.markdown(
                ui.stat_row([
                    ("Orders with a coupon", f"{used:.1f}%", "of orders in scope"),
                    ("Coupon cost", f"{cost:.1f}%", "of order value"),
                ]),
                unsafe_allow_html=True,
            )


# ==================================================
# 5. STATES AND FULFILMENT
# ==================================================
def render_states(d, scope):
    amount_header = "Sales" if scope == "Delivered" else "Value"
    with st.container(key="sv_panel_sa_states"):
        st.markdown(
            ui.panel_title("Sales by state", "States in the current filter"),
            unsafe_allow_html=True,
        )
        if "State" not in d.columns or d.empty:
            st.info("No state data for this selection.")
            return

        grouped = d.groupby("State")["Total_Amount"].agg(["sum", "size"])
        rows = ranked_rows(grouped["sum"], grouped["size"], limit=10)
        st.markdown(
            ui.ranked_bars(rows, headers=(amount_header, "Share", "Avg order")),
            unsafe_allow_html=True,
        )
        if len(grouped) > 10:
            rest = grouped["sum"].sort_values(ascending=False).iloc[10:].sum() / grouped["sum"].sum() * 100
            st.caption(f"The other {len(grouped) - 10} states together make up {rest:.1f}%.")


def outcome_note(df):
    """Plain-language check of whether any state stands out on returns/cancellations."""
    if "State" not in df.columns or df["State"].nunique() < 2:
        return None

    flagged = df["Order_Status"].isin(["returned", "cancelled"])
    by_state = flagged.groupby(df["State"]).agg(["mean", "size"])
    by_state = by_state[by_state["size"] >= 100]
    if len(by_state) < 2:
        return None

    rate = by_state["mean"] * 100
    low_state, high_state = rate.idxmin(), rate.idxmax()
    low, high = float(rate.min()), float(rate.max())
    text = (
        f"Returned or cancelled orders range from {low:.1f}% ({low_state}) "
        f"to {high:.1f}% ({high_state}) across states"
    )
    text += (
        ", so no state stands out." if high - low < 1.5
        else f". {high_state} is the highest."
    )
    return text


def render_fulfilment(df):
    """Delivery time (delivered orders) and an outcome check (all orders)."""
    with st.container(key="sv_panel_sa_delivery"):
        st.markdown(
            ui.panel_title("Delivery time", "Days from order to delivery, delivered orders"),
            unsafe_allow_html=True,
        )

        delivered = df[df["Order_Status"].eq("delivered")]
        if "Delivery_Date" not in delivered.columns or delivered.empty:
            st.info("Delivery dates are not available for this selection.")
        else:
            days = (delivered["Delivery_Date"] - delivered["Order_Date"]).dt.days.dropna()
            days = days[days >= 0].astype(int)
            if days.empty:
                st.info("Delivery dates are not available for this selection.")
            else:
                counts = days.value_counts().sort_index()
                top = counts.max()
                rows = [
                    (f"{day} day{'s' if day != 1 else ''}", f"{count:,}",
                     count / len(days) * 100, count / top * 100)
                    for day, count in counts.items()
                ]
                peak = int(np.argmax(counts.to_numpy()))
                st.markdown(
                    ui.ranked_bars(rows, highlight=peak, headers=("Orders", "Share")),
                    unsafe_allow_html=True,
                )
                within = (days <= 5).mean() * 100
                st.markdown(
                    ui.stat_row([
                        ("Average", f"{days.mean():.1f} days", ""),
                        ("Delivered within 5 days", f"{within:.0f}%", "of delivered orders"),
                    ]),
                    unsafe_allow_html=True,
                )

        note = outcome_note(df)
        if note:
            st.markdown(ui.insight_note(note), unsafe_allow_html=True)


# ==================================================
# 6. DETAIL TABLE
# ==================================================
def render_table(d):
    with st.expander("View the orders behind these numbers", expanded=False):
        columns = [
            c for c in ["Order_ID", "Order_Date", "State", "Category",
                        "Payment_Mode", "Order_Status", "Total_Amount"]
            if c in d.columns
        ]
        if not columns:
            st.info("No columns are available to display.")
            return

        max_rows = 5000
        shown = d[columns].head(max_rows).copy()
        shown["Order_Status"] = shown["Order_Status"].str.title()

        config = {
            "Order_ID": st.column_config.TextColumn("Order ID"),
            "Order_Date": st.column_config.DateColumn("Order date", format="DD MMM YYYY"),
            "State": st.column_config.TextColumn("State"),
            "Category": st.column_config.TextColumn("Category"),
            "Payment_Mode": st.column_config.TextColumn("Payment"),
            "Order_Status": st.column_config.TextColumn("Status"),
            "Total_Amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
        }
        st.dataframe(
            shown,
            column_config={k: v for k, v in config.items() if k in shown.columns},
            hide_index=True,
            height=380,
            width="stretch",
        )
        if len(d) > max_rows:
            st.caption(f"Showing the first {max_rows:,} of {len(d):,} orders in scope.")
        else:
            st.caption(f"Showing all {len(d):,} orders in scope.")


# ==================================================
# 7. MAIN ENTRY POINT
# ==================================================
def render(sales, customers, products, context=None):
    """
    Render the Sales Analysis page.

    `context` lets the KPI cards compare with the previous period:
        {"full_sales": sales, "start": start_date, "end": end_date, "states": selected_states}
    """
    if sales.empty:
        st.warning("No sales records match the selected date and state filters.")
        return
    if not {"Order_Status", "Total_Amount"}.issubset(sales.columns):
        st.error("The sales data must contain Order_Status and Total_Amount.")
        return

    df = prepare_sales(sales, extra=EXTRA_COLUMNS)

    head_col, pick_col = st.columns([3, 2], vertical_alignment="bottom")
    with pick_col:
        scope = scope_picker()

    d = apply_scope(df, scope)
    stats = scope_stats(d)
    decile = top_decile_share(d)

    with head_col:
        if d.empty:
            st.markdown(ui.page_header("Sales analysis", "No orders match this scope."), unsafe_allow_html=True)
        else:
            render_header(scope, stats, decile)

    if d.empty:
        st.info("There are no orders in the selected scope. Try All orders or widen the filters.")
        return

    # KPI cards with change versus the previous period
    previous_stats, n_days = None, 0
    previous = previous_period_slice(context)
    if previous:
        raw_rows, n_days = previous
        previous_d = apply_scope(prepare_sales(raw_rows, extra=EXTRA_COLUMNS), scope)
        if not previous_d.empty:
            previous_stats = scope_stats(previous_d)
    render_kpis(scope, stats, previous_stats, n_days, weekly_scope_series(d))

    # What sells
    left, right = st.columns(2, gap="medium")
    with left:
        render_categories(d, scope)
    with right:
        render_top_items(d, products, scope)

    # Order size and payment
    left, right = st.columns(2, gap="medium")
    with left:
        render_order_size(d, stats, decile)
    with right:
        render_payment(d)

    # States and fulfilment
    left, right = st.columns(2, gap="medium")
    with left:
        render_states(d, scope)
    with right:
        render_fulfilment(df)

    render_table(d)

    scope_note = (
        "Delivered orders only." if scope == "Delivered"
        else "All orders, including cancelled, returned and unfinished ones."
    )
    st.caption(
        f"{scope_note} Amounts are recorded Total Amount (order value minus coupon plus shipping), "
        "not profit or audited revenue. Delivery time and the outcome check use their own order sets, "
        "as stated in each panel."
    )
