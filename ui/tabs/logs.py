import streamlit as st

def render_logs_tab(ss):
    st.subheader("Runtime Logs")
    logs = ss.get("logs", [])
    if logs:
        # Use a simple st.code for now, can be enhanced with colors later
        st.code("\n".join(reversed(logs)))
    else:
        st.info("No log entries yet.") 