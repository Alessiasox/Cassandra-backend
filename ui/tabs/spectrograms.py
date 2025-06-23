from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import streamlit as st
from PIL import Image
import requests

def render_spectrograms_tab(
    *,
    all_frames:         List[Dict],
    control_mode:       str,          # "Use slider" | "Use hour picker"
    window_start:       datetime,
    window_end:         datetime,
    session_state:      Dict,
) -> None:
    """Main entry for the Spectrograms tab."""

    st.subheader("Spectrograms")

    low_res_images = [f for f in all_frames if f['resolution'] == 'LoRes']
    high_res_images = [f for f in all_frames if f['resolution'] == 'HiRes']

    # ───────────────────── LoRes section ─────────────────────
    if control_mode == "Use slider":
        lo_to_show = [
            img for img in low_res_images
            if window_start <= datetime.fromisoformat(img["timestamp"]) <= window_end
        ]
        st.markdown(f"**LoRes frames in window:** {len(lo_to_show)}")
        for img in sorted(lo_to_show, key=lambda x: x["timestamp"]):
            st.write("LoRes image URL:", img["url"])
            st.image(img["url"], caption=datetime.fromisoformat(img["timestamp"]).strftime("%H:%M"), use_column_width=True)

    else:  # hour-picker: exactly one low-res frame
        target_hour = session_state["lores_hour"]
        img = next(
            (im for im in low_res_images
             if datetime.fromisoformat(im["timestamp"]).replace(minute=0, second=0, microsecond=0) == target_hour),
            None
        )
        if img:
            st.image(img["url"], caption=datetime.fromisoformat(img["timestamp"]).strftime("%H:%M"), use_column_width=True)
        else:
            st.warning("No LoRes frame for selected hour.")

    st.divider()

    # ───────────────────── HiRes section ─────────────────────
    if control_mode == "Use hour picker":
        col_b, col_a = st.columns(2)
        with col_b:
            mins_before = st.number_input("Minutes before", 0, 60, 0, 5, key="mins_b")
        with col_a:
            mins_after  = st.number_input("Minutes after",  0, 60, 60, 5, key="mins_a")
        hi_start = session_state["lores_hour"] - timedelta(minutes=int(mins_before))
        hi_end   = session_state["lores_hour"] + timedelta(minutes=int(mins_after))
    else:
        hi_start, hi_end = window_start, window_end

    hi_to_show = [
        img for img in high_res_images
        if hi_start <= datetime.fromisoformat(img["timestamp"]) < hi_end
    ]
    st.markdown(
        f"**HiRes between {hi_start:%H:%M} – {hi_end:%H:%M} "
        f"({len(hi_to_show)})**"
    )

    if hi_to_show:
        # Create a scrollable container for HiRes images
        with st.container(height=400):
            cols = st.columns(4, gap="small")
            for idx, img in enumerate(sorted(hi_to_show, key=lambda x: x["timestamp"])):
                with cols[idx % 4]:
                    _show_image(img, caption=datetime.fromisoformat(img["timestamp"]).strftime("%H:%M:%S"))
    else:
        st.info("No HiRes frames in this interval.")


def _show_image(img_meta: Dict, *, caption: str) -> None:
    """Load image from URL and plot it."""
    try:
        st.write("HiRes image URL:", img_meta["url"])
        st.image(img_meta["url"], caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to load image: {img_meta['url']}. Error: {e}")
