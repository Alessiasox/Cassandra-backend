import sys
import os

# --- Forcefully Add Project Root to Path ---
# This is a robust way to ensure that relative imports work, especially in
# environments like Streamlit where the script execution context can be tricky.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

from ui.controls import render_sidebar_controls, render_download_buttons
from ui.tabs.spectrograms import render_spectrograms_tab
from ui.tabs.waveform import render_waveform_tab
from ui.tabs.ai import render_ai_tab
from ui.tabs.logs import render_logs_tab
from ui.utils.viewer_utils import generate_timeline

# --- Timestamp Parsing Helper ---
def parse_timestamp(timestamp_str):
    """Parse timestamp string handling Z suffix and various ISO formats"""
    if timestamp_str.endswith('Z'):
        # Remove Z and add explicit UTC offset
        timestamp_str = timestamp_str[:-1] + '+00:00'
    elif '+' not in timestamp_str and 'T' in timestamp_str:
        # Add UTC offset if missing
        timestamp_str += '+00:00'
    
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Fallback parsing for edge cases
        try:
            # Try without timezone info
            if timestamp_str.endswith('+00:00'):
                base_str = timestamp_str[:-6]
                dt = datetime.fromisoformat(base_str)
                return dt.replace(tzinfo=None)  # Return as naive datetime for consistency
            else:
                return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Last resort - return current time
            st.warning(f"Could not parse timestamp: {timestamp_str}")
            return datetime.now()

# --- Image Display Helper ---
def _show_image(img_meta, caption: str):
    """A helper to display images with error handling."""
    st.image(img_meta["url"], caption=caption, use_container_width=True)

# --- Page Config ---
st.set_page_config(
    page_title="INGV Cassandra Project",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- App State ---
ss = st.session_state
if 'logs' not in ss:
    ss.logs = []
if 'lores_hour' not in ss:
    ss.lores_hour = datetime.now().replace(minute=0, second=0, microsecond=0)

# --- Backend API Communication ---
API_URL = "http://app:8000"

@st.cache_data
def get_frames_from_backend(selected_station: str, selected_date: date) -> list:
    """Calls the backend to get frame data for a given station and date."""
    date_str = selected_date.strftime("%y%m%d")
    try:
        response = requests.get(f"{API_URL}/frames", params={"station": selected_station, "date": date_str})
        response.raise_for_status()
        ss.logs.append(f"SUCCESS: Fetched data for {selected_station} {date_str}")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from backend: {e}")
        ss.logs.append(f"ERROR: {e}")
        return []

def main():
    # --- Initialize Session State ---
    if 'logs' not in ss: ss.logs = []
    st.title("🌋 Cassandra Project — INGV VLF Network")
    st.caption(
        """
        **Cassandra** is an internal visualization and analysis toolkit for the INGV Experimental VLF Network.
        Use the control panel to configure your source folders, time ranges, and station of interest.
        """
    )
    
    # --- Sidebar and Data Loading ---
    station, selected_date, mode = render_sidebar_controls()
    # Clear cache if station changes
    if 'last_station' not in ss or ss.last_station != station:
        get_frames_from_backend.clear()
        ss.last_station = station
    # Use a custom spinner with emojis
    with st.spinner('Fetching spectrograms and waveforms... 🌋🌊📈 Please wait!'):
        all_frames = get_frames_from_backend(station, selected_date)

    # Render the working sidebar download buttons (ZIP downloads)
    render_download_buttons(frames=all_frames)

    if not all_frames:
        st.error("No data found for this station/date.")
        return

    # --- Timeline and Window Controls ---
    lores_frames = [f for f in all_frames if f['resolution'] == 'LoRes']
    all_timestamps = [parse_timestamp(f['timestamp']) for f in lores_frames]
    
    if not all_timestamps:
        st.warning("No LoRes frames found to build timeline.")
        # Render tabs with empty data
        render_spectrograms_tab(all_frames=all_frames, control_mode=mode, window_start=datetime.now(), window_end=datetime.now(), session_state=ss)
        return

    dt0 = min(all_timestamps)
    dt1 = max(all_timestamps)
    
    timeline = generate_timeline(dt0, dt1, 5)
    
    def find_closest(target_dt, dt_list):
        return min(dt_list, key=lambda dt: abs(dt - target_dt))

    if "range_slider" not in ss:
        default_start = find_closest(dt0, timeline)
        default_end = find_closest(dt0 + timedelta(hours=1), timeline)
        ss.range_slider = (default_start, default_end)
    
    ss.setdefault("lores_hour", dt0.replace(minute=0, second=0, microsecond=0))

    if mode == "Use slider":
        current_start, current_end = ss.range_slider
        if current_start not in timeline or current_end not in timeline:
             current_start = find_closest(current_start, timeline)
             current_end = find_closest(current_end, timeline)

        rng_start, rng_end = st.select_slider(
            "Time window",
            options=timeline,
            value=(current_start, current_end),
            format_func=lambda dt: dt.strftime("%H:%M"),
            key="range_slider"
        )
        ss["lores_hour"] = rng_start.replace(minute=0, second=0, microsecond=0)
    else: # "Use hour picker"
        lo_hours = sorted({ts.replace(minute=0, second=0, microsecond=0) for ts in all_timestamps})
        if ss["lores_hour"] not in lo_hours:
            ss["lores_hour"] = lo_hours[0]

        current_hour_index = lo_hours.index(ss["lores_hour"])

        c1, c2, c3 = st.columns([1, 6, 1], gap="small")
        with c1:
            st.button("◀ 1h", disabled=(current_hour_index == 0), on_click=lambda: ss.update(lores_hour=lo_hours[current_hour_index - 1]), use_container_width=True)
        with c2:
            ss["lores_hour"] = st.selectbox("LoRes hour", lo_hours, index=current_hour_index, format_func=lambda dt: dt.strftime("%H:%M"), label_visibility="collapsed")
        with c3:
            st.button("1h ▶", disabled=(current_hour_index == len(lo_hours) - 1), on_click=lambda: ss.update(lores_hour=lo_hours[current_hour_index + 1]), use_container_width=True)
        
        rng_start = ss["lores_hour"]
        rng_end = rng_start + timedelta(hours=1)

    # --- Ensure time range variables are always defined ---
    if 'rng_start' not in locals() or 'rng_end' not in locals():
        # Fallback time range if no data was loaded
        default_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        rng_start = default_time
        rng_end = default_time + timedelta(hours=1)
    
    # --- Render Tabs ---
    tab_spec, tab_wav, tab_ai, tab_logs = st.tabs(["Spectrograms", "Waveforms", "AI Inference", "Logs"])

    with tab_spec:
        render_spectrograms_tab(all_frames=all_frames, control_mode=mode, window_start=rng_start, window_end=rng_end, session_state=ss)
    with tab_wav:
        # Pass station, date, time range, and control mode to avoid duplicate sidebar rendering
        date_str = selected_date.strftime("%y%m%d")
        render_waveform_tab(station, date_str, rng_start, rng_end, mode, ss)
    
    with tab_ai:
        # Dedicated AI inference tab
        render_ai_tab(ss)
    
    with tab_logs:
        render_logs_tab(ss=ss)

if __name__ == "__main__":
    main()