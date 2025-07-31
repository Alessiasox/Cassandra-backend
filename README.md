# 🌋 VLF Network Monitoring System

A comprehensive web-based application for monitoring Very Low Frequency (VLF) electromagnetic data from remote research stations. Built for INGV (Istituto Nazionale di Geofisica e Vulcanologia) to visualize spectrograms, analyze waveforms, and perform AI-powered signal analysis.

![VLF Monitoring Dashboard](docs/screenshot.png)

## ✨ Features

- **📈 Real-time Spectrogram Visualization** - High/Low resolution images with time-based filtering
- **🎵 WAV Waveform Analysis** - Interactive audio processing with Plotly visualization
- **🤖 AI Signal Processing** - Machine learning models for automated analysis
- **🔌 Multi-Station Support** - Monitor multiple remote VLF stations simultaneously
- **⚡ High Performance** - Connection pooling, caching, and optimized data transfer
- **🔒 Secure Access** - SSH key-based authentication and VPN networking

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

**For macOS/Linux:**
```bash
git clone https://github.com/Alessiasox/Cassandra-backend.git
cd Cassandra-backend
chmod +x setup.sh
./setup.sh
```

**For Windows:**
```powershell
git clone https://github.com/Alessiasox/Cassandra-backend.git
cd Cassandra-backend
# Run PowerShell as Administrator
.\setup.ps1
```

### Option 2: Manual Setup

#### Prerequisites
- **Docker & Docker Compose** ([Install Docker](https://docs.docker.com/get-docker/))
- **Tailscale** ([Install Tailscale](https://tailscale.com/download/))
- **SSH Keys** for station access

#### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Alessiasox/Cassandra-backend.git
   cd Cassandra-backend
   ```

2. **Generate SSH keys:**
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

3. **Setup Tailscale:**
   ```bash
   # Install and connect to your Tailscale network
   tailscale up
   ```

4. **Configure stations:**
   ```bash
   cp ssh/stations.yaml.example ssh/stations.yaml
   # Edit ssh/stations.yaml with your station details
   ```

5. **Copy SSH keys:**
   ```bash
   cp ~/.ssh/id_ed25519 ssh/
   cp ~/.ssh/id_ed25519.pub ssh/
   ```

6. **Start the application:**
   ```bash
   docker-compose up -d
   ```

7. **Access the dashboard:**
   - 🌐 **Main UI:** http://localhost:8501
   - 📊 **API:** http://localhost:8000
   - 📁 **Files:** http://localhost:8080

## 📦 Alternative Distribution Options

### Option A: Standalone Executable (Future)
We're considering creating standalone executables using:
- **PyInstaller** for Python components
- **Electron** for cross-platform desktop app
- **Docker bundling** for complete isolation

### Option B: Cloud Deployment
Deploy to cloud platforms with one-click installation:
- **AWS/Azure/GCP** with Terraform templates
- **DigitalOcean App Platform**
- **Railway/Render** for simplified hosting

### Option C: Package Managers
Future distribution through:
- **Homebrew** (macOS/Linux): `brew install vlf-monitoring`
- **Chocolatey** (Windows): `choco install vlf-monitoring`
- **Snap** (Linux): `snap install vlf-monitoring`

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   FastAPI       │    │   Nginx Proxy   │
│   (Port 8501)   │◄──►│   Backend       │◄──►│   (Port 8080)    │
│                 │    │   (Port 8000)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                          ┌─────────────┐
                          │   SSHFS     │
                          │   Mounts    │
                          └─────────────┘
                                 │
                      ┌─────────────────────┐
                      │    Tailscale VPN    │
                      └─────────────────────┘
                                 │
         ┌─────────────┬─────────────┬─────────────┐
         │             │             │             │
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │Station 1│   │Station 2│   │Station 3│   │Station N│
    │(Windows)│   │(Windows)│   │(Windows)│   │(Windows)│
    └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

## 🔧 Configuration

### Station Configuration (`ssh/stations.yaml`)
```yaml
CampiFlegrei:
  host: 100.64.12.34        # Tailscale IP
  port: 22
  username: stationuser
  remote_base: C:/htdocs/VLF

MonteUrbino:
  host: 100.97.240.60
  port: 22
  username: Adriano
  remote_base: C:/htdocs/VLF
```

### Environment Variables (`.env`)
```bash
SSH_PRIVATE_KEY_PATH=/app/ssh/id_ed25519
FILE_SERVER_URL=http://localhost:8080
COMPOSE_PROJECT_NAME=vlf-network
```

## 🖥️ Setting Up VLF Stations

Each Windows PC running VLF data collection needs:

### 1. Enable SSH Server
```powershell
# Install OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

### 2. Configure SSH Keys
```powershell
# Create SSH directory
mkdir $env:USERPROFILE\.ssh

# Add your public key to authorized_keys
# Copy the content of your id_ed25519.pub to:
# C:\Users\[username]\.ssh\authorized_keys
```

### 3. Install Tailscale
1. Download from [tailscale.com/download/windows](https://tailscale.com/download/windows)
2. Install and run `tailscale up`
3. Note the assigned `100.x.x.x` IP address

### 4. Verify Data Structure
Ensure your VLF data follows this structure:
```
C:/htdocs/VLF/
├── LoRes/
│   ├── G8_LoResT_250731UTC1200.jpg
│   └── ...
├── HiRes/
│   ├── G4_HiResT_250731UTC120000.jpg
│   └── ...
└── Wav/
    ├── G8_Audio_31UTC120000.wav
    └── ...
```

## 🎯 Usage

### Monitoring Multiple Stations
1. **Select Station** - Choose from configured stations in the sidebar
2. **Pick Date** - Select date range for analysis
3. **Time Control** - Use slider or hour picker for precise time selection
4. **View Data** - Switch between Spectrograms, Waveforms, and AI tabs

### Waveform Analysis
- **Audio Playback** - Listen to VLF signals directly in browser
- **Interactive Plots** - Zoom, pan, and analyze waveforms
- **Download** - Export WAV files for offline analysis
- **Time Filtering** - Show only files within selected time ranges

### AI Analysis
- **Model Selection** - Choose from pre-trained signal analysis models
- **Batch Processing** - Analyze multiple files simultaneously
- **Export Results** - Download analysis results as CSV/JSON

## 🔒 Security Considerations

- **SSH Keys:** Store private keys securely, never commit to version control
- **Tailscale:** Use private networks, enable key expiry
- **Firewall:** Restrict access to necessary ports only
- **Updates:** Keep Docker images and dependencies updated

## 🐛 Troubleshooting

### Common Issues

**Container name conflicts:**
```bash
# Quick cleanup
./cleanup.sh

# Or manual cleanup
docker-compose down
docker stop $(docker ps -aq --filter "name=cassandra")
docker rm -f $(docker ps -aq --filter "name=cassandra")
```

**"Connection refused" errors:**
```bash
# Check if all containers are running
docker-compose ps

# Check Tailscale connectivity
tailscale status

# Test SSH connection manually
ssh -i ~/.ssh/id_ed25519 user@100.x.x.x
```

**"No WAV files found":**
- Verify station data structure matches expected format
- Check SSH key permissions on Windows stations
- Ensure Tailscale is connected on all stations

**Performance issues:**
```bash
# Clear caches
curl http://localhost:8000/cache/clear

# Check cache status
curl http://localhost:8000/cache/status

# Restart services
docker-compose restart
```

## 📊 Development

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/Alessiasox/Cassandra-backend.git
cd Cassandra-backend

# Start development environment
docker-compose -f docker-compose.dev.yml up

# Run tests
docker-compose exec app python -m pytest

# Access logs
docker-compose logs -f ui
```

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit a Pull Request

## 📄 License

??

## 🤝 Support

??

## 🌟 Acknowledgments

??

---
