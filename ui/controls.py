import streamlit as st
import yaml
from datetime import datetime
import io
import zipfile
import requests

def get_station_list() -> list:
    """Fetch station list from the backend API."""
    try:
        response = requests.get("http://app:8000/stations")
        response.raise_for_status()
        return response.json()
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

    return station, selected_date, mode

def to_internal_url(url):
    # Patch browser URL to Docker-internal URL for download
    if url.startswith("http://localhost:8080/"):
        return url.replace("http://localhost:8080/", "http://proxy/")
    return url

def render_download_buttons(frames=None):
    """Renders the download buttons in the sidebar. If frames are provided, enables download as ZIP."""
    st.sidebar.header("Download Options")
    can_download = frames is not None and len(frames) > 0
    # Download All Files
    if st.sidebar.button("Download All Files", use_container_width=True, disabled=not can_download, key="download_all_files_btn"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for frame in frames:
                fname = frame.get("url", "").split("/")[-1]
                try:
                    # Use internal URL for download
                    data = requests.get(to_internal_url(frame["url"])).content
                    zf.writestr(fname, data)
                except Exception:
                    pass
        zip_buffer.seek(0)
        st.sidebar.download_button(
            label="Save ZIP",
            data=zip_buffer,
            file_name="frames.zip",
            mime="application/zip",
            use_container_width=True,
            key="save_zip_btn"
        )
    # Download LoRes Only
    lores_frames = [f for f in frames or [] if f.get("resolution") == "LoRes"]
    can_download_lores = len(lores_frames) > 0
    if st.sidebar.button("Download LoRes Only", use_container_width=True, disabled=not can_download_lores, key="download_lores_only_btn"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for frame in lores_frames:
                fname = frame.get("url", "").split("/")[-1]
                try:
                    data = requests.get(to_internal_url(frame["url"])).content
                    zf.writestr(fname, data)
                except Exception:
                    pass
        zip_buffer.seek(0)
        st.sidebar.download_button(
            label="Save LoRes ZIP",
            data=zip_buffer,
            file_name="lores_frames.zip",
            mime="application/zip",
            use_container_width=True,
            key="save_lores_zip_btn"
        )
    # Download HiRes Only
    hires_frames = [f for f in frames or [] if f.get("resolution") == "HiRes"]
    can_download_hires = len(hires_frames) > 0
    if st.sidebar.button("Download HiRes Only", use_container_width=True, disabled=not can_download_hires, key="download_hires_only_btn"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for frame in hires_frames:
                fname = frame.get("url", "").split("/")[-1]
                try:
                    data = requests.get(to_internal_url(frame["url"])).content
                    zf.writestr(fname, data)
                except Exception:
                    pass
        zip_buffer.seek(0)
        st.sidebar.download_button(
            label="Save HiRes ZIP",
            data=zip_buffer,
            file_name="hires_frames.zip",
            mime="application/zip",
            use_container_width=True,
            key="save_hires_zip_btn"
        )
    