#!/usr/bin/env bash
set -euo pipefail

MOUNT_POINT=${1:-$(pwd)/vlfstore}
CONFIG_FILE="$(dirname "$0")/../ssh/stations.yaml"

# Check if sshfs exists
command -v sshfs >/dev/null || {
  echo "sshfs not found. Install macFUSE + sshfs first." >&2
  exit 1
}

mkdir -p "$MOUNT_POINT"

# Simple YAML parser for station configuration
# Expected format:
# Duronia:
#   host: 100.76.133.15
#   username: vlffetch
#   remote_base: C:/htdocs/VLF
#   key_path: ~/.ssh/id_ed25519

current_station=""
while IFS=: read -r key value; do
  key=$(echo "$key" | xargs)        # trim
  value=$(echo "$value" | xargs)    # trim

  case "$key" in
    "")       continue ;;           # skip empty lines
    \#*)      continue ;;           # skip comments
    *":")     current_station=${key%:} ;;
    host)     host[$current_station]=$value ;;
    username) user[$current_station]=$value ;;
    remote_base) base[$current_station]=$value ;;
    key_path) key[$current_station]=$value ;;
  esac
done < "$CONFIG_FILE"

# Mount each station
for st in "${!host[@]}"; do
  local_dir="$MOUNT_POINT/$st"
  mkdir -p "$local_dir"

  ssh_key=${key[$st]:-$HOME/.ssh/id_ed25519}

  # Check if already mounted
  if mount | grep -q " $local_dir "; then
    echo "$st already mounted"
    continue
  fi

  echo "Mounting $st to $local_dir"
  sshfs \
    -o IdentityFile="$ssh_key" \
    -o allow_other \
    "${user[$st]}@${host[$st]}:${base[$st]//\\//}" \
    "$local_dir"
done