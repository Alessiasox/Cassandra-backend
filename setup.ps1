# VLF Network Monitoring System - Windows Setup Script
# Run this in PowerShell as Administrator

param(
    [switch]$Force
)

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

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Install Chocolatey package manager
function Install-Chocolatey {
    Write-Step "Installing Chocolatey package manager..."
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Success "Chocolatey installed"
    } else {
        Write-Success "Chocolatey already installed"
    }
}

# Install Docker Desktop
function Install-Docker {
    Write-Step "Checking Docker installation..."
    
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Docker Desktop..."
        choco install docker-desktop -y
        Write-Warning "Docker Desktop installed. Please:"
        Write-Warning "1. Restart your computer"
        Write-Warning "2. Launch Docker Desktop"
        Write-Warning "3. Enable WSL 2 integration"
        Write-Warning "4. Run this script again"
        pause
        exit
    } else {
        Write-Success "Docker found"
    }
}

# Install Git
function Install-Git {
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

# Install Tailscale
function Install-Tailscale {
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
        
        $config = @"
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
"@
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
        $env = @"
# VLF Network Environment Configuration
SSH_PRIVATE_KEY_PATH=/app/ssh/id_ed25519
FILE_SERVER_URL=http://localhost:8080
COMPOSE_PROJECT_NAME=vlf-network
"@
        $env | Out-File -FilePath ".env" -Encoding UTF8
        Write-Success "Environment file created"
    } else {
        Write-Success "Environment file already exists"
    }
}

# Copy SSH keys
function Copy-SSHKeys {
    Write-Step "Copying SSH keys to project..."
    
    New-Item -ItemType Directory -Path "ssh" -Force | Out-Null
    Copy-Item "$env:USERPROFILE\.ssh\id_ed25519" "ssh\" -Force
    Copy-Item "$env:USERPROFILE\.ssh\id_ed25519.pub" "ssh\" -Force
    
    Write-Success "SSH keys copied"
}

# Start application
function Start-Application {
    Write-Step "Starting VLF Network Monitoring System..."
    
    docker-compose build
    docker-compose up -d
    
    Write-Success "Application started!"
    Write-Host ""
    Write-Host "🌐 Access the application at: http://localhost:8501" -ForegroundColor Cyan
    Write-Host "📊 Backend API at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "📁 File server at: http://localhost:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Warning "Make sure all VLF stations have:"
    Write-Warning "1. Tailscale running"
    Write-Warning "2. SSH server enabled"
    Write-Warning "3. Your SSH public key authorized"
}

# Main setup flow
function Main {
    if (!(Test-Administrator)) {
        Write-Error "Please run this script as Administrator"
        pause
        exit 1
    }
    
    Write-Step "Starting Windows setup..."
    
    Install-Chocolatey
    Install-Docker
    Install-Git
    Setup-SSH
    Install-Tailscale
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