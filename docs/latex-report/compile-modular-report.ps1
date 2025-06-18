#!/usr/bin/env powershell

<#
.SYNOPSIS
    Compile the FLOPY-NET LaTeX report
.DESCRIPTION
    This script compiles the FLOPY-NET technical report using a Docker-based LaTeX environment.
#>

param(
    [switch]$Clean = $false,
    [switch]$Verbose = $false,
    [string]$OutputDir = "output"
)

# Configuration
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$REPORT_DIR = $SCRIPT_DIR
$MAIN_TEX = "FLOPY-NET_Comprehensive_Report.tex"
$OUTPUT_PDF = "FLOPY-NET_Report.pdf"
$DOCKER_IMAGE = "danteev/texlive:latest"

# Colors for output
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorInfo = "Cyan"

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host "==> $Message" -ForegroundColor $Color
}

function Write-Error-Exit {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor $ColorError
    exit 1
}

function Clean-Artifacts {
    if ($Clean) {
        Write-Status "Cleaning previous build artifacts..." $ColorInfo
        
        $cleanup_extensions = @("*.aux", "*.bbl", "*.blg", "*.log", "*.out", "*.toc", "*.lof", "*.lot", "*.fls", "*.fdb_latexmk", "*.synctex.gz")
        
        foreach ($ext in $cleanup_extensions) {
            Get-ChildItem -Path $REPORT_DIR -Filter $ext -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
        }
        
        if (Test-Path "$REPORT_DIR\$OutputDir") {
            Remove-Item -Path "$REPORT_DIR\$OutputDir\*" -Force -Recurse -ErrorAction SilentlyContinue
        }
        
        Write-Status "Cleanup completed" $ColorSuccess
    }
}

function Compile-LaTeX {
    Write-Status "Starting LaTeX compilation..." $ColorInfo
    
    # Check if Docker is available
    docker --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Exit "Docker is not installed or not accessible"
    }
    
    # Pull Docker image if not present
    Write-Status "Checking Docker image..." $ColorInfo
    docker image inspect $DOCKER_IMAGE > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Pulling LaTeX Docker image (this may take a while)..." $ColorWarning
        docker pull $DOCKER_IMAGE
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Exit "Failed to pull Docker image"
        }
    }    # Define Docker run command for pdflatex
    $docker_pdflatex_args = @(
        "run", "--rm",
        "-v", "${REPORT_DIR}:/workspace",
        "-w", "/workspace",
        $DOCKER_IMAGE,
        "pdflatex", "-interaction=nonstopmode", $MAIN_TEX
    )
    
    # Define Docker run command for bibtex
    $docker_bibtex_args = @(
        "run", "--rm",
        "-v", "${REPORT_DIR}:/workspace",
        "-w", "/workspace",
        $DOCKER_IMAGE,
        "bibtex", "FLOPY-NET_Comprehensive_Report"
    )
    
    # Full LaTeX compilation sequence for documents with bibliography
    Write-Status "Running pdflatex (1st pass)..." $ColorInfo
    & docker @docker_pdflatex_args
    
    Write-Status "Running bibtex to process bibliography..." $ColorInfo
    & docker @docker_bibtex_args
    
    Write-Status "Running pdflatex (2nd pass)..." $ColorInfo
    & docker @docker_pdflatex_args
    
    Write-Status "Running pdflatex (3rd pass)..." $ColorInfo
    & docker @docker_pdflatex_args
    
    # Move output to output directory
    if (Test-Path "$REPORT_DIR\FLOPY-NET_Comprehensive_Report.pdf") {
        if (-not (Test-Path "$REPORT_DIR\$OutputDir")) {
            New-Item -Path "$REPORT_DIR\$OutputDir" -ItemType Directory -Force | Out-Null
        }
        Copy-Item -Path "$REPORT_DIR\FLOPY-NET_Comprehensive_Report.pdf" -Destination "$REPORT_DIR\$OutputDir\$OUTPUT_PDF" -Force
        Write-Status "PDF output copied to: $OutputDir\$OUTPUT_PDF" $ColorSuccess
    } else {
        Write-Error-Exit "PDF compilation failed - output file not found. Check the .log file for errors."
    }
}

function Main {
    Clean-Artifacts
    Compile-LaTeX
    Write-Status "Report compilation finished." $ColorSuccess
}

Main
