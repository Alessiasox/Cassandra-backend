import streamlit as st
from datetime import datetime

def render_waveform_tab(ss):
    """
    Renders the Waveform + AI tab.
    Currently a placeholder.
    """
    st.subheader("Waveform + AI Inference")
    st.info("No .wav files are provided by the current backend.")
    _ai_stub(ss)


def _ai_stub(ss):
    """Simple AI inference mock that logs to session_state."""
    st.divider()
    st.subheader("AI Inference (stub)")
    model = st.selectbox("Model", ["1D CNN", "Simple RNN", "Transformer"])
    if st.button("Run Inference"):
        now = datetime.utcnow().strftime("%H:%M:%S UTC")
        st.success("Inference complete (mock). See Logs tab.")
        ss.get("logs", []).extend(
            [
                f"INFO: {now} — Started {model}",
                f"WARN: 00:00:01 — No peaks found (stub)",
                f"SUCCESS: 00:00:02 — Finished (stub)",
            ]
        ) 