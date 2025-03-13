#!/bin/bash
# Initialize Git repository with proper settings for the Federated Learning project

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Git is not installed. Please install Git and try again."
    exit 1
fi

# Initialize Git repository if it doesn't exist
if [ ! -d .git ]; then
    echo "Initializing Git repository..."
    git init
else
    echo "Git repository already exists."
fi

# Configure Git to use correct line endings
echo "Configuring Git line endings..."
git config core.autocrlf input

# Check if Git LFS is installed
if ! command -v git-lfs &> /dev/null; then
    echo "Git LFS is not installed. Large files will not be tracked correctly."
    echo "Please install Git LFS from https://git-lfs.github.com/ if you need to work with large files."
else
    # Initialize Git LFS
    echo "Initializing Git LFS..."
    git lfs install
    
    # Uncomment LFS configurations in .gitattributes if needed
    # Uncomment the following lines if you want to enable Git LFS for model files
    # sed -i 's/# \(\*.h5 filter=lfs diff=lfs merge=lfs -text\)/\1/' .gitattributes
    # sed -i 's/# \(\*.pt filter=lfs diff=lfs merge=lfs -text\)/\1/' .gitattributes
    # sed -i 's/# \(\*.pth filter=lfs diff=lfs merge=lfs -text\)/\1/' .gitattributes
    # sed -i 's/# \(\*.onnx filter=lfs diff=lfs merge=lfs -text\)/\1/' .gitattributes
fi

# Create dev branch
echo "Creating dev branch..."
git checkout -b dev

# Initial commit
echo "Making initial commit..."
git add .gitignore .gitattributes CONTRIBUTING.md README.md
git commit -m "Initial commit: Add Git configuration files"

echo "Git repository successfully initialized!"
echo "Please create a remote repository and push your changes with:"
echo "  git remote add origin <your-repository-url>"
echo "  git push -u origin dev" 