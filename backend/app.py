# backend/app.py
import os
import re
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import paramiko

# --- Environment and Configuration ---

FILE_SERVER_URL = os.getenv("FILE_SERVER_URL", "http://localhost:8080")
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH")
REMOTE_DIR = os.getenv("REMOTE_DIR", "C:/htdocs/VLF")

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


@app.get("/frames", response_model=list[Frame])
def list_frames_on_demand(date: str = Query(..., description="Date in YYMMDD format, e.g., 250411")):
    """
    Lists frames for a specific date by running a remote command over SSH.
    """
    if not all([SSH_HOST, SSH_USER, SSH_PRIVATE_KEY_PATH, REMOTE_DIR]):
        raise HTTPException(status_code=500, detail="SSH environment variables not set.")

    # Build the remote command to search for files
    search_pattern = f"{REMOTE_DIR.replace('/', os.path.sep)}\\*T_{date}*.jpg"
    command = f'dir /s /b "{search_pattern}"'

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=SSH_HOST, # type: ignore
            username=SSH_USER, # type: ignore
            key_filename=SSH_PRIVATE_KEY_PATH, # type: ignore
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
        filename = os.path.basename(line.strip())
        
        m_lores = LORES_RE.match(filename)
        m_hires = HIRES_RE.match(filename)

        if m_lores:
            station, date_str, time_str = m_lores.groups()
            resolution = "LoRes"
            ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M")
        elif m_hires:
            station, date_str, time_str = m_hires.groups()
            resolution = "HiRes"
            ts = datetime.strptime(date_str + time_str, "%y%m%d%H%M%S")
        else:
            continue
        
        # Normalize both paths to use forward slashes for reliable replacement
        normalized_line = line.strip().replace("\\", "/")
        normalized_base = REMOTE_DIR.replace("\\", "/")
        
        relative_path = normalized_line.replace(normalized_base, "", 1).strip("/")
        url = f"{FILE_SERVER_URL}/{relative_path}"

        frames.append(Frame(station=station, resolution=resolution, timestamp=ts, url=url))

    return frames