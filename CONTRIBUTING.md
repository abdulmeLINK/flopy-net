# Contributing to Federated Learning with SDN Integration

Thank you for your interest in contributing to our project! This document provides guidelines and best practices for contributing.

## Git Workflow

### Branching Strategy

We follow a simplified Git Flow approach:

- `main`: Production-ready code
- `dev`: Development branch, integrate features here
- Feature branches: Create from `dev`, name as `feature/your-feature-name`
- Bug fix branches: Create from `dev`, name as `fix/bug-description`

### Pull Request Process

1. Create a branch from `dev` for your feature or fix
2. Make your changes, commit them using meaningful commit messages
3. Push your branch and create a Pull Request to merge back into `dev`
4. Request reviews from maintainers
5. Address any feedback
6. Once approved, your branch will be merged

## Commit Guidelines

Follow these best practices for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests after the first line

Example:
```
Add policy caching mechanism for improved performance

Closes #123
```

## Code Style

- Follow PEP 8 style guide for Python code
- Use docstrings for functions, classes, and modules
- Add type hints to function signatures when possible

## Working with Large Files

If you need to work with large files (models, datasets):

1. First check if they're truly necessary to include in the repository
2. Consider adding them to `.gitignore` if they can be generated/downloaded
3. For necessary large files, use Git LFS (Large File Storage):
   - Install Git LFS: https://git-lfs.github.com/
   - Uncomment the relevant patterns in `.gitattributes`
   - Track large files with: `git lfs track "*.h5"`

## Environment Setup

Always use a virtual environment for development:

```bash
# Create a virtual environment
python -m venv flsdn

# Activate it (Linux/macOS)
source flsdn/bin/activate

# Activate it (Windows)
.\flsdn\Scripts\activate

# Install dependencies
pip install -r requirements-docker.txt
```

## Testing

- Write tests for new features
- Ensure all tests pass before submitting a PR
- Run the test suite with: `pytest`

## Documentation

- Update documentation when changing functionality
- Use markdown for documentation files
- Keep the README.md up to date

## Docker Development

When working with Docker:

- Test Docker builds locally before pushing
- Don't commit built images or volumes
- Update docker-compose.yml when adding new services
- Document any changes to Docker configuration

## Questions?

If you have any questions or need clarification, please open an issue or contact the maintainers. 