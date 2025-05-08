import os
import requests
from datetime import datetime, timezone

API = os.getenv("API_URL", "http://localhost:8000")
FS  = os.getenv("FILE_SERVER_URL", "http://localhost:8080/files")

def _range():
    # example time‐range from your live station
    return {
        "station":    "Duronia",
        "resolution": "LoRes",
        "start":      "2025-04-09T22:00:00Z",
        "end":        "2025-04-24T22:00:00Z",
    }

def test_some_frames_exist():
    r = requests.get(f"{API}/frames", params=_range(), timeout=10)
    r.raise_for_status()
    data = r.json()
    assert len(data) > 0

def test_urls_are_accessible():
    r = requests.get(f"{API}/frames", params=_range(), timeout=10)
    r.raise_for_status()
    data = r.json()
    # hit the first image URL
    img_url = data[0]["url"]
    r2 = requests.get(img_url, timeout=10)
    r2.raise_for_status()
    assert r2.headers["Content-Type"].startswith("image/")