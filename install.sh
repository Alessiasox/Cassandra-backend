#!/bin/bash

# VLF Network Monitoring System - One-Click Installer
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/vlf-network-monitoring/main/install.sh | bash

set -e

echo "🌋 VLF Network Monitoring System - One-Click Installer"
echo "====================================================="
echo ""

# Download and run the full setup
echo "📥 Downloading VLF Network Monitoring System..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download the repository
if command -v git &> /dev/null; then
    git clone https://github.com/your-repo/vlf-network-monitoring.git
else
    echo "Downloading repository..."
    curl -L https://github.com/your-repo/vlf-network-monitoring/archive/main.tar.gz | tar -xz
    mv vlf-network-monitoring-main vlf-network-monitoring
fi

cd vlf-network-monitoring

# Make setup script executable and run it
chmod +x setup.sh
./setup.sh

echo ""
echo "🎉 Installation complete!"
echo "The application is now running at: http://localhost:8501" 