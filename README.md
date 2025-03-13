# Federated Learning with SDN Integration

This project implements a federated learning system with software-defined networking (SDN) integration. It includes a policy engine for managing network policies, a federated learning server, an SDN controller, and a dashboard for monitoring and visualization.

## Architecture

The system consists of the following components:

1. **Policy Engine**: A FastAPI application that manages policies for the FL system and SDN integration.
2. **FL Server**: A federated learning server that coordinates training across multiple clients.
3. **SDN Controller**: An ONOS controller for managing the network.
4. **Dashboard**: A Dash web application with a REST API for monitoring and visualization.

## Git Setup

The project is configured for Git version control. To set up the repository:

### On Linux/macOS:
```bash
# Initialize the Git repository with our configuration
./init-git.sh
```

### On Windows:
```powershell
# Initialize the Git repository with our configuration
.\init-git.ps1
```

This will:
- Initialize a Git repository
- Configure proper line ending handling
- Set up Git LFS (if installed)
- Create a development branch
- Make an initial commit with configuration files

For more information on contributing to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Docker Setup

The project is containerized using Docker and Docker Compose. Each component runs in its own container, and they communicate with each other over a Docker network.

### Prerequisites

- Docker
- Docker Compose

### Running the System

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/federated-learning.git
   cd federated-learning
   ```

2. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

3. Access the services:
   - Dashboard Web UI: http://localhost:8050/
   - Dashboard API: http://localhost:8051/
   - Policy Engine API: http://localhost:8000/
   - FL Server API: http://localhost:8088/
   - ONOS Web UI: http://localhost:8181/onos/ui/

4. Stop the containers:
   ```bash
   docker-compose down
   ```

### Helper Scripts

The repository includes helper scripts for running the Docker setup:

- `docker-run.sh` (Linux/macOS): Builds and starts the containers, then checks if the services are running.
- `docker-run.ps1` (Windows): PowerShell script that does the same as the shell script.

## Development Environment

For development, you can set up a Python virtual environment:

```bash
# Create a virtual environment
python -m venv flsdn

# Activate the virtual environment (Linux/macOS)
source flsdn/bin/activate

# Activate the virtual environment (Windows)
.\flsdn\Scripts\activate

# Install dependencies
pip install -r requirements-docker.txt
```

## Project Structure

- `fl/`: Federated learning server code
- `policy_engine/`: Policy engine code
- `dashboard/`: Dashboard web application and API
- `docker/`: Dockerfiles for each component
- `docker-compose.yml`: Docker Compose configuration

## License

This project is licensed under the MIT License - see the LICENSE file for details.
