#!/bin/bash
# Script to create and push to a new branch for the model repository fix

# Branch name with date for uniqueness
BRANCH_NAME="fix/model-repository-$(date +%Y%m%d)"

echo "Creating new branch: $BRANCH_NAME"
git checkout -b $BRANCH_NAME

echo "Adding modified files..."
git add src/infrastructure/repositories/file_model_repository.py
git add src/domain/interfaces/fl_model_repository.py
git add src/infrastructure/repositories/README.md
git add src/domain/entities/README.md
git add src/infrastructure/repositories/model_cleanup.py
git add README.md
git add test_model_versions.py

echo "Committing changes..."
git commit -m "Fix model repository serialization and update documentation

- Fix NumPy array serialization in FileModelRepository
- Update interface to use explicit FLModel type
- Add proper model versioning with metadata
- Create cleanup tool for legacy model formats
- Update documentation to reflect new model storage format"

echo "Pushing to remote repository..."
git push origin $BRANCH_NAME

echo "Done! New branch '$BRANCH_NAME' has been pushed to the remote repository."
echo "To create a pull request, visit your Git repository web interface." 