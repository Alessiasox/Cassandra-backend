# Cassandra Backend

A FastAPI-based backend system for the INGV Cassandra Project, providing on-demand access to VLF spectrogram data from remote stations.

## Overview

This system provides:
- **On-demand frame listing**: Fetch spectrogram frames for specific dates via SSH
- **File serving**: Serve downloaded spectrograms through an Nginx proxy
- **Web UI**: Streamlit-based interface for browsing and visualizing data
- **Performance monitoring**: Comprehensive test suite with performance metrics

## Architecture

- **Backend**: FastAPI application that SSHes into remote Windows machines to list files
- **Proxy**: Nginx container with SSHFS mount to serve remote files
- **UI**: Streamlit web interface for data visualization
- **Tests**: Automated test suite with performance reporting

## Quick Start

1. **Setup environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your SSH credentials and remote paths
   ```

2. **Start the system**:
   ```bash
   make start
   ```

3. **Run tests**:
   ```bash
   make test
   ```

4. **View performance metrics**:
   ```bash
   cd tests && python3 show_performance.py
   ```

## Services

- **FastAPI Backend**: `http://localhost:8000`
- **File Server**: `http://localhost:8080`
- **Web UI**: `http://localhost:8501`

## API Endpoints

- `GET /health` - Health check
- `GET /frames?date=YYMMDD` - List frames for a specific date

## File Structure

```
├── backend/           # FastAPI application
├── proxy/            # Nginx configuration
├── ui/               # Streamlit web interface
├── tests/            # Test suite and performance reporting
├── scripts/          # Utility scripts
└── ssh/              # SSH keys and station configuration
```

## Development

- **Build**: `make build`
- **Start**: `make start`
- **Test**: `make test`
- **Stop**: `make down`

## Performance

The system includes comprehensive performance monitoring:
- API response times
- File download speeds
- Proxy readiness checks
- Automated performance reports

Test results and downloaded images are automatically copied to the local `tests/` directory.