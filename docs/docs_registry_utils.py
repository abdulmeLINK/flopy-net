#!/usr/bin/env python3
"""
Docu# Default configuration
DEFAULT_CONFIG = {
    "registry": "abdulmelink",
    "version": "v1.0.0-alpha.8",
    "build_date": datetime.now().strftime("%Y-%m-%d"),
    "component_images": {ion Docker Registry Utility Script

This script provides functionality for building Docker images for Docusaurus documentation,
tagging them with appropriate names and versions, and pushing them to a registry.
Designed specifically for FLOPY-NET documentation components.

Usage:
    python docs_registry_utils.py build
    python docs_registry_utils.py push --registry abdulmelink
    python docs_registry_utils.py all --registry abdulmelink

Author: flopynet Team
"""

import os
import sys
import argparse
import subprocess
import logging
import json
import time
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docs_registry_utils")

# Default configuration
DEFAULT_CONFIG = {
    "registry": "abdulmelink",
    "version": "v1.0.0-alpha.8",
    "build_date": datetime.now().strftime("%Y-%m-%d"),
    "component_images": {
        "docs": {
            "image": "flopynet-docs",
            "dockerfile": "Dockerfile",
            "context": ".",
            "specialized_tags": {
                "latest": "Latest stable documentation build",
                "dev": "Development documentation with latest features",
                "stable": "Stable release documentation",
                "archive": "Archived documentation for reference",
                "mobile": "Mobile-optimized documentation build",
                "offline": "Offline-capable documentation build",
                "api": "API documentation focus",
                "tutorial": "Tutorial and getting started focus"
            }
        }
    }
}

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a file or use default configuration.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG
    
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                # Merge file config with default config
                config.update(file_config)
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    return config

def load_package_json_version() -> str:
    """
    Load version from package.json if available.
    
    Returns:
        Version string from package.json or default version
    """
    package_json_path = "package.json"
    if os.path.exists(package_json_path):
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                version = package_data.get('version', DEFAULT_CONFIG['version'])
                logger.info(f"Loaded version from package.json: {version}")
                return f"v{version}" if not version.startswith('v') else version
        except Exception as e:
            logger.warning(f"Error loading version from package.json: {e}")
    
    return DEFAULT_CONFIG['version']

def run_command(command: str, hide_output: bool = False, ignore_error: bool = False) -> Tuple[bool, str]:
    """
    Run a shell command and return the result.
    
    Args:
        command: The command to run
        hide_output: Whether to hide command output from logs
        ignore_error: Whether to ignore command errors
        
    Returns:
        Tuple of (success, output)
    """
    logger.info(f"Running command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=not ignore_error
        )
        
        if result.returncode == 0:
            if not hide_output and result.stdout:
                logger.info(f"Command output: {result.stdout.strip()}")
            return True, result.stdout.strip()
        else:
            logger.error(f"Command failed: {result.stderr.strip()}")
            return False, result.stderr.strip()
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False, str(e)

def build_docker_image(component: str, config: Dict[str, Any]) -> bool:
    """
    Build a Docker image for a component.
    
    Args:
        component: Component name (docs)
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    component_config = config["component_images"].get(component)
    if not component_config:
        logger.error(f"No configuration found for component: {component}")
        return False
    
    image_name = component_config["image"]
    dockerfile = component_config["dockerfile"]
    context = component_config.get("context", ".")
    version = config.get("version", "latest")
    build_date = config.get("build_date", datetime.now().strftime("%Y-%m-%d"))
    
    # Get git commit hash if available
    git_commit = "latest"
    git_success, git_output = run_command("git rev-parse --short HEAD", ignore_error=True)
    if git_success:
        git_commit = git_output.strip()
    
    # Check if Dockerfile exists
    if not os.path.exists(dockerfile):
        logger.error(f"Dockerfile not found: {dockerfile}")
        return False
    
    # Build the image with both latest and version tags
    build_cmd = (
        f'docker build '
        f'-t {image_name}:latest '
        f'-t {image_name}:{version} '
        f'--build-arg DOCUSAURUS_VERSION={version} '
        f'--build-arg BUILD_DATE={build_date} '
        f'--build-arg GIT_COMMIT={git_commit} '
        f'--build-arg NODE_ENV=production '
        f'-f {dockerfile} {context}'
    )
    
    logger.info(f"Building Docker image for {component}: {build_cmd}")
    
    success, output = run_command(build_cmd)
    if success:
        logger.info(f"Successfully built Docker image: {image_name}:latest and {image_name}:{version}")
        return True
    else:
        logger.error(f"Failed to build Docker image for {component}: {output}")
        return False

def tag_and_push_image(component: str, config: Dict[str, Any]) -> bool:
    """
    Tag and push a Docker image to the registry.
    
    Args:
        component: Component name (docs)
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    component_config = config["component_images"].get(component)
    if not component_config:
        logger.error(f"No configuration found for component: {component}")
        return False
    
    registry = config.get("registry", "abdulmelink")
    image_name = component_config["image"]
    version = config.get("version", "latest")
    local_tag = f"{image_name}:latest"
    remote_tag = f"{registry}/{image_name}:latest"
    remote_version_tag = f"{registry}/{image_name}:{version}"
    
    # Tag the base image (latest)
    tag_cmd = f"docker tag {local_tag} {remote_tag}"
    logger.info(f"Tagging image: {tag_cmd}")
    
    success, output = run_command(tag_cmd)
    if not success:
        logger.error(f"Failed to tag image {local_tag}: {output}")
        return False
    
    # Tag the versioned image
    version_tag_cmd = f"docker tag {local_tag} {remote_version_tag}"
    logger.info(f"Tagging versioned image: {version_tag_cmd}")
    
    success, output = run_command(version_tag_cmd)
    if not success:
        logger.error(f"Failed to tag versioned image {local_tag}: {output}")
        return False
    
    # Push the base image (latest)
    push_cmd = f"docker push {remote_tag}"
    logger.info(f"Pushing image: {push_cmd}")
    
    success, output = run_command(push_cmd)
    if not success:
        logger.error(f"Failed to push image {remote_tag}: {output}")
        return False
    
    logger.info(f"Successfully pushed {remote_tag}")
    
    # Push the versioned image
    version_push_cmd = f"docker push {remote_version_tag}"
    logger.info(f"Pushing versioned image: {version_push_cmd}")
    
    success, output = run_command(version_push_cmd)
    if not success:
        logger.error(f"Failed to push versioned image {remote_version_tag}: {output}")
        return False
    
    logger.info(f"Successfully pushed {remote_version_tag}")
    
    # Tag and push specialized versions
    specialized_tags = component_config.get("specialized_tags", {})
    for tag, description in specialized_tags.items():
        if tag == "latest":  # Skip latest as it's already handled
            continue
            
        specialized_tag = f"{registry}/{image_name}:{tag}"
        
        # Tag specialized version
        spec_tag_cmd = f"docker tag {local_tag} {specialized_tag}"
        logger.info(f"Tagging specialized image: {spec_tag_cmd}")
        
        success, output = run_command(spec_tag_cmd)
        if not success:
            logger.warning(f"Failed to tag specialized image {specialized_tag}: {output}")
            continue
        
        # Push specialized version
        spec_push_cmd = f"docker push {specialized_tag}"
        logger.info(f"Pushing specialized image: {spec_push_cmd}")
        
        success, output = run_command(spec_push_cmd)
        if not success:
            logger.warning(f"Failed to push specialized image {specialized_tag}: {output}")
        else:
            logger.info(f"Successfully pushed specialized image {specialized_tag}")
    
    return True

def check_remote_tags(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Check which tags already exist in the remote registry.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping image names to lists of existing tags
    """
    registry = config.get("registry", "abdulmelink")
    result = {}
    
    for component, component_config in config["component_images"].items():
        image_name = component_config["image"]
        remote_image = f"{registry}/{image_name}"
        
        # Use docker registry API to list tags (simplified with docker CLI)
        cmd = f"docker image ls {remote_image} --format '{{{{.Tag}}}}'"
        success, output = run_command(cmd, ignore_error=True)
        
        if success and output:
            tags = [tag for tag in output.strip().split('\n') if tag and tag != '<none>']
            result[remote_image] = tags
            logger.info(f"Found existing tags for {remote_image}: {', '.join(tags)}")
        else:
            result[remote_image] = []
            logger.info(f"No existing tags found for {remote_image}")
    
    return result

def login_to_registry(config: Dict[str, Any]) -> bool:
    """
    Log in to the Docker registry.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    registry = config.get("registry", "abdulmelink")
    username = config.get("registry_username")
    password = config.get("registry_password")
    
    if not username or not password:
        logger.warning("Registry username or password not provided, skipping login")
        return False
    
    login_cmd = f"docker login -u {username} -p {password}"
    logger.info(f"Logging into Docker Hub registry")
    
    # Hide actual command with password from logs
    success, output = run_command(login_cmd, hide_output=True)
    if success:
        logger.info(f"Successfully logged into Docker Hub registry")
        return True
    else:
        logger.error(f"Failed to login to registry: {output}")
        return False

def clean_build_artifacts() -> bool:
    """
    Clean build artifacts and temporary files.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Cleaning build artifacts...")
    
    # Remove Docusaurus build directory
    build_cmd = "npm run clear"
    success, output = run_command(build_cmd, ignore_error=True)
    if success:
        logger.info("Successfully cleared Docusaurus cache and build artifacts")
    else:
        logger.warning(f"Failed to clear Docusaurus artifacts: {output}")
    
    # Remove any dangling Docker images
    prune_cmd = "docker image prune -f"
    success, output = run_command(prune_cmd, ignore_error=True)
    if success:
        logger.info("Successfully pruned dangling Docker images")
    else:
        logger.warning(f"Failed to prune Docker images: {output}")
    
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Documentation Docker Registry Utility Script")
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build Docker images for documentation")
    build_parser.add_argument("--config", type=str, help="Path to configuration file")
    build_parser.add_argument("--clean", action="store_true", help="Clean build artifacts before building")
      # Push command
    push_parser = subparsers.add_parser("push", help="Push Docker images to registry")
    push_parser.add_argument("--registry", type=str, default="abdulmelink", 
                           help="Docker registry to push to")
    push_parser.add_argument("--username", type=str, help="Registry username")
    push_parser.add_argument("--password", type=str, help="Registry password")
    push_parser.add_argument("--config", type=str, help="Path to configuration file")
    
    # All command (build and push)
    all_parser = subparsers.add_parser("all", help="Build and push Docker images")
    all_parser.add_argument("--registry", type=str, default="abdulmelink", 
                          help="Docker registry to push to")
    all_parser.add_argument("--username", type=str, help="Registry username")
    all_parser.add_argument("--password", type=str, help="Registry password")
    all_parser.add_argument("--config", type=str, help="Path to configuration file")
    all_parser.add_argument("--clean", action="store_true", help="Clean build artifacts before building")
    
    # List command to show available components and existing registry tags
    list_parser = subparsers.add_parser("list", help="List components and registry tags")
    list_parser.add_argument("--registry", type=str, default="abdulmelink", 
                           help="Docker registry to check")
    list_parser.add_argument("--config", type=str, help="Path to configuration file")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean build artifacts")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config if hasattr(args, "config") else None)
    
    # Load version from package.json
    config["version"] = load_package_json_version()
    
    # Override config with command-line arguments
    if hasattr(args, "registry") and args.registry:
        config["registry"] = args.registry
    if hasattr(args, "username") and args.username:
        config["registry_username"] = args.username
    if hasattr(args, "password") and args.password:
        config["registry_password"] = args.password
    
    # List components and exit if list command
    if args.command == "list":
        logger.info(f"Available components:")
        for component, component_config in config["component_images"].items():
            logger.info(f"  - {component}: {component_config['image']} ({component_config['dockerfile']})")
        
        logger.info(f"Checking registry {config['registry']} for existing tags...")
        check_remote_tags(config)
        sys.exit(0)
    
    # Clean command
    if args.command == "clean":
        clean_build_artifacts()
        sys.exit(0)
    
    # Clean before building if requested
    if hasattr(args, "clean") and args.clean:
        clean_build_artifacts()
    
    component = "docs"  # We only have one component for docs
    
    # Process commands
    if args.command == "build" or args.command == "all":
        # Build Docker images
        logger.info("Building Docker image for documentation...")
        success = build_docker_image(component, config)
        
        if success:
            logger.info("Built documentation Docker image successfully")
        else:
            logger.error("Failed to build documentation Docker image")
            sys.exit(1)
    
    if args.command == "push" or args.command == "all":
        # Log in to registry
        login_to_registry(config)
        
        # Push Docker images
        logger.info("Pushing Docker image to registry...")
        success = tag_and_push_image(component, config)
        
        if success:
            logger.info("Pushed documentation Docker image successfully")
        else:
            logger.error("Failed to push documentation Docker image")
            sys.exit(1)
    
    if not args.command:
        logger.error("No command specified. Use 'build', 'push', 'all', 'list', or 'clean'.")
        parser.print_help()
        sys.exit(1)
    
    logger.info("Done!")

if __name__ == "__main__":
    main()
