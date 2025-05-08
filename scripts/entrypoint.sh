#!/usr/bin/env bash
set -e

# Only the *first* arg is the final CMD (uvicorn ...),
# everything before we do the mount.

# ---------- 1. mount with sshfs --------------------------------------
mkdir -p "$VLF_MOUNT"

/usr/bin/sshfs \
    -o StrictHostKeyChecking=no \
    -o IdentityFile="$SSH_KEY_PATH" \
    -o allow_other \
    "${SSHFS_USER}@${VLF_HOST}:${REMOTE_BASE//\\//}" \
    "$VLF_MOUNT"

echo "✔ SSHFS mounted at $VLF_MOUNT"

# ---------- 2. init-db (first run only; harmless if table exists) ----
psql "$DATABASE_URL" -f /app/ingest/init_db.sql || true

# ---------- 3. optional: ingest once --------------------------------
python /app/ingest/scan_metadata.py --db-url "$DATABASE_URL" --mount "$VLF_MOUNT" || true

# ---------- 4. hand over to the real CMD ----------------------------
exec "$@"