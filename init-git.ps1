# Initialize Git repository with proper settings for the Federated Learning project

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "Git version: $gitVersion"
} catch {
    Write-Host "Git is not installed. Please install Git and try again."
    exit 1
}

# Initialize Git repository if it doesn't exist
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..."
    git init
} else {
    Write-Host "Git repository already exists."
}

# Configure Git to use correct line endings
Write-Host "Configuring Git line endings..."
git config core.autocrlf true

# Check if Git LFS is installed
try {
    $gitLfsVersion = git lfs version
    Write-Host "Git LFS is installed: $gitLfsVersion"
    
    # Initialize Git LFS
    Write-Host "Initializing Git LFS..."
    git lfs install
    
    # Uncomment LFS configurations in .gitattributes if needed
    # Note: PowerShell equivalent for sed is more verbose, so just inform the user
    Write-Host "If you need to track large model files with Git LFS,"
    Write-Host "please uncomment the relevant lines in .gitattributes manually."
} catch {
    Write-Host "Git LFS is not installed. Large files will not be tracked correctly."
    Write-Host "Please install Git LFS from https://git-lfs.github.com/ if you need to work with large files."
}

# Create dev branch
Write-Host "Creating dev branch..."
git checkout -b dev

# Initial commit
Write-Host "Making initial commit..."
git add .gitignore .gitattributes CONTRIBUTING.md README.md
git commit -m "Initial commit: Add Git configuration files"

Write-Host "`nGit repository successfully initialized!"
Write-Host "Please create a remote repository and push your changes with:"
Write-Host "  git remote add origin <your-repository-url>"
Write-Host "  git push -u origin dev" 