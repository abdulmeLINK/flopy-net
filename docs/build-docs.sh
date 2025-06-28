#!/bin/bash
#
# Build and Push FLOPY-NET Documentation Docker Images
#
# This script provides a convenient wrapper around the docs_registry_utils.py script
# for building and pushing FLOPY-NET documentation Docker images to the registry.
#
# Usage:
#   ./build-docs.sh build
#   ./build-docs.sh push abdulmelink myuser mypass
#   ./build-docs.sh all abdulmelink myuser mypass --clean
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

function check_prerequisites() {
    print_color $CYAN "Checking prerequisites..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_color $GREEN "Found Python: $PYTHON_VERSION"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version)
        print_color $GREEN "Found Python: $PYTHON_VERSION"
        PYTHON_CMD="python"
    else
        print_color $RED "Python is not available. Please install Python 3.7 or later."
        exit 1
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_color $GREEN "Found Docker: $DOCKER_VERSION"
    else
        print_color $RED "Docker is not available. Please install Docker."
        exit 1
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_color $GREEN "Found Node.js: $NODE_VERSION"
    else
        print_color $RED "Node.js is not available. Please install Node.js 18 or later."
        exit 1
    fi
}

function show_usage() {
    echo "Usage: $0 <action> [registry] [username] [password] [--clean]"
    echo ""
    echo "Actions:"
    echo "  build             Build Docker image"
    echo "  push              Push Docker image to registry"
    echo "  all               Build and push Docker image"
    echo "  list              List available components and registry tags"
    echo "  clean             Clean build artifacts"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 push abdulmelink myuser mypass"
    echo "  $0 all abdulmelink myuser mypass --clean"
    echo "  $0 list"
    echo "  $0 clean"
}

# Main script
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

ACTION=$1
REGISTRY=${2:-"abdulmelink"}
USERNAME=$3
PASSWORD=$4
CLEAN_FLAG=""

# Check for --clean flag
for arg in "$@"; do
    if [ "$arg" = "--clean" ]; then
        CLEAN_FLAG="--clean"
        break
    fi
done

print_color $CYAN "=== FLOPY-NET Documentation Build Script ==="
print_color $YELLOW "Action: $ACTION"
print_color $YELLOW "Registry: $REGISTRY"

check_prerequisites

# Check if docs_registry_utils.py exists
if [ ! -f "docs_registry_utils.py" ]; then
    print_color $RED "Error: docs_registry_utils.py not found in current directory."
    exit 1
fi

# Build the command
CMD="$PYTHON_CMD docs_registry_utils.py $ACTION"

if [ "$ACTION" != "build" ] && [ "$ACTION" != "clean" ] && [ "$ACTION" != "list" ]; then
    CMD="$CMD --registry $REGISTRY"
fi

if [ -n "$USERNAME" ]; then
    CMD="$CMD --username $USERNAME"
fi

if [ -n "$PASSWORD" ]; then
    CMD="$CMD --password $PASSWORD"
fi

if [ -n "$CLEAN_FLAG" ]; then
    CMD="$CMD $CLEAN_FLAG"
fi

print_color $CYAN "\nExecuting: $CMD"

# Execute the command
if eval $CMD; then
    print_color $GREEN "\n=== Build completed successfully! ==="
    
    # Show next steps based on action
    case $ACTION in
        "build")
            print_color $YELLOW "\nNext steps:"
            print_color $YELLOW "  1. Test the image locally: docker run -p 3000:80 flopynet-docs:latest"
            print_color $YELLOW "  2. Push to registry: ./build-docs.sh push $REGISTRY"
            ;;
        "push")
            print_color $GREEN "\nImage pushed successfully!"
            print_color $YELLOW "You can now pull the image with: docker pull $REGISTRY/flopynet-docs:latest"
            ;;
        "all")
            print_color $GREEN "\nBuild and push completed successfully!"
            print_color $YELLOW "You can now pull the image with: docker pull $REGISTRY/flopynet-docs:latest"
            ;;
        "list")
            print_color $GREEN "\nListing completed."
            ;;
        "clean")
            print_color $GREEN "\nClean completed."
            ;;
    esac
else
    print_color $RED "\n=== Build failed! ==="
    exit 1
fi
