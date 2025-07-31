#!/bin/bash

# VLF Network Monitoring System - Automated Setup
# Supports macOS, Linux, and Windows (via WSL)

set -e

echo "🌋 VLF Network Monitoring System - Setup Wizard"
echo "=============================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    print_success "Detected OS: $OS"
}

# Check if Docker is installed
check_docker() {
    print_step "Checking Docker installation..."
    
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        print_success "Docker and Docker Compose found"
        return 0
    else
        print_warning "Docker not found. Installing Docker..."
        install_docker
    fi
}

# Install Docker based on OS
install_docker() {
    case $OS in
        "macos")
            print_step "Please install Docker Desktop for Mac from: https://docker.com/products/docker-desktop"
            print_warning "After installation, restart this script"
            exit 1
            ;;
        "linux")
            print_step "Installing Docker on Linux..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            print_success "Docker installed. Please log out and back in, then restart this script"
            exit 1
            ;;
        "windows")
            print_step "Please install Docker Desktop for Windows from: https://docker.com/products/docker-desktop"
            print_warning "Make sure to enable WSL 2 backend"
            exit 1
            ;;
    esac
}

# Setup SSH keys
setup_ssh() {
    print_step "Setting up SSH keys for VLF stations..."
    
    SSH_DIR="$HOME/.ssh"
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    
    if [[ ! -f "$SSH_DIR/id_ed25519" ]]; then
        print_step "Generating new SSH key..."
        read -p "Enter your email for SSH key: " email
        ssh-keygen -t ed25519 -C "$email" -f "$SSH_DIR/id_ed25519" -N ""
        print_success "SSH key generated"
    else
        print_success "SSH key already exists"
    fi
    
    # Copy public key to clipboard
    if [[ "$OS" == "macos" ]]; then
        cat "$SSH_DIR/id_ed25519.pub" | pbcopy
        print_success "Public key copied to clipboard"
    elif command -v xclip &> /dev/null; then
        cat "$SSH_DIR/id_ed25519.pub" | xclip -selection clipboard
        print_success "Public key copied to clipboard"
    else
        print_warning "Please copy this public key to your VLF stations:"
        echo "----------------------------------------"
        cat "$SSH_DIR/id_ed25519.pub"
        echo "----------------------------------------"
    fi
}

# Setup Tailscale
setup_tailscale() {
    print_step "Setting up Tailscale VPN..."
    
    if command -v tailscale &> /dev/null; then
        print_success "Tailscale already installed"
    else
        print_step "Installing Tailscale..."
        case $OS in
            "macos")
                print_step "Download Tailscale from: https://tailscale.com/download/mac"
                ;;
            "linux")
                curl -fsSL https://tailscale.com/install.sh | sh
                ;;
            "windows")
                print_step "Download Tailscale from: https://tailscale.com/download/windows"
                ;;
        esac
    fi
    
    print_warning "Please run 'tailscale up' to connect to your Tailscale network"
    print_warning "Make sure all your VLF stations are also connected to the same Tailscale network"
}

# Setup configuration
setup_config() {
    print_step "Setting up station configuration..."
    
    if [[ ! -f "ssh/stations.yaml" ]]; then
        print_step "Creating station configuration template..."
        mkdir -p ssh
        cat > ssh/stations.yaml << 'EOF'
# VLF Network Stations Configuration
# Add your stations here following this format:

# ExampleStation:
#   host: 100.x.x.x  # Tailscale IP of the station
#   port: 22
#   username: stationuser
#   remote_base: C:/htdocs/VLF

CampiFlegrei:
  host: 100.x.x.x  # Replace with your station's Tailscale IP
  port: 22
  username: username  # Replace with your station's username
  remote_base: C:/htdocs/VLF
EOF
        print_warning "Please edit ssh/stations.yaml with your actual station details"
    else
        print_success "Station configuration already exists"
    fi
}

# Create environment file
create_env() {
    print_step "Creating environment configuration..."
    
    if [[ ! -f ".env" ]]; then
        cat > .env << EOF
# VLF Network Environment Configuration
SSH_PRIVATE_KEY_PATH=/app/ssh/id_ed25519
FILE_SERVER_URL=http://localhost:8080
COMPOSE_PROJECT_NAME=vlf-network
EOF
        print_success "Environment file created"
    else
        print_success "Environment file already exists"
    fi
}

# Copy SSH keys to project
copy_ssh_keys() {
    print_step "Setting up SSH keys for the application..."
    
    mkdir -p ssh
    cp "$HOME/.ssh/id_ed25519" ssh/
    cp "$HOME/.ssh/id_ed25519.pub" ssh/
    chmod 600 ssh/id_ed25519
    chmod 644 ssh/id_ed25519.pub
    
    print_success "SSH keys copied to project directory"
}

# Start the application
start_app() {
    print_step "Starting VLF Network Monitoring System..."
    
    # Clean up any existing containers to prevent conflicts
    print_step "Cleaning up existing containers..."
    docker-compose down 2>/dev/null || true
    
    # Stop and remove any remaining cassandra containers that might conflict
    existing_containers=$(docker ps -aq --filter "name=cassandra" 2>/dev/null)
    if [ ! -z "$existing_containers" ]; then
        docker stop $existing_containers 2>/dev/null || true
        docker rm -f $existing_containers 2>/dev/null || true
    fi
    print_success "Container cleanup complete"
    
    docker-compose build
    docker-compose up -d
    
    print_success "Application started successfully!"
    echo ""
    echo "🌐 Access the application at: http://localhost:8501"
    echo "📊 Backend API at: http://localhost:8000"
    echo "📁 File server at: http://localhost:8080"
    echo ""
    print_warning "Make sure all your VLF stations are:"
    print_warning "1. Connected to Tailscale"
    print_warning "2. Have SSH server running"
    print_warning "3. Have your SSH public key in authorized_keys"
    echo ""
}

# Main installation flow
main() {
    echo "Starting automated setup..."
    echo ""
    
    detect_os
    check_docker
    setup_ssh
    setup_tailscale
    setup_config
    create_env
    copy_ssh_keys
    
    echo ""
    read -p "Ready to start the application? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        start_app
    else
        print_warning "Setup complete. Run 'docker-compose up -d' when ready to start"
    fi
}

main "$@" 