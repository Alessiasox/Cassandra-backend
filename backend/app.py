# backend/app.py
import os
import re
import logging
import time
import threading
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
import paramiko
import yaml
from typing import Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Optimization Infrastructure ---

# SSH connection pool - keeps connections alive per station
_ssh_connections = {}
_ssh_connection_lock = threading.Lock()

# Cache for WAV file results - reduces SSH calls
_wav_cache = {}
_cache_lock = threading.Lock()
WAV_CACHE_DURATION = 60  # Cache results for 60 seconds

# Cache for frame results as well
_frame_cache = {}
FRAME_CACHE_DURATION = 120  # Cache frames for 2 minutes (they change less frequently)

def get_ssh_connection(station_cfg: dict) -> paramiko.SSHClient:
    """Get or create a reusable SSH connection for a station"""
    ssh_host = station_cfg["host"]
    ssh_user = station_cfg["username"]
    ssh_port = station_cfg.get("port", 22)
    ssh_private_key_path = os.getenv("SSH_PRIVATE_KEY_PATH")
    
    connection_key = f"{ssh_user}@{ssh_host}:{ssh_port}"
    
    with _ssh_connection_lock:
        # Check if we have a valid connection
        if connection_key in _ssh_connections:
            client = _ssh_connections[connection_key]
            try:
                # Test if connection is still alive
                client.exec_command("echo test", timeout=2)
                logger.info(f"Reusing SSH connection for {connection_key}")
                return client
            except:
                # Connection is dead, remove it
                logger.info(f"SSH connection dead for {connection_key}, creating new one")
                try:
                    client.close()
                except:
                    pass
                del _ssh_connections[connection_key]
        
        # Create new connection
        logger.info(f"Creating new SSH connection for {connection_key}")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ssh_host,
            username=ssh_user,
            key_filename=ssh_private_key_path,
            port=ssh_port,
            timeout=5  # Faster timeout for quicker failures
        )
        _ssh_connections[connection_key] = client
        return client

def get_cached_wav_files(station: str, date: str) -> Optional[list]:
    """Check if we have cached WAV file results"""
    cache_key = f"{station}_{date}"
    
    with _cache_lock:
        if cache_key in _wav_cache:
            cached_data, timestamp = _wav_cache[cache_key]
            if time.time() - timestamp < WAV_CACHE_DURATION:
                logger.info(f"Using cached WAV results for {station} {date}")
                return cached_data
            else:
                # Cache expired
                del _wav_cache[cache_key]
    
    return None

def cache_wav_files(station: str, date: str, wav_files: list):
    """Cache WAV file results"""
    cache_key = f"{station}_{date}"
    
    with _cache_lock:
        _wav_cache[cache_key] = (wav_files, time.time())
        logger.info(f"Cached {len(wav_files)} WAV files for {station} {date}")

def get_cached_frames(station: str, date: str) -> Optional[list]:
    """Check if we have cached frame results"""
    cache_key = f"frames_{station}_{date}"
    
    with _cache_lock:
        if cache_key in _frame_cache:
            cached_data, timestamp = _frame_cache[cache_key]
            if time.time() - timestamp < FRAME_CACHE_DURATION:
                logger.info(f"Using cached frame results for {station} {date}")
                return cached_data
            else:
                # Cache expired
                del _frame_cache[cache_key]
    
    return None

def cache_frames(station: str, date: str, frames: list):
    """Cache frame results"""
    cache_key = f"frames_{station}_{date}"
    
    with _cache_lock:
        _frame_cache[cache_key] = (frames, time.time())
        logger.info(f"Cached {len(frames)} frames for {station} {date}")

# --- Environment and Configuration ---

FILE_SERVER_URL = os.getenv("FILE_SERVER_URL", "http://proxy")
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH")
REMOTE_DIR = os.getenv("REMOTE_DIR", "C:/htdocs/VLF")

STATIONS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../ssh/stations.yaml')

# --- Regex for parsing filenames ---

# LoRes: G1_LoResT_250411UTC0700.jpg (4-digit time)
LORES_RE = re.compile(r"([^_]+)_LoResT_(\d{6})UTC(\d{4})\.jpg", re.IGNORECASE)
# HiRes: G1_HiResT_250410UTC144140.jpg (6-digit time)
HIRES_RE = re.compile(r"([^_]+)_HiResT_(\d{6})UTC(\d{6})\.jpg", re.IGNORECASE)
# WAV: G8_Audio_29UTC223440.wav (day of month + HHMMSS time)
WAV_RE = re.compile(r"([^_]+)_Audio_(\d{2})UTC(\d{6})\.wav", re.IGNORECASE)

app = FastAPI(title="Cassandra On-Demand API")

# --- Models ---

class Frame(BaseModel):
    station: str
    resolution: str
    timestamp: datetime
    url: str

class WavFile(BaseModel):
    station: str
    timestamp: datetime
    filename: str
    url: str
    remote_path: str

# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}

# Add cache management endpoint for debugging
@app.get("/cache/clear")
def clear_cache():
    """Clear all cached data and SSH connections for debugging"""
    global _wav_cache, _frame_cache, _ssh_connections
    
    with _cache_lock:
        wav_entries = len(_wav_cache)
        frame_entries = len(_frame_cache)
        _wav_cache.clear()
        _frame_cache.clear()
    
    with _ssh_connection_lock:
        connections = len(_ssh_connections)
        for client in _ssh_connections.values():
            try:
                client.close()
            except:
                pass
        _ssh_connections.clear()
    
    total_entries = wav_entries + frame_entries
    logger.info(f"Cleared {total_entries} cache entries ({wav_entries} WAV, {frame_entries} frames) and {connections} SSH connections")
    return {"message": f"Cleared {total_entries} cache entries ({wav_entries} WAV, {frame_entries} frames) and {connections} SSH connections"}

@app.get("/cache/status")
def cache_status():
    """Get cache statistics"""
    with _cache_lock:
        wav_entries = len(_wav_cache)
        frame_entries = len(_frame_cache)
        
        wav_details = {}
        for key, (data, timestamp) in _wav_cache.items():
            age = time.time() - timestamp
            wav_details[key] = {
                "files": len(data),
                "age_seconds": round(age, 1),
                "expires_in": round(WAV_CACHE_DURATION - age, 1)
            }
        
        frame_details = {}
        for key, (data, timestamp) in _frame_cache.items():
            age = time.time() - timestamp
            frame_details[key] = {
                "files": len(data),
                "age_seconds": round(age, 1),
                "expires_in": round(FRAME_CACHE_DURATION - age, 1)
            }
    
    with _ssh_connection_lock:
        active_connections = list(_ssh_connections.keys())
    
    return {
        "wav_cache": {
            "entries": wav_entries,
            "details": wav_details,
            "duration": WAV_CACHE_DURATION
        },
        "frame_cache": {
            "entries": frame_entries,
            "details": frame_details,
            "duration": FRAME_CACHE_DURATION
        },
        "ssh_connections": {
            "active": active_connections,
            "count": len(active_connections)
        }
    }

# Load station configs at startup
def load_stations_config() -> Dict[str, dict]:
    with open(STATIONS_CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

STATIONS = load_stations_config()

@app.get("/stations")
def list_stations():
    """List available stations."""
    return list(STATIONS.keys())

@app.get("/frames", response_model=list[Frame])
def list_frames_on_demand(
    station: str = Query(..., description="Station name, e.g., CampiFlegrei"),
    date: str = Query(..., description="Date in YYMMDD format, e.g., 250411")
):
    """
    Lists frames for a specific date and station using optimized SSH connection pooling and caching.
    """
    logger.info(f"Optimized frame search: station={station}, date={date}")
    
    # Check cache first
    cached_results = get_cached_frames(station, date)
    if cached_results is not None:
        return cached_results
    
    if station not in STATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown station: {station}")
    
    station_cfg = STATIONS[station]
    remote_dir = station_cfg["remote_base"]
    
    if not remote_dir:
        raise HTTPException(status_code=500, detail="Remote directory not configured for station.")

    # Build optimized search patterns for both LoRes and HiRes
    patterns = [
        f"{remote_dir.replace('/', os.path.sep)}\\LoRes\\*T_{date}*.jpg",
        f"{remote_dir.replace('/', os.path.sep)}\\HiRes\\*T_{date}*.jpg"
    ]

    try:
        # Use connection pool for faster connection
        client = get_ssh_connection(station_cfg)
        
        all_stdout_lines = []
        
        # Execute searches for both directories
        for i, pattern in enumerate(patterns):
            res_type = "LoRes" if "LoRes" in pattern else "HiRes"
            command = f'dir /b "{pattern}" 2>nul'
            logger.info(f"Executing frame command for {res_type}: {command}")
            
            try:
                _, stdout, stderr = client.exec_command(command, timeout=10)
                stdout_lines = stdout.read().decode().strip().splitlines()
                
                # Add full paths for files found
                base_dir = f"{remote_dir.replace('/', os.path.sep)}\\{res_type}"
                for line in stdout_lines:
                    if line.strip():
                        full_path = f"{base_dir}\\{line.strip()}"
                        all_stdout_lines.append(full_path)
                
                logger.info(f"{res_type}: found {len(stdout_lines)} files")
                
            except Exception as e:
                logger.warning(f"Search for {res_type} failed: {e}")
                continue

        logger.info(f"Frame search for {station}: found {len(all_stdout_lines)} total files")

    except paramiko.AuthenticationException as e:
        logger.error(f"Frame SSH authentication failed for {station}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH authentication failed: {e}")
    except Exception as e:
        logger.error(f"Frame SSH execution failed for {station}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH execution failed: {e}")

    # --- Parse the results ---
    frames: list[Frame] = []
    for line in all_stdout_lines:
        full_path = line.strip().replace('\\', '/')
        filename = os.path.basename(full_path)
        
        # Determine resolution from path
        resolution = "HiRes" if "HiRes" in full_path else "LoRes"
        
        # Try both date formats for maximum compatibility
        for pattern in [LORES_RE, HIRES_RE]:
            m = pattern.match(filename)
            if m:
                if pattern == LORES_RE:
                    # YYMMDD format
                    station_name, date_str, time_str = m.groups()
                    ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M")
                else:
                    # YYMMDD format
                    station_name, date_str, time_str = m.groups()
                    ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")
                
                # Build URL with station name for proper proxy routing
                normalized_remote_dir = remote_dir.replace('\\', '/')
                if normalized_remote_dir.endswith('/'):
                    normalized_remote_dir = normalized_remote_dir[:-1]
                relative_path = full_path.replace(normalized_remote_dir, '', 1).lstrip('/')
                url = f"{FILE_SERVER_URL}/{station}/{relative_path}"
                
                frames.append(Frame(
                    station=station,
                    resolution=resolution,
                    timestamp=ts,
                    url=url
                ))
                break
        else:
            logger.warning(f"Frame filename doesn't match any pattern: {filename}")

    # Sort by timestamp (newest first)
    frames.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Cache the results for faster future access
    cache_frames(station, date, frames)
    
    logger.info(f"Returning {len(frames)} frames for {station} {date}")
    return frames

@app.get("/wavs", response_model=list[WavFile])
def list_wav_files(
    station: str = Query(..., description="Station name, e.g., CampiFlegrei"),
    date: str = Query(..., description="Date in YYMMDD format, e.g., 250411")
):
    """
    Lists WAV files for a specific date and station using optimized SSH connection pooling and caching.
    """
    logger.info(f"Optimized WAV search: station={station}, date={date}")
    
    # Check cache first
    cached_results = get_cached_wav_files(station, date)
    if cached_results is not None:
        return cached_results
    
    if station not in STATIONS:
        logger.error(f"Unknown station requested: {station}")
        raise HTTPException(status_code=400, detail=f"Unknown station: {station}")
    
    station_cfg = STATIONS[station]
    remote_dir = station_cfg["remote_base"]
    
    if not remote_dir:
        raise HTTPException(status_code=500, detail="Remote directory not configured for station.")

    # Build optimized search command - more targeted than recursive dir
    day_of_month = date[-2:]  # Last 2 digits (e.g., 250729 -> 29)
    
    # Try multiple search patterns for better coverage
    wav_dir = f"{remote_dir.replace('/', os.path.sep)}\\Wav"
    search_patterns = [
        f"{wav_dir}\\*Audio*_{day_of_month}UTC*.wav",
        f"{wav_dir}\\*_{day_of_month}UTC*.wav",  # Broader pattern
        f"{wav_dir}\\*{day_of_month}*.wav"       # Even broader for edge cases
    ]
    
    logger.info(f"WAV search for {station}: day={day_of_month}, searching {len(search_patterns)} patterns")

    try:
        # Use connection pool for faster connection
        client = get_ssh_connection(station_cfg)
        
        all_stdout_lines = []
        all_stderr_lines = []
        
        # Execute multiple targeted searches (faster than one big recursive search)
        for i, pattern in enumerate(search_patterns):
            command = f'dir /b "{pattern}" 2>nul'  # Suppress "File not found" errors
            logger.info(f"Executing WAV command {i+1}/{len(search_patterns)}: {command}")
            
            try:
                _, stdout, stderr = client.exec_command(command, timeout=15)
                stdout_lines = stdout.read().decode().strip().splitlines()
                stderr_lines = stderr.read().decode().strip()
                
                # Add full paths for files found
                for line in stdout_lines:
                    if line.strip():
                        full_path = f"{wav_dir}\\{line.strip()}"
                        all_stdout_lines.append(full_path)
                
                if stderr_lines:
                    all_stderr_lines.append(stderr_lines)
                    
                logger.info(f"Pattern {i+1}: found {len(stdout_lines)} files")
                
            except Exception as e:
                logger.warning(f"Search pattern {i+1} failed: {e}")
                continue

        # Remove duplicates while preserving order
        unique_lines = []
        seen = set()
        for line in all_stdout_lines:
            if line not in seen:
                unique_lines.append(line)
                seen.add(line)
        
        all_stdout_lines = unique_lines
        logger.info(f"WAV search for {station}: found {len(all_stdout_lines)} unique files total")

        if all_stderr_lines:
            combined_stderr = "; ".join(all_stderr_lines)
            logger.warning(f"WAV search warnings for {station}: {combined_stderr[:200]}")

    except paramiko.AuthenticationException as e:
        logger.error(f"WAV SSH authentication failed for {station}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH authentication failed: {e}")
    except paramiko.SSHException as e:
        logger.error(f"WAV SSH connection failed for {station}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH connection failed: {e}")
    except Exception as e:
        logger.error(f"WAV SSH execution failed for {station}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH execution failed: {e}")

    # --- Parse the results ---
    wav_files: list[WavFile] = []
    for line in all_stdout_lines:
        full_path = line.strip().replace('\\', '/')
        filename = os.path.basename(full_path)
        m_wav = WAV_RE.match(filename)
        
        if m_wav:
            station_name, day_str, time_str = m_wav.groups()
            # Convert day of month to full date using the input date
            year_month = date[:4]  # Extract YYMM from input date (e.g., 2507 from 250729)
            full_date_str = year_month + day_str  # Reconstruct YYMMDD
            # Parse full datetime (time_str is always 6 digits HHMMSS for WAV)
            ts = datetime.strptime(full_date_str + time_str, "%y%m%d%H%M%S")
            
            normalized_remote_dir = remote_dir.replace('\\', '/')
            if normalized_remote_dir.endswith('/'):
                normalized_remote_dir = normalized_remote_dir[:-1]
            relative_path = full_path.replace(normalized_remote_dir, '', 1).lstrip('/')
            url = f"{FILE_SERVER_URL}/{station}/{relative_path}"
            
            wav_files.append(WavFile(
                station=station,
                timestamp=ts,
                filename=filename,
                url=url,
                remote_path=full_path
            ))
        else:
            logger.warning(f"WAV filename doesn't match pattern: {filename}")

    # Sort by timestamp (newest first)
    wav_files.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Cache the results for faster future access
    cache_wav_files(station, date, wav_files)
    
    logger.info(f"Returning {len(wav_files)} WAV files for {station} {date}")
    return wav_files