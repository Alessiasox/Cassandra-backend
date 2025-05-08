# ui/streamlit_app.py
import os
import streamlit as st
import requests
from datetime import datetime

API_URL = os.getenv("API_URL", "http://app:8000")

st.title("Cassandra Quick‐Test")

if st.button("Check Health"):
    r = requests.get(f"{API_URL}/health")
    st.json(r.json())

st.markdown("---")
st.subheader("Fetch frames")

station    = st.text_input("Station", "Duronia")
resolution = st.selectbox("Resolution", ["LoRes","HiRes"])
start      = st.text_input("Start (ISO)", "2025-04-24T00:00:00Z")
end        = st.text_input("End   (ISO)", "2025-04-24T23:59:59Z")

if st.button("Load"):
    try:
        params = {"station":station,"resolution":resolution,
                  "start":start,"end":end}
        r = requests.get(f"{API_URL}/frames", params=params)
        r.raise_for_status()
        data = r.json()
        st.write(f"Found {len(data)} frames")
        for f in data[:5]:
            st.markdown(f"- {f['timestamp']} → [view image]({f['url']})")
    except Exception as e:
        st.error(e)