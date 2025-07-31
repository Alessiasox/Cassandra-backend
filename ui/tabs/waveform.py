import streamlit as st
import requests
import numpy as np
from datetime import datetime, timezone
import plotly.graph_objects as go
from scipy.io import wavfile
import io
import time # Added for retry logic

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

def render_waveform_tab(station, date_str, rng_start, rng_end, control_mode, ss):
    """
    Renders the Waveform tab with WAV file visualization and audio playback.
    """
    st.subheader("🎵 Waveform Analysis")
    
    # Show selected time range based on control mode
    if control_mode == "Use slider":
        st.info(f"🕐 **Time Range**: {rng_start.strftime('%H:%M')} - {rng_end.strftime('%H:%M')} on {station} (Slider Mode)")
    else:  # Hour picker
        st.info(f"🕐 **Selected Hour**: {rng_start.strftime('%H:%M')} on {station} (Hour Picker Mode)")
    st.markdown("*Interactive waveform visualization, audio playback, and file downloads*")
    
    # Fetch WAV files from backend
    backend_url = "http://app:8000"
    
    # Better startup experience - check if system is still mounting
    if 'system_ready' not in ss:
        st.info("⚙️ System is starting up and mounting remote stations...")
        st.caption("This may take 1-2 minutes on first load. WAV files will be available once mounting is complete.")
        
        # Manual retry button instead of auto-rerun to avoid duplicate tabs
        if st.button("🔄 Try Loading WAV Files", type="primary"):
            ss['system_ready'] = True
            st.success("✅ System marked as ready! Click the button again to search for WAV files.")
        return
    
    # Simple search controls
    search_key = f"wav_data_{station}_{date_str}"
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_clicked = st.button("🔍 Search for WAV Files", type="primary")
    with col2:
        if search_key in ss:
            if st.button("🗑️ Clear Results"):
                del ss[search_key]
                st.rerun()
    
    # Show cached results if available
    if search_key in ss:
        wav_files = ss[search_key]
        # Only show success message if no WAV files found
        if not wav_files:
            st.info(f"📂 No WAV files found for {station} on {date_str}")
            st.caption("💡 Try a different station or date")
            return
    elif search_clicked:
        # Perform search when button is clicked
        with st.spinner("🔍 Searching for WAV files... This may take up to 60 seconds"):
            try:
                response = requests.get(f"{backend_url}/wavs", params={
                    "station": station,
                    "date": date_str
                }, timeout=60)
                
                if response.status_code == 200:
                    wav_files = response.json()
                    # Cache the results
                    ss[search_key] = wav_files
                    # Only show message if no files found
                    if not wav_files:
                        st.info(f"📂 No WAV files found for {station} on {date_str}")
                        st.caption("💡 Try a different station or date")
                        return
                else:
                    st.error(f"❌ Failed to fetch WAV files: HTTP {response.status_code}")
                    return
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ Timeout connecting to backend")
                st.info("💡 The backend might be starting up or overloaded. Try again in a moment.")
                return
            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot connect to backend")
                st.info("💡 Make sure the backend service is running")
                return
            except Exception as e:
                st.error(f"❌ Error connecting to backend: {e}")
                return
    else:
        # No search performed yet
        st.info("👆 Click 'Search for WAV Files' to begin")
        st.caption("💡 Results will be cached for faster access. Use 'Clear Results' to refresh.")
        return
    
    # Continue with processing results (wav_files should be available)
    if not wav_files:
        st.info(f"📂 No WAV files found for {station} on {date_str}")
        st.caption("💡 Try a different station or date")
        return
    
    # Filter WAV files based on control mode and time range
    filtered_wav_files = []
    for wav_file in wav_files:
        # Parse WAV file timestamp
        timestamp_str = wav_file['timestamp']
        try:
            wav_timestamp = parse_timestamp(timestamp_str)
            if wav_timestamp.tzinfo is None:
                wav_timestamp = wav_timestamp.replace(tzinfo=timezone.utc)
            
            # Convert to naive for comparison (assume UTC)
            wav_time_naive = wav_timestamp.replace(tzinfo=None)
            rng_start_naive = rng_start.replace(tzinfo=None) if rng_start.tzinfo else rng_start
            rng_end_naive = rng_end.replace(tzinfo=None) if rng_end.tzinfo else rng_end
            
            # Mode-aware filtering logic
            if control_mode == "Use slider":
                # Slider mode: show WAV files within the selected range
                if rng_start_naive <= wav_time_naive < rng_end_naive:
                    filtered_wav_files.append(wav_file)
            else:  # Hour picker mode
                # Hour picker mode: show WAV files only within that specific hour
                hour_start = rng_start_naive
                hour_end = hour_start.replace(minute=59, second=59, microsecond=999999)
                if hour_start <= wav_time_naive <= hour_end:
                    filtered_wav_files.append(wav_file)
                    
        except ValueError:
            # Include files with parsing issues to avoid losing data
            filtered_wav_files.append(wav_file)
                    
    # Show filtering results
    if not filtered_wav_files:
        if control_mode == "Use slider":
            st.warning(f"⚠️ No WAV files found in selected time range ({rng_start.strftime('%H:%M')} - {rng_end.strftime('%H:%M')})")
        else:
            st.warning(f"⚠️ No WAV files found for selected hour ({rng_start.strftime('%H:%M')})")
        st.info("💡 Try adjusting the time range in the Spectrograms tab")
        return
    
    # Display filtered WAV files
    for i, wav_file in enumerate(filtered_wav_files):
        with st.expander(f"🎵 {wav_file['filename']}", expanded=(i == 0)):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Parse timestamp
                timestamp_str = wav_file['timestamp']
                timestamp = parse_timestamp(timestamp_str)
                
                st.write(f"**Time**: {timestamp.strftime('%H:%M:%S UTC')}")
                st.write(f"**Station**: {wav_file['station']}")
            
            with col2:
                st.caption("🔊 Actions")
            
            # Download and process WAV file
            wav_key = f"wav_{wav_file['filename']}"
            
            # Check if WAV is already processed
            if wav_key in ss and 'success' in ss[wav_key]:
                # Display cached results
                cached_data = ss[wav_key]
                st.plotly_chart(cached_data['figure'], use_container_width=True)
                st.audio(cached_data['audio_bytes'], format="audio/wav")
                st.download_button(
                    label="💾 Download WAV File",
                    data=cached_data['audio_bytes'],
                    file_name=wav_file['filename'],
                    mime="audio/wav"
                )
            else:
                # Show loading state and download
                with st.spinner(f"Loading {wav_file['filename']}..."):
                    try:
                        # Convert localhost URL to internal proxy URL
                        internal_url = wav_file['url'].replace('http://localhost:8080', 'http://proxy')
                        
                        # Retry logic for large WAV files
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                wav_response = requests.get(internal_url, timeout=120)  # Increased timeout for large files
                                break
                            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                                if attempt == max_retries - 1:
                                    raise e
                                time.sleep(1)  # Brief wait before retry
                        
                        if wav_response.status_code == 200:
                            audio_data = io.BytesIO(wav_response.content)
                            sample_rate, data = wavfile.read(audio_data)
                            
                            # Convert to mono if stereo
                            if len(data.shape) > 1:
                                data = np.mean(data, axis=1)
                            
                            # Create time axis
                            duration = len(data) / sample_rate
                            time_axis = np.linspace(0, duration, len(data))
                            
                            # Create plotly figure
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=time_axis,
                                y=data,
                                mode='lines',
                                name='Amplitude',
                                line=dict(width=0.8)
                            ))
                            
                            fig.update_layout(
                                title=f"Waveform: {wav_file['filename']}",
                                xaxis_title="Time (seconds)",
                                yaxis_title="Amplitude",
                                height=300,
                                margin=dict(l=50, r=50, t=50, b=50)
                            )
                            
                            # Cache the processed data
                            audio_data.seek(0)
                            audio_bytes = audio_data.getvalue()
                            ss[wav_key] = {
                                'success': True,
                                'figure': fig,
                                'audio_bytes': audio_bytes
                            }
                            
                            # Display results
                            st.plotly_chart(fig, use_container_width=True)
                            st.audio(audio_bytes, format="audio/wav")
                            st.download_button(
                                label="💾 Download WAV File",
                                data=audio_bytes,
                                file_name=wav_file['filename'],
                                mime="audio/wav"
                            )
                            
                        else:
                            # Only show error for actual failures
                            st.warning(f"⚠️ Unable to load WAV file (HTTP {wav_response.status_code})")
                            
                    except requests.exceptions.ConnectionError:
                        st.warning("⚠️ Connection issue - WAV file temporarily unavailable")
                    except requests.exceptions.Timeout:
                        st.warning("⚠️ Large file taking longer than expected - try again later")
                    except Exception as e:
                        # Only log actual processing errors
                        error_msg = str(e)
                        if "WAV" in error_msg or "audio" in error_msg.lower():
                            st.warning(f"⚠️ Audio processing issue: {error_msg}")
                        else:
                            st.warning("⚠️ Unexpected issue loading WAV file")
                
 