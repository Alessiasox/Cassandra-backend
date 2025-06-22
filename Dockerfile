# ──────────────────────────────────────────────────────────────
# Base image: smallest Debian-based Python that can still apt-install
FROM python:3.10-slim

COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

# --- OS packages we need inside the container -----------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        sshfs \            
        postgresql-client \
        fuse3 \
 && rm -rf /var/lib/apt/lists/*

# --- Create FUSE device and set permissions ------------------
RUN mkdir -p /dev/fuse && \
    chmod 666 /dev/fuse

# --- Python deps ----------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy project code ----------------------------------------
COPY . /app

# --- Environment tweaks ---------------------------------------
ENV PYTHONUNBUFFERED=1                  \
    PYTHONDONTWRITEBYTECODE=1           \
    STATIONS_CONFIG=/app/ssh/stations.yaml

# The actual command is supplied by docker-compose (entrypoint.sh)
CMD [ "python", "--version" ]