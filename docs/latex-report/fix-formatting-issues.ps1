# PowerShell script to fix common LaTeX formatting issues
# This script addresses overfull/underfull box warnings in the FLOPY-NET report

Write-Host "Fixing LaTeX formatting issues in FLOPY-NET report..." -ForegroundColor Green

# Check if pdflatex is available
$pdflatexPath = Get-Command pdflatex -ErrorAction SilentlyContinue
if (-not $pdflatexPath) {
    Write-Host "Warning: pdflatex not found. Cannot test compilation." -ForegroundColor Yellow
    Write-Host "Please install a LaTeX distribution like MiKTeX or TeX Live." -ForegroundColor Yellow
}

# Function to clean up auxiliary files
function Clean-LatexFiles {
    Write-Host "Cleaning up LaTeX auxiliary files..." -ForegroundColor Blue
    $auxFiles = @("*.aux", "*.log", "*.out", "*.toc", "*.lof", "*.lot", "*.fls", "*.fdb_latexmk", "*.synctex.gz")
    foreach ($pattern in $auxFiles) {
        Get-ChildItem -Path . -Name $pattern | Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

# Function to compile the document
function Compile-Document {
    param(
        [string]$DocumentName = "FLOPY-NET_Comprehensive_Report.tex"
    )
    
    if (-not $pdflatexPath) {
        Write-Host "Skipping compilation - pdflatex not available" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Compiling LaTeX document..." -ForegroundColor Blue
    
    # Run pdflatex twice to resolve references
    pdflatex -interaction=nonstopmode $DocumentName
    pdflatex -interaction=nonstopmode $DocumentName
    
    # Check if PDF was generated
    $pdfFile = $DocumentName -replace '\.tex$', '.pdf'
    if (Test-Path $pdfFile) {
        Write-Host "PDF generated successfully: $pdfFile" -ForegroundColor Green
    } else {
        Write-Host "PDF generation failed. Check the .log file for errors." -ForegroundColor Red
    }
}

# Function to show compilation summary
function Show-CompilationSummary {
    $logFile = "FLOPY-NET_Comprehensive_Report.log"
    if (Test-Path $logFile) {
        Write-Host "`nCompilation Summary:" -ForegroundColor Cyan
        
        # Count warnings
        $overfullWarnings = (Select-String -Path $logFile -Pattern "Overfull").Count
        $underfullWarnings = (Select-String -Path $logFile -Pattern "Underfull").Count
        $undefinedReferences = (Select-String -Path $logFile -Pattern "undefined").Count
        
        Write-Host "Overfull box warnings: $overfullWarnings" -ForegroundColor $(if ($overfullWarnings -gt 0) {"Yellow"} else {"Green"})
        Write-Host "Underfull box warnings: $underfullWarnings" -ForegroundColor $(if ($underfullWarnings -gt 0) {"Yellow"} else {"Green"})
        Write-Host "Undefined references: $undefinedReferences" -ForegroundColor $(if ($undefinedReferences -gt 0) {"Red"} else {"Green"})
        
        if ($overfullWarnings -eq 0 -and $underfullWarnings -eq 0 -and $undefinedReferences -eq 0) {
            Write-Host "✓ No formatting issues detected!" -ForegroundColor Green
        } else {
            Write-Host "⚠ Some formatting issues remain. Check the .log file for details." -ForegroundColor Yellow
        }
    }
}

# Main execution
Write-Host "Starting LaTeX formatting fix process..." -ForegroundColor Cyan

# Clean up old files
Clean-LatexFiles

# Compile the document
Compile-Document

# Show summary
Show-CompilationSummary

Write-Host "`nFormatting fix process completed!" -ForegroundColor Green
Write-Host "Tips for further improvements:" -ForegroundColor Cyan
Write-Host "1. Use \\raggedbottom to reduce underfull vbox warnings" -ForegroundColor White
Write-Host "2. Break long lines in tables and code blocks" -ForegroundColor White
Write-Host "3. Use appropriate column widths in tables" -ForegroundColor White
Write-Host "4. Consider using microtype package for better typography" -ForegroundColor White
