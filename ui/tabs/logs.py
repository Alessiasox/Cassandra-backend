import streamlit as st

def render_logs_tab(ss):
    st.subheader("📋 System Status")
    
    # Simple system status
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🎵 WAV Files", "Available")
        st.metric("📊 Spectrograms", "Working")
    
    with col2:
        st.metric("🤖 AI Inference", "Ready")
        st.metric("📡 Backend", "Connected")
    
    # AI Inference logs only
    st.divider()
    st.subheader("🤖 AI Inference Logs")
    
    logs = ss.get("logs", [])
    if logs:
        # Show last 10 logs in a clean format
        recent_logs = logs[-10:]
        for log in reversed(recent_logs):
            if "🟢" in log:
                st.success(log)
            elif "🟡" in log:
                st.warning(log)
            elif "❌" in log:
                st.error(log)
            else:
                st.info(log)
    else:
        st.info("💡 Run AI inference in the 'Waveform + AI' tab to see logs here")
    
    # Clear logs button
    if st.button("🗑️ Clear AI Logs", help="Clear all AI inference logs"):
        ss['logs'] = []
        st.success("✅ Logs cleared!") 