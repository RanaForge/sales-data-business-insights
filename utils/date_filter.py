
import calendar
from datetime import date, timedelta

import streamlit as st


def render_date_filter(min_date, max_date):
    """Render a custom date-range calendar for SalesVision."""

    # --------------------------------------------------
    # 1. Initialize calendar state
    # --------------------------------------------------
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = max_date.replace(day=1)

    if "filter_start" not in st.session_state:
        st.session_state.filter_start = min_date

    if "filter_end" not in st.session_state:
        st.session_state.filter_end = max_date

    if "pending_start" not in st.session_state:
        st.session_state.pending_start = None

    if "custom_range_mode" not in st.session_state:
        st.session_state.custom_range_mode = False

    # Keep the selected dates within the available dataset range.
    st.session_state.filter_start = max(
        min_date,
        min(st.session_state.filter_start, max_date),
    )

    st.session_state.filter_end = max(
        st.session_state.filter_start,
        min(st.session_state.filter_end, max_date),
    )

    # Keep the calendar month within the available data range.
    current_month = st.session_state.calendar_month

    if current_month < min_date.replace(day=1):
        st.session_state.calendar_month = min_date.replace(day=1)

    elif current_month > max_date.replace(day=1):
        st.session_state.calendar_month = max_date.replace(day=1)

    # --------------------------------------------------
    # 2. Calendar and dashboard styling
    # --------------------------------------------------
    st.markdown(
        """
        <style>
        /* Calendar headings */
        .calendar-title {
            color: #FFFFFF !important;
            font-size: 19px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .calendar-subtitle {
            color: #D7E0F5 !important;
            font-size: 12px;
            margin-bottom: 14px;
        }

        /* Selected date card */
        .calendar-selected {
            background: #FFFFFF !important;
            border: 1px solid #DCE5F2;
            border-radius: 12px;
            padding: 12px;
            margin: 12px 0;
            color: #172554 !important;
            line-height: 1.8;
        }

        .calendar-selected span {
            color: #64748B !important;
            font-size: 11px;
        }

        .calendar-selected strong {
            color: #172554 !important;
            font-size: 14px;
        }

        /* Custom range instructions */
        .calendar-instructions {
            background: #E0E7FF !important;
            color: #312E81 !important;
            border-radius: 9px;
            padding: 10px;
            font-size: 12px;
            margin: 10px 0;
        }

        /* Weekday labels */
        .calendar-weekday {
            text-align: center;
            color: #FFFFFF !important;
            font-size: 11px;
            font-weight: 700;
            padding: 5px 0 8px 0;
        }

        /* Calendar day buttons */
        [data-testid="stSidebar"] div[data-testid="stButton"] button {
            min-height: 36px;
            padding: 0;
            border-radius: 9px;
            border: 1px solid #DCE5F2 !important;
            background: #FFFFFF !important;
            color: #172554 !important;
            font-size: 13px;
            font-weight: 600;
        }

        [data-testid="stSidebar"] div[data-testid="stButton"] button p {
            color: #172554 !important;
        }

        [data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
            background: #E0E7FF !important;
            border-color: #6366F1 !important;
        }

        /* Dropdown labels */
        [data-testid="stSidebar"] label {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* Month/year dropdowns */
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border-color: #CBD5E1 !important;
            color: #172554 !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] input {
            color: #172554 !important;
            -webkit-text-fill-color: #172554 !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] div,
        [data-testid="stSidebar"] [data-baseweb="select"] span {
            color: #172554 !important;
        }

        /* Month heading */
        .calendar-month-label {
            color: #FFFFFF !important;
            text-align: center;
            font-weight: 700;
        }
        
        
        /* Force a visible indigo sidebar toggle */
        [data-testid="stSidebarCollapsedControl"] {
            background-color: #4F46E5 !important;
            border-radius: 10px !important;
            opacity: 1 !important;
            box-shadow: 0 3px 10px rgba(79, 70, 229, 0.35) !important;
        }

        [data-testid="stSidebarCollapsedControl"] > button,
        [data-testid="stSidebarCollapsedControl"] button {
            background-color: #4F46E5 !important;
            color: #FFFFFF !important;
            opacity: 1 !important;
            border: 1px solid #4338CA !important;
            border-radius: 10px !important;
        }

        /* Streamlit may render the arrow using an SVG icon */
        [data-testid="stSidebarCollapsedControl"] svg {
            color: #FFFFFF !important;
            stroke: #FFFFFF !important;
            opacity: 1 !important;
        }

        /* Keep the arrow visible on hover */
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stSidebarCollapsedControl"] button:hover {
            background-color: #3730A3 !important;
        }


        </style>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # 3. Heading
    # --------------------------------------------------
    st.markdown(
        '<div class="calendar-title">Date range</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="calendar-subtitle">'
        'Filter dashboard data by order date'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # 4. Quick date presets
    # --------------------------------------------------
    p1, p2 = st.columns(2)

    if p1.button(
        "Last 7 days",
        key="preset_7",
        use_container_width=True,
    ):
        st.session_state.filter_end = max_date
        st.session_state.filter_start = max(
            min_date,
            max_date - timedelta(days=6),
        )
        st.session_state.pending_start = None
        st.session_state.custom_range_mode = False
        st.rerun()

    if p2.button(
        "Last 30 days",
        key="preset_30",
        use_container_width=True,
    ):
        st.session_state.filter_end = max_date
        st.session_state.filter_start = max(
            min_date,
            max_date - timedelta(days=29),
        )
        st.session_state.pending_start = None
        st.session_state.custom_range_mode = False
        st.rerun()

    p3, p4 = st.columns(2)

    if p3.button(
        "This month",
        key="preset_month",
        use_container_width=True,
    ):
        st.session_state.filter_end = max_date
        st.session_state.filter_start = max(
            min_date,
            max_date.replace(day=1),
        )
        st.session_state.pending_start = None
        st.session_state.custom_range_mode = False
        st.rerun()

    if p4.button(
        "All dates",
        key="preset_all",
        use_container_width=True,
    ):
        st.session_state.filter_start = min_date
        st.session_state.filter_end = max_date
        st.session_state.pending_start = None
        st.session_state.custom_range_mode = False
        st.rerun()

    # --------------------------------------------------
    # 5. Custom date range selection
    # --------------------------------------------------
    if st.button(
        "✎  Custom date range",
        key="enable_custom_range",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state.custom_range_mode
            else "secondary"
        ),
    ):
        st.session_state.custom_range_mode = True
        st.session_state.pending_start = None
        st.rerun()

    start_date = st.session_state.filter_start
    end_date = st.session_state.filter_end

    st.markdown(
        f"""
        <div class="calendar-selected">
            <span>START DATE</span><br>
            <strong>{start_date.strftime("%d %b %Y")}</strong>
            <br>
            <span>END DATE</span><br>
            <strong>{end_date.strftime("%d %b %Y")}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.custom_range_mode:
        if st.session_state.pending_start is None:
            instruction = (
                "Select a start date, then select an end date."
            )
        else:
            instruction = (
                "Now select the end date. Start: "
                + st.session_state.pending_start.strftime("%d %b %Y")
            )

        st.markdown(
            f'<div class="calendar-instructions">{instruction}</div>',
            unsafe_allow_html=True,
        )

    # --------------------------------------------------
    # 6. Month and year dropdown navigation
    # --------------------------------------------------
    current_month = st.session_state.calendar_month

    available_years = list(range(min_date.year, max_date.year + 1))

    nav_col1, nav_col2 = st.columns([1, 1])

    with nav_col1:
        selected_year = st.selectbox(
            "Year",
            options=available_years,
            index=available_years.index(current_month.year),
            key="calendar_year_select",
        )

    months_for_year = [
        month
        for month in range(1, 13)
        if (
            date(selected_year, month, 1)
            <= max_date.replace(day=1)
            and (
                selected_year > min_date.year
                or month >= min_date.month
            )
        )
    ]

    with nav_col2:
        selected_month = st.selectbox(
            "Month",
            options=months_for_year,
            index=(
                months_for_year.index(current_month.month)
                if current_month.month in months_for_year
                else 0
            ),
            format_func=lambda month: calendar.month_name[month],
            key="calendar_month_select",
        )

    new_month = date(selected_year, selected_month, 1)

    if new_month != st.session_state.calendar_month:
        st.session_state.calendar_month = new_month
        st.rerun()

    current_month = st.session_state.calendar_month

    # Previous month button
    previous, month_label, next_month = st.columns([1, 4, 1])

    if previous.button(
        "‹",
        key="calendar_previous",
        use_container_width=True,
    ):
        if current_month.month == 1:
            new_month = date(current_month.year - 1, 12, 1)
        else:
            new_month = date(
                current_month.year,
                current_month.month - 1,
                1,
            )

        if new_month >= min_date.replace(day=1):
            st.session_state.calendar_month = new_month
            st.rerun()

    # Visible month and year label
    month_label.markdown(
        f"""
        <div class="calendar-month-label"
             style="padding-top:9px; font-size:14px;">
            {current_month.strftime("%B %Y")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Next month button
    if next_month.button(
        "›",
        key="calendar_next",
        use_container_width=True,
    ):
        if current_month.month == 12:
            new_month = date(current_month.year + 1, 1, 1)
        else:
            new_month = date(
                current_month.year,
                current_month.month + 1,
                1,
            )

        if new_month <= max_date.replace(day=1):
            st.session_state.calendar_month = new_month
            st.rerun()

    # --------------------------------------------------
    # 7. Weekday headings
    # --------------------------------------------------
    weekday_columns = st.columns(7)

    for column, weekday in zip(
        weekday_columns,
        ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    ):
        column.markdown(
            f'<div class="calendar-weekday">{weekday}</div>',
            unsafe_allow_html=True,
        )

    # --------------------------------------------------
    # 8. Calendar grid
    # --------------------------------------------------
    weeks = calendar.monthcalendar(
        current_month.year,
        current_month.month,
    )

    for week in weeks:
        day_columns = st.columns(7)

        for day_index, day_number in enumerate(week):
            if day_number == 0:
                day_columns[day_index].markdown("&nbsp;")
                continue

            chosen_date = date(
                current_month.year,
                current_month.month,
                day_number,
            )

            # Dates outside the available dataset range
            # cannot be selected.
            if not min_date <= chosen_date <= max_date:
                day_columns[day_index].markdown(
                    f"""
                    <div style="
                        text-align:center;
                        padding:9px 0;
                        color:#94A3B8;
                        font-size:12px;
                    ">{day_number}</div>
                    """,
                    unsafe_allow_html=True,
                )
                continue

            # Highlight the range endpoints.
            is_endpoint = chosen_date in (
                st.session_state.filter_start,
                st.session_state.filter_end,
            )

            # Highlight the pending start date.
            if st.session_state.pending_start is not None:
                is_endpoint = (
                    chosen_date == st.session_state.pending_start
                )

            if day_columns[day_index].button(
                str(day_number),
                key=f"calendar_day_{current_month}_{day_number}",
                type="primary" if is_endpoint else "secondary",
                use_container_width=True,
                disabled=not st.session_state.custom_range_mode,
            ):
                if st.session_state.pending_start is None:
                    # First click selects the start date.
                    st.session_state.pending_start = chosen_date

                else:
                    # Second click selects the end date.
                    first_date = st.session_state.pending_start

                    st.session_state.filter_start = min(
                        first_date,
                        chosen_date,
                    )

                    st.session_state.filter_end = max(
                        first_date,
                        chosen_date,
                    )

                    st.session_state.pending_start = None
                    st.session_state.custom_range_mode = False

                st.rerun()

    # --------------------------------------------------
    # 9. Return selected dates to app.py
    # --------------------------------------------------
    return (
        st.session_state.filter_start,
        st.session_state.filter_end,
    )
