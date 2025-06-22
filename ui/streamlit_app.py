# ui/streamlit_app.py
import os
import streamlit as st
import requests
from datetime import datetime

API_URL = os.getenv("API_URL", "http://app:8000")

st.title("Cassandra On-Demand Viewer")

st.markdown("---")
st.subheader("Fetch Frames by Date")

# Use a simple text input for the date in YYMMDD format
date_str = st.text_input("Date (YYMMDD format)", "250411")

if st.button("Load Frames"):
    if not date_str or len(date_str) != 6 or not date_str.isdigit():
        st.error("Please enter a valid date in YYMMDD format.")
    else:
        try:
            params = {"date": date_str}
            r = requests.get(f"{API_URL}/frames", params=params)
            r.raise_for_status()
            data = r.json()
            st.write(f"Found {len(data)} frames for date {date_str}")
            # Display the first 20 frames found
            for f in data[:20]:
                st.markdown(f"- **{f['resolution']}** at {f['timestamp']} → [view image]({f['url']})")
        except Exception as e:
            st.error(f"An error occurred: {e}")