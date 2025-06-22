# Use the standard nginx image as a base
FROM nginx:stable

# Install sshfs and fuse for mounting
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        sshfs \
        fuse3 \
    && rm -rf /var/lib/apt/lists/*

# Copy the entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set our script as the container's entrypoint
ENTRYPOINT ["/entrypoint.sh"] 