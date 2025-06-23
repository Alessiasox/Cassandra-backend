FROM python:3.10-slim

COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        sshfs \            
        postgresql-client \
        fuse3 \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /dev/fuse && \
    chmod 666 /dev/fuse

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1                  \
    PYTHONDONTWRITEBYTECODE=1           \
    STATIONS_CONFIG=/app/ssh/stations.yaml \
    PYTHONPATH=/app

CMD [ "python", "--version" ]