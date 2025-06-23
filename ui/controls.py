import streamlit as st
import yaml
from datetime import datetime

def get_station_list() -> list:
    """Loads station list from the YAML file."""
    try:
        with open("ssh/stations.yaml", 'r') as f:
            stations_config = yaml.safe_load(f)
            return list(stations_config.keys()) if stations_config else []
    except FileNotFoundError:
        return ["default"]
    except Exception:
        return ["default"]

def render_sidebar_controls():
    """
    Renders the main sidebar controls:
    - Station selector
    - Date picker
    - Control mode (slider vs. hour picker)
    """
    st.sidebar.header("Control Panel")

    # 1) Station selector
    station = st.sidebar.selectbox("Station", get_station_list(), key="station")

    # 2) Date picker
    selected_date = st.sidebar.date_input("Date", value=datetime.now(), key="sel_date")

    # 3) Control mode
    mode = st.sidebar.radio(
        "Control mode",
        ["Use slider", "Use hour picker"],
        horizontal=True,
        key="mode"
    )

    st.sidebar.markdown("---")
    render_download_buttons()

    return station, selected_date, mode


def render_download_buttons():
    """Renders the download buttons in the sidebar."""
    st.sidebar.header("Download Options")
    st.sidebar.button("Download All Files", use_container_width=True, disabled=True)
    st.sidebar.button("Download All WAV Files", use_container_width=True, disabled=True)
    st.sidebar.button("Download LoRes WAV", use_container_width=True, disabled=True)
    st.sidebar.button("Download HiRes WAV", use_container_width=True, disabled=True)
    st.sidebar.button("Download LoRes Spec", use_container_width=True, disabled=True)
    st.sidebar.button("Download HiRes Spec", use_container_width=True, disabled=True) 