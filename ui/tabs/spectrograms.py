from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import streamlit as st
from PIL import Image
import requests

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

def _show_image(img_meta, caption: str):
    """A helper to display images with error handling."""
    st.image(img_meta["url"], caption=caption, use_container_width=True)

def render_spectrograms_tab(all_frames, control_mode, window_start, window_end, session_state):
    """
    Renders the Spectrograms tab with timeline-based image display.
    """
    st.subheader("📈 Spectrograms")
    
    if control_mode == "Use slider":
        st.caption(f"**Displaying images between** {window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}")
        
        # Filter images based on the time window
        lores_in_window = [
            img for img in all_frames 
            if img.get("resolution") == "LoRes" and window_start <= parse_timestamp(img["timestamp"]) <= window_end
        ]
        for img in lores_in_window:
            st.image(img["url"], caption=parse_timestamp(img["timestamp"]).strftime("%H:%M"), use_container_width=True)

        # HiRes images in the same time window
        hires_in_window = [
            img for img in all_frames 
            if img.get("resolution") == "HiRes" and window_start <= parse_timestamp(img["timestamp"]) <= window_end
        ]
        
        if hires_in_window:
            st.subheader("🔍 High Resolution Images")
            cols = st.columns(3)
            for i, img in enumerate(hires_in_window):
                with cols[i % 3]:
                    with st.expander(f"📊 {parse_timestamp(img['timestamp']).strftime('%H:%M:%S')}", expanded=False):
                        _show_image(img, caption=parse_timestamp(img["timestamp"]).strftime("%H:%M:%S"))

    else:  # "Use hour picker"
        target_hour = window_start  # Hour picker mode
        
        st.caption(f"**Displaying images for hour** {target_hour.strftime('%H:%M')}")
        
        # LoRes images for the target hour (strict 1-hour window)
        lores_start = target_hour
        lores_end = target_hour + timedelta(hours=1)
        
        # Filter LoRes images for the target hour
        lores_this_hour = [
            img for img in all_frames 
            if img.get("resolution") == "LoRes"
        ]
        
        for img in lores_this_hour:
            img_time = parse_timestamp(img["timestamp"])
            if lores_start <= img_time < lores_end:
                _show_image(img, caption=img_time.strftime("%H:%M"))
        
        st.divider()
        
        # ───────────────────── HiRes section ─────────────────────
        if control_mode == "Use hour picker":
            col_b, col_a = st.columns(2)
            with col_b:
                mins_before = st.number_input(
                    "Minutes before", 
                    min_value=0, 
                    max_value=120, 
                    value=0, 
                    step=5, 
                    key="mins_before",
                    help="Show HiRes images this many minutes before the selected hour"
                )
            with col_a:
                mins_after = st.number_input(
                    "Minutes after", 
                    min_value=0, 
                    max_value=120, 
                    value=60, 
                    step=5, 
                    key="mins_after",
                    help="Show HiRes images this many minutes after the selected hour"
                )
            hi_start = target_hour - timedelta(minutes=int(mins_before))
            hi_end = target_hour + timedelta(minutes=int(mins_after))
        else:
            hi_start, hi_end = window_start, window_end

        hi_to_show = [
            img for img in all_frames
            if img.get("resolution") == "HiRes" and hi_start <= parse_timestamp(img["timestamp"]) < hi_end
        ]
        
        st.markdown(
            f"**HiRes between {hi_start:%H:%M} - {hi_end:%H:%M} "
            f"({len(hi_to_show)})**"
        )

        if hi_to_show:
            # Create a scrollable container for HiRes images
            with st.container(height=400):
                cols = st.columns(4, gap="small")
                for idx, img in enumerate(sorted(hi_to_show, key=lambda x: x["timestamp"])):
                    with cols[idx % 4]:
                        _show_image(img, caption=parse_timestamp(img["timestamp"]).strftime("%H:%M:%S"))
        else:
            st.info("No HiRes frames in this interval.")
