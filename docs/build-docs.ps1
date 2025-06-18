#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build and Push FLOPY-NET Documentation Docker Images
    
.DESCRIPTION
    This script provides a convenient wrapper around the docs_registry_utils.py script
    for building and pushing FLOPY-NET documentation Docker images to the registry.
    
.PARAMETER Action
    The action to perform: build, push, all, list, or clean
    
.PARAMETER Registry
    The Docker registry to use (default: abdulmelik)
    
.PARAMETER Username
    The registry username for authentication
    
.PARAMETER Password
    The registry password for authentication
    
.PARAMETER Clean
    Clean build artifacts before building

.EXAMPLE
    .\build-docs.ps1 -Action build
    
.EXAMPLE
    .\build-docs.ps1 -Action push -Registry abdulmelik -Username myuser -Password mypass
    
.EXAMPLE
    .\build-docs.ps1 -Action all -Registry abdulmelik -Clean
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("build", "push", "all", "list", "clean")]
    [string]$Action,
    
    [string]$Registry = "abdulmelink",
    [string]$Username,
    [string]$Password,
    [switch]$Clean
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$ColorGreen = "Green"
$ColorYellow = "Yellow"
$ColorRed = "Red"
$ColorCyan = "Cyan"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-PythonAvailable {
    try {
        $pythonVersion = python --version 2>&1
        Write-ColorOutput "Found Python: $pythonVersion" $ColorGreen
        return $true
    } catch {
        Write-ColorOutput "Python is not available. Please install Python 3.7 or later." $ColorRed
        return $false
    }
}

function Test-DockerAvailable {
    try {
        $dockerVersion = docker --version 2>&1
        Write-ColorOutput "Found Docker: $dockerVersion" $ColorGreen
        return $true
    } catch {
        Write-ColorOutput "Docker is not available. Please install Docker." $ColorRed
        return $false
    }
}

function Test-NodeAvailable {
    try {
        $nodeVersion = node --version 2>&1
        Write-ColorOutput "Found Node.js: $nodeVersion" $ColorGreen
        return $true
    } catch {
        Write-ColorOutput "Node.js is not available. Please install Node.js 18 or later." $ColorRed
        return $false
    }
}

# Main script
Write-ColorOutput "=== FLOPY-NET Documentation Build Script ===" $ColorCyan
Write-ColorOutput "Action: $Action" $ColorYellow
Write-ColorOutput "Registry: $Registry" $ColorYellow

# Check prerequisites
Write-ColorOutput "`nChecking prerequisites..." $ColorCyan

if (-not (Test-PythonAvailable)) {
    exit 1
}

if (-not (Test-DockerAvailable)) {
    exit 1
}

if (-not (Test-NodeAvailable)) {
    exit 1
}

# Check if docs_registry_utils.py exists
$scriptPath = "docs_registry_utils.py"
if (-not (Test-Path $scriptPath)) {
    Write-ColorOutput "Error: $scriptPath not found in current directory." $ColorRed
    exit 1
}

# Build the command
$command = "python $scriptPath $Action"

if ($Registry) {
    $command += " --registry $Registry"
}

if ($Username) {
    $command += " --username $Username"
}

if ($Password) {
    $command += " --password $Password"
}

if ($Clean) {
    $command += " --clean"
}

Write-ColorOutput "`nExecuting: $command" $ColorCyan

# Execute the command
try {
    Invoke-Expression $command
    Write-ColorOutput "`n=== Build completed successfully! ===" $ColorGreen
} catch {
    Write-ColorOutput "`n=== Build failed! ===" $ColorRed
    Write-ColorOutput "Error: $_" $ColorRed
    exit 1
}

# Show next steps based on action
switch ($Action) {
    "build" {
        Write-ColorOutput "`nNext steps:" $ColorYellow
        Write-ColorOutput "  1. Test the image locally: docker run -p 3000:80 flopynet-docs:latest" $ColorYellow
        Write-ColorOutput "  2. Push to registry: .\build-docs.ps1 -Action push -Registry $Registry" $ColorYellow
    }
    "push" {
        Write-ColorOutput "`nImage pushed successfully!" $ColorGreen
        Write-ColorOutput "You can now pull the image with: docker pull $Registry/flopynet-docs:latest" $ColorYellow
    }
    "all" {
        Write-ColorOutput "`nBuild and push completed successfully!" $ColorGreen
        Write-ColorOutput "You can now pull the image with: docker pull $Registry/flopynet-docs:latest" $ColorYellow
    }
    "list" {
        Write-ColorOutput "`nListing completed." $ColorGreen
    }
    "clean" {
        Write-ColorOutput "`nClean completed." $ColorGreen
    }
}
