# VLF Network Monitoring System - Windows Setup
# Requires Administrator privileges

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires Administrator privileges. Please run PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

Write-Host "🌋 VLF Network Monitoring System - Windows Setup" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

function Write-Step {
    param($Message)
    Write-Host "[STEP] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[⚠] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

# Install Chocolatey
function Install-Chocolatey {
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Chocolatey package manager..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Success "Chocolatey installed"
    } else {
        Write-Success "Chocolatey already installed"
    }
}

# Check Docker installation
function Check-Docker {
    Write-Step "Checking Docker installation..."
    
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Docker Desktop..."
        choco install docker-desktop -y
        Write-Warning "Docker Desktop installed. Please:"
        Write-Warning "1. Restart your computer"
        Write-Warning "2. Launch Docker Desktop"
        Write-Warning "3. Enable WSL 2 integration"
        Write-Warning "4. Run this script again"
        exit 0
    } else {
        Write-Success "Docker found"
    }
}

# Check Git installation
function Check-Git {
    Write-Step "Checking Git installation..."
    
    if (!(Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Git..."
        choco install git -y
        Write-Success "Git installed"
    } else {
        Write-Success "Git already installed"
    }
}

# Setup SSH keys
function Setup-SSH {
    Write-Step "Setting up SSH keys..."
    
    $sshDir = "$env:USERPROFILE\.ssh"
    if (!(Test-Path $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    }
    
    $keyPath = "$sshDir\id_ed25519"
    if (!(Test-Path $keyPath)) {
        Write-Step "Generating SSH key..."
        $email = Read-Host "Enter your email for SSH key"
        ssh-keygen -t ed25519 -C $email -f $keyPath -N '""'
        Write-Success "SSH key generated"
    } else {
        Write-Success "SSH key already exists"
    }
    
    # Copy public key to clipboard
    Get-Content "$keyPath.pub" | Set-Clipboard
    Write-Success "Public key copied to clipboard"
    Write-Warning "Please add this public key to your VLF stations' authorized_keys"
}

# Setup Tailscale
function Setup-Tailscale {
    Write-Step "Setting up Tailscale..."
    
    if (!(Get-Command tailscale -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Tailscale..."
        choco install tailscale -y
        Write-Success "Tailscale installed"
    } else {
        Write-Success "Tailscale already installed"
    }
    
    Write-Warning "Please run 'tailscale up' to connect to your network"
}

# Setup project configuration
function Setup-Config {
    Write-Step "Setting up configuration..."
    
    if (!(Test-Path "ssh\stations.yaml")) {
        Write-Step "Creating station configuration..."
        New-Item -ItemType Directory -Path "ssh" -Force | Out-Null
        
        $config = @'
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
'@
        $config | Out-File -FilePath "ssh\stations.yaml" -Encoding UTF8
        Write-Warning "Please edit ssh\stations.yaml with your actual station details"
    } else {
        Write-Success "Configuration already exists"
    }
}

# Create environment file
function Create-Environment {
    Write-Step "Creating environment file..."
    
    if (!(Test-Path ".env")) {
        $env = @'
# VLF Network Environment Configuration
SSH_PRIVATE_KEY_PATH=/app/ssh/id_ed25519
FILE_SERVER_URL=http://localhost:8080
COMPOSE_PROJECT_NAME=vlf-network
'@
        $env | Out-File -FilePath ".env" -Encoding UTF8
        Write-Success "Environment file created"
    } else {
        Write-Success "Environment file already exists"
    }
}

# Copy SSH keys
function Copy-SSHKeys {
    Write-Step "Copying SSH keys to project..."
    
    $sshSourceDir = "$env:USERPROFILE\.ssh"
    $sshTargetDir = "ssh"
    
    if (!(Test-Path $sshTargetDir)) {
        New-Item -ItemType Directory -Path $sshTargetDir -Force | Out-Null
    }
    
    Copy-Item "$sshSourceDir\id_ed25519" "$sshTargetDir\" -Force
    Copy-Item "$sshSourceDir\id_ed25519.pub" "$sshTargetDir\" -Force
    
    Write-Success "SSH keys copied"
}

# Start the application
function Start-Application {
    Write-Step "Starting VLF Network Monitoring System..."
    
    # Clean up any existing containers to prevent conflicts
    Write-Step "Cleaning up existing containers..."
    docker-compose down 2>$null
    
    # Stop and remove any remaining cassandra containers
    $existing = docker ps -aq --filter "name=cassandra" 2>$null
    if ($existing) {
        docker stop $existing 2>$null
        docker rm -f $existing 2>$null
    }
    Write-Success "Container cleanup complete"
    
    docker-compose build
    docker-compose up -d
    
    Write-Success "Application started successfully!"
    Write-Host ""
    Write-Host "🌐 Access the application at: http://localhost:8501" -ForegroundColor Cyan
    Write-Host "📊 Backend API at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "📁 File server at: http://localhost:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Warning "Make sure all your VLF stations are:"
    Write-Warning "1. Connected to Tailscale"
    Write-Warning "2. Have SSH server running"
    Write-Warning "3. Have your SSH public key in authorized_keys"
}

# Main execution
function Main {
    Write-Step "Starting Windows setup..."
    
    Install-Chocolatey
    Check-Docker
    Check-Git
    Setup-SSH
    Setup-Tailscale
    Setup-Config
    Create-Environment
    Copy-SSHKeys
    
    $confirm = Read-Host "Ready to start the application? (y/N)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        Start-Application
    } else {
        Write-Warning "Setup complete. Run 'docker-compose up -d' when ready"
    }
}

Main 