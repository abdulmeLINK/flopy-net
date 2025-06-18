#!/usr/bin/env powershell

# This script fixes double backslashes in node definitions

$sections_dir = Join-Path $PSScriptRoot "sections"
$section_files = Get-ChildItem -Path $sections_dir -Filter "*.tex"

foreach ($file in $section_files) {
    Write-Host "Fixing $($file.FullName)"
    $content = Get-Content -Path $file.FullName -Raw
    
    # Replace double backslashes in node text with single backslashes
    $new_content = $content -replace '{([^}]*?)\\\\([^}]*?)}', '{$1\\$2}'
    
    # If there were changes, write the file
    if ($content -ne $new_content) {
        Write-Host "  Changes detected, saving..."
        Set-Content -Path $file.FullName -Value $new_content
    }
}

Write-Host "Done fixing backslashes!"
