# backend/app.py
import os
import re
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import paramiko
import yaml
from typing import Dict

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

app = FastAPI(title="Cassandra On-Demand API")

# --- Models ---

class Frame(BaseModel):
    station: str
    resolution: str
    timestamp: datetime
    url: str

# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}

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
    Lists frames for a specific date and station by running a remote command over SSH.
    """
    if station not in STATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown station: {station}")
    station_cfg = STATIONS[station]
    ssh_host = station_cfg["host"]
    ssh_user = station_cfg["username"]
    ssh_port = station_cfg.get("port", 22)
    remote_dir = station_cfg["remote_base"]
    ssh_private_key_path = os.getenv("SSH_PRIVATE_KEY_PATH")
    if not all([ssh_host, ssh_user, ssh_private_key_path, remote_dir]):
        raise HTTPException(status_code=500, detail="SSH configuration missing for station.")

    # Build the remote command to search for files
    search_pattern = f"{remote_dir.replace('/', os.path.sep)}\\*T_{date}*.jpg"
    command = f'dir /s /b "{search_pattern}"'

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ssh_host,
            username=ssh_user,
            key_filename=ssh_private_key_path,
            port=ssh_port,
            timeout=10
        )
        _, stdout, stderr = client.exec_command(command)
        stdout_lines = stdout.read().decode().strip().splitlines()
        stderr_lines = stderr.read().decode().strip()
        client.close()

        if stderr_lines and "File Not Found" not in stderr_lines:
            raise HTTPException(status_code=500, detail=f"Remote command error: {stderr_lines}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH execution failed: {e}")

    # --- Parse the results ---
    frames: list[Frame] = []
    for line in stdout_lines:
        full_path = line.strip().replace('\\', '/')
        filename = os.path.basename(full_path)
        m_lores = LORES_RE.match(filename)
        m_hires = HIRES_RE.match(filename)
        if m_lores:
            station_name, date_str, time_str = m_lores.groups()
            resolution = "LoRes"
            ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M")
        elif m_hires:
            station_name, date_str, time_str = m_hires.groups()
            resolution = "HiRes"
            ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")
        else:
            continue
        normalized_remote_dir = remote_dir.replace('\\', '/')
        if normalized_remote_dir.endswith('/'):
            normalized_remote_dir = normalized_remote_dir[:-1]
        relative_path = full_path.replace(normalized_remote_dir, '', 1).lstrip('/')
        url = f"{FILE_SERVER_URL}/{relative_path}"
        frames.append(Frame(station=station, resolution=resolution, timestamp=ts, url=url))
    return frames