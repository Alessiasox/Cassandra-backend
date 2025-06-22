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
    Lists frames for a specific date by running specific, non-recursive remote commands.
    """
    if not all([SSH_HOST, SSH_USER, SSH_PRIVATE_KEY_PATH, REMOTE_DIR]):
        raise HTTPException(status_code=500, detail="SSH environment variables not set.")

    # Build two specific, non-recursive commands for LoRes and HiRes
    lores_path = f"{REMOTE_DIR.replace('/', os.path.sep)}\\LoRes\\*T_{date}*.jpg"
    hires_path = f"{REMOTE_DIR.replace('/', os.path.sep)}\\HiRes\\*T_{date}*.jpg"
    command = f'dir /b "{lores_path}" & dir /b "{hires_path}"'

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
        
        # The new dir command only returns filenames, so we must prepend the path.
        if "LoRes" in normalized_line:
            base_path = f"{REMOTE_DIR}/LoRes"
        elif "HiRes" in normalized_line:
            base_path = f"{REMOTE_DIR}/HiRes"
        else:
            continue # Should not happen

        full_path = f"{base_path}/{normalized_line}"
        normalized_base = REMOTE_DIR.replace("\\", "/")
        
        relative_path = full_path.replace(normalized_base, "", 1).strip("/")
        url = f"{FILE_SERVER_URL}/{relative_path}"

        frames.append(Frame(station=station, resolution=resolution, timestamp=ts, url=url))

    return frames