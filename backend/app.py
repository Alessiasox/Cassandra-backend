# backend/app.py
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL    = os.getenv("DATABASE_URL")
FILE_SERVER_URL = os.getenv("FILE_SERVER_URL", "http://localhost")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set")

app = FastAPI(title="Cassandra Frames API")

# 1) mount object‐store or sshfs‐mounted folder
#    so that /files/... serves /mnt/vlf/...
app.mount(
    "/files",
    StaticFiles(directory="/mnt/vlf"),
    name="files",
)


class Frame(BaseModel):
    station:    str
    resolution: str
    timestamp:  datetime
    url:        str  # fully qualified HTTP URL


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/frames", response_model=list[Frame])
def list_frames(
    station:    str = Query(...),
    resolution: str = Query(...),
    start:      datetime = Query(...),
    end:        datetime = Query(...),
):
    """
    Return all frames in Postgres between start/end (inclusive).
    Builds a URL under /files/<resolution>/<filename>.
    """
    sql = """
        SELECT station, resolution, timestamp, key
        FROM frames
        WHERE station    = %s
          AND resolution = %s
          AND timestamp  BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (station, resolution, start, end))
            rows = cur.fetchall()
    finally:
        conn.close()

    out: list[Frame] = []
    for r in rows:
        # r["key"] is e.g. "LoRes/G1_LoResT_250410UTC144000.jpg"
        url = f"{FILE_SERVER_URL}/files/{r['key']}"
        out.append(Frame(
            station    = r["station"],
            resolution = r["resolution"],
            timestamp  = r["timestamp"],
            url        = url,
        ))
    return out