#!/usr/bin/env powershell

<#
.SYNOPSIS
    Compile the FLOPY-NET LaTeX report using local LaTeX installation
.DESCRIPTION
    This script compiles the FLOPY-NET technical report using a local LaTeX installation (MiKTeX or TeX Live).
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

function Test-LaTeXInstallation {
    Write-Status "Checking for LaTeX installation..." $ColorInfo
    
    # Check for pdflatex
    try {
        $null = Get-Command pdflatex -ErrorAction Stop
        Write-Status "Found pdflatex" $ColorSuccess
    } catch {
        Write-Error-Exit "pdflatex not found. Please install MiKTeX or TeX Live."
    }
    
    # Check for bibtex
    try {
        $null = Get-Command bibtex -ErrorAction Stop
        Write-Status "Found bibtex" $ColorSuccess
    } catch {
        Write-Error-Exit "bibtex not found. Please install MiKTeX or TeX Live."
    }
}

function Compile-LaTeX {
    Write-Status "Starting LaTeX compilation..." $ColorInfo
    
    Test-LaTeXInstallation
    
    # Change to report directory
    Push-Location $REPORT_DIR
    
    try {
        # Full LaTeX compilation sequence for documents with bibliography
        Write-Status "Running pdflatex (1st pass)..." $ColorInfo
        & pdflatex -interaction=nonstopmode $MAIN_TEX
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "pdflatex first pass completed with warnings. Check the .log file."
        }
        
        Write-Status "Running bibtex to process bibliography..." $ColorInfo
        & bibtex "FLOPY-NET_Comprehensive_Report"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "bibtex completed with warnings. Check the .blg file."
        }
        
        Write-Status "Running pdflatex (2nd pass)..." $ColorInfo
        & pdflatex -interaction=nonstopmode $MAIN_TEX
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "pdflatex second pass completed with warnings. Check the .log file."
        }
        
        Write-Status "Running pdflatex (3rd pass)..." $ColorInfo
        & pdflatex -interaction=nonstopmode $MAIN_TEX
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "pdflatex third pass completed with warnings. Check the .log file."
        }
        
        # Move output to output directory
        if (Test-Path "FLOPY-NET_Comprehensive_Report.pdf") {
            if (-not (Test-Path $OutputDir)) {
                New-Item -Path $OutputDir -ItemType Directory -Force | Out-Null
            }
            Copy-Item -Path "FLOPY-NET_Comprehensive_Report.pdf" -Destination "$OutputDir\$OUTPUT_PDF" -Force
            Write-Status "PDF output copied to: $OutputDir\$OUTPUT_PDF" $ColorSuccess
        } else {
            Write-Error-Exit "PDF compilation failed - output file not found. Check the .log file for errors."
        }
    }
    finally {
        Pop-Location
    }
}

function Main {
    Clean-Artifacts
    Compile-LaTeX
    Write-Status "Report compilation finished." $ColorSuccess
}

Main
