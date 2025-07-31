#!/bin/bash

# VLF Network Monitoring System - Container Cleanup
# Use this script if you encounter container name conflicts

echo "🧹 Cleaning up Cassandra containers..."

# Stop docker-compose services
echo "Stopping docker-compose services..."
docker-compose down 2>/dev/null || true

# Find and stop/remove any remaining cassandra containers
existing_containers=$(docker ps -aq --filter "name=cassandra" 2>/dev/null)
if [ ! -z "$existing_containers" ]; then
    echo "Found existing containers: $existing_containers"
    echo "Stopping containers..."
    docker stop $existing_containers 2>/dev/null || true
    echo "Removing containers..."
    docker rm -f $existing_containers 2>/dev/null || true
    echo "✅ Cleanup complete!"
else
    echo "✅ No cassandra containers found"
fi

echo ""
echo "You can now run:"
echo "  docker-compose up -d    # Start the application"
echo "  ./setup.sh              # Run full setup again" 