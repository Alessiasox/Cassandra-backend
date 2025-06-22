#!/bin/bash
set -ex

# This script mounts a remote directory using sshfs and then starts nginx.
# It is intended to be the main entrypoint for the 'proxy' container.

# Check for required environment variables
if [ -z "$SSH_USER" ] || [ -z "$SSH_HOST" ] || [ -z "$SSH_PRIVATE_KEY_PATH" ] || [ -z "$REMOTE_DIR" ]; then
  echo "Error: Missing required SSH environment variables." >&2
  exit 1
fi

MOUNT_POINT="/usr/share/nginx/html"
mkdir -p "$MOUNT_POINT"

echo "Attempting to mount ${REMOTE_DIR} from ${SSH_USER}@${SSH_HOST}..."

# Mount the remote directory with verbose logging.
# We use `-o daemon_timeout=30` to help with debugging hangs.
sshfs \
  -o allow_other \
  -o reconnect \
  -o StrictHostKeyChecking=no \
  -o LogLevel=DEBUG3 \
  -o "identityfile=${SSH_PRIVATE_KEY_PATH}" \
  "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}" \
  "${MOUNT_POINT}"

echo "Mount command finished. Checking mount status..."

# Verify that the mount was successful before starting nginx
if ! mountpoint -q "${MOUNT_POINT}"; then
    echo "Error: Mount failed. Check the logs above for details." >&2
    # Keep the container alive for debugging if the mount fails
    echo "Mount failed. Container will sleep indefinitely for debugging." >&2
    tail -f /dev/null
fi

echo "✔ Mount successful. Starting Nginx..."

# Start nginx in the foreground.
# This will keep the container running.
exec nginx -g 'daemon off;'