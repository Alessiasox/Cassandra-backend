#!/bin/bash
set -e

# This script mounts all remote stations using sshfs and then starts nginx.
# It reads station configurations from stations.yaml and mounts each to a separate subdirectory.

CONFIG_FILE="/app/ssh/stations.yaml"
MOUNT_BASE="/usr/share/nginx/html"
SSH_PRIVATE_KEY_PATH="/app/ssh/id_ed25519"

echo "Multi-station SSHFS proxy starting..."
echo "Reading stations from: $CONFIG_FILE"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file $CONFIG_FILE not found." >&2
  exit 1
fi

# Create base mount directory
mkdir -p "$MOUNT_BASE"

# Remove known_hosts to avoid prompts
rm -f /root/.ssh/known_hosts

# Simple YAML parser for station configuration
declare -A host user remote_base port
current_station=""

while IFS=: read -r key value; do
  key=$(echo "$key" | xargs)    # trim whitespace
  value=$(echo "$value" | xargs) # trim whitespace

  case "$key" in
    "")       continue ;;                    # skip empty lines
    \#*)      continue ;;                    # skip comments
    host)     
        if [ -n "$current_station" ]; then
            host["$current_station"]="$value"
        fi
        ;;
    username) 
        if [ -n "$current_station" ]; then
            user["$current_station"]="$value"
        fi
        ;;
    remote_base) 
        if [ -n "$current_station" ]; then
            remote_base["$current_station"]="$value"
        fi
        ;;
    port)     
        if [ -n "$current_station" ]; then
            port["$current_station"]="${value:-22}"
        fi
        ;;
    *)
        # If it's not a known property and value is empty, it's a station name
        if [ -z "$value" ] && [ -n "$key" ]; then
            current_station="$key"
            current_station=$(echo "$current_station" | tr -d ' ')
        fi
        ;;
  esac
done < "$CONFIG_FILE"

# Mount each station to its own subdirectory
mounted_stations=()
for station in "${!host[@]}"; do
  station_host="${host[$station]}"
  station_user="${user[$station]}"
  station_remote_base="${remote_base[$station]}"
  station_port="${port[$station]:-22}"
  
  station_mount_point="$MOUNT_BASE/$station"
  
  echo "Mounting station: $station"
  echo "  Host: $station_host"
  echo "  User: $station_user" 
  echo "  Remote: $station_remote_base"
  echo "  Mount point: $station_mount_point"
  
  # Create station-specific mount directory
  mkdir -p "$station_mount_point"
  
  # Attempt to mount the station
  echo "Attempting to mount $station_remote_base from ${station_user}@${station_host}..."
  
  if timeout 30 sshfs \
    -o allow_other \
    -o reconnect \
    -o StrictHostKeyChecking=no \
    -o LogLevel=ERROR \
    -o port="$station_port" \
    -o "identityfile=${SSH_PRIVATE_KEY_PATH}" \
    "${station_user}@${station_host}:${station_remote_base//\\//}" \
    "$station_mount_point"; then
    
    echo "✅ Successfully mounted $station"
    mounted_stations+=("$station")
  else
    echo "❌ Failed to mount $station (timeout or connection error) - continuing with other stations"
    rmdir "$station_mount_point" 2>/dev/null || true
  fi
  
  echo ""
done

# Check if at least one station was mounted
if [ ${#mounted_stations[@]} -eq 0 ]; then
  echo "Error: No stations could be mounted successfully." >&2
  echo "Proxy will sleep indefinitely for debugging." >&2
  tail -f /dev/null
fi

echo "Successfully mounted ${#mounted_stations[@]} stations: ${mounted_stations[*]}"
echo "Starting Nginx..."

# Start nginx in the background so we can run the auto-remount loop
nginx -g 'daemon off;' &
nginx_pid=$!

# Auto-remount function for multiple stations
auto_remount() {
  while true; do
    sleep 30
    
    for station in "${mounted_stations[@]}"; do
      station_mount_point="$MOUNT_BASE/$station"
      
      if ! mountpoint -q "$station_mount_point"; then
        echo "[Auto-Remount] $station mount lost, attempting to remount..."
        
        station_host="${host[$station]}"
        station_user="${user[$station]}"
        station_remote_base="${remote_base[$station]}"
        station_port="${port[$station]:-22}"
        
        # Clean up any stale mount
        fusermount -u "$station_mount_point" 2>/dev/null || true
        
        # Attempt remount
        if sshfs \
          -o allow_other \
          -o reconnect \
          -o StrictHostKeyChecking=no \
          -o LogLevel=ERROR \
          -o port="$station_port" \
          -o "identityfile=${SSH_PRIVATE_KEY_PATH}" \
          "${station_user}@${station_host}:${station_remote_base//\\//}" \
          "$station_mount_point"; then
          echo "[Auto-Remount] ✅ Successfully remounted $station"
        else
          echo "[Auto-Remount] ❌ Failed to remount $station"
        fi
      fi
    done
  done
}

# Start auto-remount in background
auto_remount &

# Wait for nginx to finish
wait $nginx_pid