"""
Sidebar filters for SalesVision (Streamlit 1.65+).

    start_date, end_date = render_date_filter(min_date, max_date)
    selected_states      = render_state_filter(all_states)

Date range
    * one-row quick-range control: 7D, 30D, 90D, 1Y, All
    * a native calendar popup for custom ranges (replaces the 500-line
      hand-built calendar, so it is faster and works on touch screens)
    * the option that matches the current range is always highlighted

States
    * a summary line ("All 10 states", "3 of 10 states") and an inline
      expander with toggle chips plus Select all / Clear
"""
from datetime import timedelta

import streamlit as st

from utils.ui import format_date

PRESETS = ["7D", "30D", "90D", "1Y", "All"]
PRESET_DAYS = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365}


# --------------------------------------------------
# 1. Date range helpers
# --------------------------------------------------
def preset_range(label, min_date, max_date):
    """Start and end dates for a quick-range pill."""
    if label == "All":
        return min_date, max_date
    start = max_date - timedelta(days=PRESET_DAYS[label] - 1)
    return max(min_date, start), max_date


def active_preset(start, end, min_date, max_date):
    """Name of the preset equal to (start, end), or None for a custom range."""
    for label in PRESETS:
        if preset_range(label, min_date, max_date) == (start, end):
            return label
    return None


def _init_date_state(min_date, max_date):
    """Create the filter state once and keep it inside the data's date range."""
    state = st.session_state
    state.setdefault("filter_start", min_date)
    state.setdefault("filter_end", max_date)
    state.setdefault("date_version", 0)

    start = min(max(state["filter_start"], min_date), max_date)
    end = min(max(state["filter_end"], start), max_date)
    state["filter_start"], state["filter_end"] = start, end


def _on_preset(min_date, max_date):
    label = st.session_state.get("date_preset")
    if not label:          # clicking the active pill deselects it: keep the range
        return
    start, end = preset_range(label, min_date, max_date)
    st.session_state["filter_start"] = start
    st.session_state["filter_end"] = end
    # A new key makes the calendar widget pick up the new start and end.
    st.session_state["date_version"] += 1


def _on_custom(min_date, max_date):
    value = st.session_state.get(f"date_range_{st.session_state['date_version']}")
    # While only the first date is chosen the widget returns one date: wait.
    if isinstance(value, (list, tuple)) and len(value) == 2:
        st.session_state["filter_start"], st.session_state["filter_end"] = value


# --------------------------------------------------
# 2. Date range widget
# --------------------------------------------------
def render_date_filter(min_date, max_date):
    """Render the date-range filter and return (start_date, end_date)."""
    _init_date_state(min_date, max_date)
    state = st.session_state

    st.markdown('<div class="sv-side-label">Date range</div>', unsafe_allow_html=True)

    # Keep the highlighted pill in sync with the real range.
    state["date_preset"] = active_preset(
        state["filter_start"], state["filter_end"], min_date, max_date
    )
    st.segmented_control(
        "Quick range",
        PRESETS,
        selection_mode="single",
        key="date_preset",
        on_change=_on_preset,
        args=(min_date, max_date),
        label_visibility="collapsed",
        width="stretch",
    )

    st.date_input(
        "Custom range",
        value=(state["filter_start"], state["filter_end"]),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
        key=f"date_range_{state['date_version']}",
        on_change=_on_custom,
        args=(min_date, max_date),
        label_visibility="collapsed",
    )

    start, end = state["filter_start"], state["filter_end"]
    days = (end - start).days + 1
    st.caption(f"{format_date(start)} to {format_date(end)} ({days:,} days)")
    return start, end


# --------------------------------------------------
# 3. State filter
# --------------------------------------------------
def _set_states(values):
    st.session_state["state_filter"] = list(values)


def _state_label(selected, total):
    if len(selected) == total:
        return f"All {total} states"
    if not selected:
        return "No states selected"
    if len(selected) == 1:
        return selected[0]
    return f"{len(selected)} of {total} states"


def render_state_filter(all_states):
    """Render the state filter and return the list of selected states."""
    key = "state_filter"
    all_states = list(all_states)

    current = st.session_state.get(key)
    if current is None:                       # first run: everything selected
        current = all_states
    current = [s for s in current if s in all_states]
    st.session_state[key] = current

    st.markdown('<div class="sv-side-label">States</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sv-side-value">{_state_label(current, len(all_states))}</div>',
        unsafe_allow_html=True,
    )

    # The expander label stays fixed: Streamlit collapses an expander whose
    # label changes, which would close it after every click.
    with st.expander("Choose states", expanded=False):
        left, right = st.columns(2)
        left.button(
            "Select all", key="states_select_all",
            on_click=_set_states, args=(all_states,), width="stretch",
        )
        right.button(
            "Clear", key="states_clear",
            on_click=_set_states, args=([],), width="stretch",
        )
        st.pills(
            "States",
            all_states,
            selection_mode="multi",
            key=key,
            label_visibility="collapsed",
        )

    return list(st.session_state.get(key) or [])
