#!/usr/bin/env python3
"""
Walk a mounted VLF directory tree and upsert file metadata into Postgres.
"""

import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

def scan_and_upsert(db_url: str, mount_root: str):
    conn = psycopg2.connect(db_url)
    cur  = conn.cursor()
    # collect (station, resolution, timestamp, key)
    to_insert = []
    for station in os.listdir(mount_root):
        station_dir = os.path.join(mount_root, station)
        if not os.path.isdir(station_dir):
            continue
        for resolution in ("LoRes", "HiRes", "Wav"):
            res_dir = os.path.join(station_dir, resolution)
            if not os.path.isdir(res_dir):
                continue
            for root, _, files in os.walk(res_dir):
                for fn in files:
                    ext = fn.lower().rsplit(".", 1)[-1]
                    if resolution == "Wav" and ext != "wav":
                        continue
                    if resolution != "Wav" and ext not in ("jpg", "jpeg", "png"):
                        continue
                    full = os.path.join(root, fn)
                    mtime = datetime.fromtimestamp(os.path.getmtime(full))
                    # key is path relative to mount_root, so nginx/object-store can serve
                    key = os.path.relpath(full, mount_root)
                    to_insert.append((station, resolution, mtime, key))

    if not to_insert:
        print("No files found under", mount_root)
    else:
        # bulk upsert: ignore conflicts on primary key
        execute_values(cur,
            """
            INSERT INTO frames (station, resolution, timestamp, key)
            VALUES %s
            ON CONFLICT (station, resolution, timestamp) DO NOTHING
            """,
            to_insert
        )
        conn.commit()
        print(f"Upserted {len(to_insert)} rows.")

    cur.close()
    conn.close()


def main():
    p = argparse.ArgumentParser(description="Scan VLF mount and ingest to Postgres")
    p.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL"),
        help="Postgres URL (e.g. postgres://user:pw@host:5432/dbname)"
    )
    p.add_argument(
        "--mount",
        default=os.getenv("VLF_MOUNT", "/mnt/vlf"),
        help="Root path where stations are SSHFS-mounted"
    )
    args = p.parse_args()

    if not args.db_url:
        print("ERROR: DATABASE_URL not set")
        exit(1)

    scan_and_upsert(args.db_url, args.mount)


if __name__ == "__main__":
    main()