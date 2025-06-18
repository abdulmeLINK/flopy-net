# FLOPY-NET Documentation Docker Build

This directory contains Docker configuration and build scripts for the FLOPY-NET documentation.

## Files

- `Dockerfile` - Multi-stage Docker build for Docusaurus documentation
- `docker-compose.yml` - Docker Compose configuration for running the documentation
- `nginx.conf` - Nginx configuration for serving the documentation
- `docs_registry_utils.py` - Python script for building and pushing Docker images
- `build-docs.ps1` - PowerShell wrapper script for easy usage
- `.dockerignore` - Docker ignore file to optimize build context

## Quick Start

### Prerequisites

- Docker
- Python 3.7+
- Node.js 18+
- npm

### Build and Run Locally

1. **Build the Docker image:**
   ```bash
   python docs_registry_utils.py build
   ```
   
   Or using PowerShell:
   ```powershell
   .\build-docs.ps1 -Action build
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up
   ```

3. **Access the documentation:**
   Open http://localhost:3000 in your browser

### Push to Registry

1. **Build and push to registry:**
   ```bash
   python docs_registry_utils.py all --registry abdulmelink --username YOUR_USERNAME --password YOUR_PASSWORD
   ```
   
   Or using PowerShell:
   ```powershell
   .\build-docs.ps1 -Action all -Registry abdulmelink -Username YOUR_USERNAME -Password YOUR_PASSWORD
   ```

## Available Commands

### Python Script (`docs_registry_utils.py`)

- `build` - Build Docker image
- `push` - Push Docker image to registry
- `all` - Build and push Docker image
- `list` - List available components and registry tags
- `clean` - Clean build artifacts

### PowerShell Script (`build-docs.ps1`)

- `-Action build` - Build Docker image
- `-Action push` - Push Docker image to registry
- `-Action all` - Build and push Docker image
- `-Action list` - List available components and registry tags
- `-Action clean` - Clean build artifacts
- `-Clean` - Clean build artifacts before building
- `-Registry` - Specify registry (default: abdulmelink)
- `-Username` - Registry username
- `-Password` - Registry password

## Image Tags

The following tags are created:

- `abdulmelink/flopynet-docs:latest` - Latest build
- `abdulmelink/flopynet-docs:v1.0.0-alpha.8` - Version-specific tag
- `abdulmelink/flopynet-docs:dev` - Development build
- `abdulmelink/flopynet-docs:stable` - Stable release
- `abdulmelink/flopynet-docs:archive` - Archived version
- `abdulmelink/flopynet-docs:mobile` - Mobile-optimized
- `abdulmelink/flopynet-docs:offline` - Offline-capable
- `abdulmelink/flopynet-docs:api` - API documentation focus
- `abdulmelink/flopynet-docs:tutorial` - Tutorial focus

## Docker Compose

The documentation service runs on port 3000 and includes:

- Health checks
- Nginx reverse proxy
- Gzip compression
- Security headers
- Static asset caching

## Development

For development, you can mount volumes for hot reloading:

```yaml
volumes:
  - ./docs:/app/docs
  - ./src:/app/src
  - ./docusaurus.config.js:/app/docusaurus.config.js
```

## Troubleshooting

1. **Build fails with permission errors:**
   - Ensure Docker daemon is running
   - Check file permissions

2. **Push fails with authentication errors:**
   - Verify registry credentials
   - Login to Docker Hub: `docker login`

3. **Documentation not loading:**
   - Check if port 3000 is available
   - Verify health check status: `docker-compose ps`

## Architecture

The Docker image uses a multi-stage build:

1. **Builder stage:** Uses Node.js Alpine to build the Docusaurus site
2. **Runtime stage:** Uses Nginx Alpine to serve the static files

This approach minimizes the final image size while maintaining all necessary dependencies for the build process.
