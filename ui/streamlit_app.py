import streamlit as st
import requests
from datetime import datetime, date, timedelta
import pandas as pd
import yaml

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
def get_frames_from_backend(selected_date: date) -> list:
    """Calls the backend to get frame data for a given date."""
    date_str = selected_date.strftime("%y%m%d")
    try:
        response = requests.get(f"{API_URL}/frames", params={"date": date_str})
        response.raise_for_status()
        ss.logs.append(f"SUCCESS: Fetched data for {date_str}")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from backend: {e}")
        ss.logs.append(f"ERROR: {e}")
        return []

# --- UI Helper Functions ---
def get_station_list() -> list:
    """Loads station list from the YAML file."""
    try:
        with open("ssh/stations.yaml", 'r') as f:
            stations_config = yaml.safe_load(f)
            return list(stations_config.keys()) if stations_config else []
    except FileNotFoundError:
        st.sidebar.error("stations.yaml not found.")
        return ["default"]
    except Exception as e:
        st.sidebar.error(f"Error reading stations.yaml: {e}")
        return ["default"]

def render_sidebar():
    """Renders the sidebar controls and returns selected values."""
    with st.sidebar:
        st.header("Control Panel")
        station = st.selectbox("Station", get_station_list())
        st.markdown("---")
        st.markdown("Source Folder: VLF (on-demand)")
        st.markdown("---")
        selected_date = st.date_input("Date", datetime.now())
        st.markdown("---")
        st.header("Download Options")
        st.warning("Download buttons are not yet implemented.")
        st.button("Download All Files", disabled=True)
        st.button("Download LoRes WAV", disabled=True)
        st.button("Download HiRes WAV", disabled=True)
        return station, selected_date

def render_spectrograms_tab(frames: list, window_start: datetime, window_end: datetime):
    """Renders the spectrograms tab content within a specific time window."""
    st.subheader("Spectrograms")

    df = pd.DataFrame(frames)
    if df.empty:
        st.info("No frames found for the selected date. Try another date.")
        return
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    window_frames = df[(df['timestamp'] >= window_start) & (df['timestamp'] < window_end)]
    
    lores_frames = window_frames[window_frames['resolution'] == 'LoRes'].sort_values('timestamp')
    hires_frames = window_frames[window_frames['resolution'] == 'HiRes'].sort_values('timestamp')

    st.markdown(f"**Displaying window: {window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}**")

    if not lores_frames.empty:
        st.markdown(f"**LoRes frame for this hour:**")
        st.image(lores_frames.iloc[0]['url'], caption=f"LoRes - {lores_frames.iloc[0]['timestamp']}")
    else:
        st.info("No LoRes frame available for this hour.")

    st.markdown("---")
    st.markdown(f"**HiRes frames in this hour: {len(hires_frames)}**")
    for _, frame in hires_frames.iterrows():
        st.image(frame['url'], caption=f"HiRes - {frame['timestamp']}", width=300)

def render_waveform_tab():
    st.warning("Waveform and AI features are not yet implemented.")

def render_logs_tab():
    st.header("Session Logs")
    if ss.logs:
        st.code("\n".join(reversed(ss.logs)))
    else:
        st.info("No log messages yet.")

# --- Main App ---
st.title("INGV Cassandra Project")
st.caption(
    """
**Cassandra** is an internal visualization and analysis toolkit developed for the INGV Experimental VLF Network.
It allows you to:
- Browse spectrograms from multiple stations (LoRes: hourly, HiRes: ~40s)
- Explore and play raw waveform `.wav` audio files
- Run (or simulate) AI-based signal classification
- Download any combination of files for offline use
"""
)

station, selected_date = render_sidebar()
all_frames_for_day = get_frames_from_backend(selected_date)

available_hours = []
if all_frames_for_day:
    df = pd.DataFrame(all_frames_for_day)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    available_hours = sorted(list(
        df[df['resolution'] == 'LoRes']['timestamp'].dt.floor('H').unique()
    ))

if not available_hours:
    st.warning("No LoRes frames found for the selected date to define hourly windows.")
else:
    if ss.lores_hour.date() != selected_date:
        ss.lores_hour = available_hours[0]

    current_hour_index = available_hours.index(ss.lores_hour)
    
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1:
        st.button(
            "1 h earlier",
            disabled=current_hour_index == 0,
            on_click=lambda: ss.update(lores_hour=available_hours[current_hour_index - 1]),
            use_container_width=True
        )
    with c2:
        ss.lores_hour = st.selectbox(
            "Time window",
            available_hours,
            index=current_hour_index,
            format_func=lambda dt: dt.strftime("%Y-%m-%d %H:%M"),
            label_visibility="collapsed"
        )
    with c3:
        st.button(
            "1 h later",
            disabled=current_hour_index == len(available_hours) - 1,
            on_click=lambda: ss.update(lores_hour=available_hours[current_hour_index + 1]),
            use_container_width=True
        )
    
    window_start = ss.lores_hour
    window_end = window_start + timedelta(hours=1)

    tab_spec, tab_wav, tab_logs = st.tabs(
        ["Spectrograms", "Waveform + AI", "Logs"]
    )

    with tab_spec:
        render_spectrograms_tab(all_frames_for_day, window_start, window_end)
    with tab_wav:
        render_waveform_tab()
    with tab_logs:
        render_logs_tab()