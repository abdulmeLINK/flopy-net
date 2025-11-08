# Contributing to FLOPY-NET

Thank you for your interest in contributing to FLOPY-NET! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Testing Guidelines](#testing-guidelines)

---

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- **Be Respectful**: Treat all community members with respect and professionalism
- **Be Collaborative**: Work together constructively and accept feedback gracefully
- **Be Inclusive**: Welcome contributors from all backgrounds and experience levels
- **Be Professional**: Focus on technical merit and constructive discussion

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.8+ installed
- Node.js 18+ and npm/yarn (for dashboard development)
- Docker and Docker Compose
- GNS3 VM configured (for network emulation testing)
- Git for version control

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/flopy-net.git
   cd flopy-net
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/abdulmeLINK/flopy-net.git
   ```

---

## Development Setup

### Python Backend Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run tests**:
   ```bash
   pytest src/tests/
   ```

### Dashboard Frontend Setup

1. **Navigate to dashboard directory**:
   ```bash
   cd dashboard/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Run linting**:
   ```bash
   npm run lint
   ```

### Documentation Setup

1. **Navigate to docs directory**:
   ```bash
   cd docs
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start local docs server**:
   ```bash
   npm start
   ```

---

## Coding Standards

### Python Code Style

Follow **PEP 8** style guidelines with these specific conventions:

- **Indentation**: 4 spaces (no tabs)
- **Line Length**: Maximum 100 characters (relaxed from PEP 8's 79)
- **Imports**: Group in order: standard library, third-party, local application
- **Docstrings**: Use Google-style docstrings for all public functions/classes

**Example**:
```python
def calculate_aggregation(client_models: List[Dict], weights: List[float]) -> Dict:
    """
    Aggregates client models using weighted averaging.
    
    Args:
        client_models: List of client model parameters
        weights: List of aggregation weights for each client
        
    Returns:
        Dict containing aggregated model parameters
        
    Raises:
        ValueError: If lengths of client_models and weights don't match
    """
    if len(client_models) != len(weights):
        raise ValueError("Mismatch between models and weights")
    
    # Implementation here
    return aggregated_model
```

### TypeScript/React Code Style

Follow project conventions:

- **Indentation**: 2 spaces
- **Semicolons**: Required
- **Quotes**: Single quotes for strings
- **Components**: Use functional components with TypeScript
- **Naming**: PascalCase for components, camelCase for functions/variables

**Example**:
```typescript
interface FlTrainingProps {
  rounds: number;
  accuracy: number;
}

export const FlTrainingCard: React.FC<FlTrainingProps> = ({ rounds, accuracy }) => {
  const [isLoading, setIsLoading] = useState(false);
  
  return (
    <div className="training-card">
      <h3>Training Round {rounds}</h3>
      <p>Accuracy: {accuracy.toFixed(2)}%</p>
    </div>
  );
};
```

### Configuration Files

- **JSON**: Use 2-space indentation, no trailing commas
- **YAML**: Use 2-space indentation
- **Validate**: Always validate configuration files before committing

---

## Commit Message Guidelines

Follow the **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates

### Examples

```
feat(policy-engine): add network bandwidth policy type

Implements new policy type for enforcing bandwidth constraints
on FL clients. Includes validation logic and dashboard integration.

Closes #45
```

```
fix(dashboard): correct events page filtering bug

Events page was incorrectly filtering by 'type' instead of 'event_type',
causing no results to display when filters were applied.

Fixes #5
```

```
docs(readme): update installation instructions

Added Docker prerequisites and clarified GNS3 VM setup steps.
```

### Commit Guidelines

- **Keep commits atomic**: One logical change per commit
- **Write descriptive messages**: Explain why, not just what
- **Reference issues**: Use `Closes #123` or `Fixes #123` in commit body
- **Sign commits**: Use `git commit -s` to add sign-off

---

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all tests**:
   ```bash
   # Python tests
   pytest src/tests/
   
   # Frontend tests
   cd dashboard/frontend && npm test
   ```

3. **Check code style**:
   ```bash
   # Python linting
   flake8 src/
   
   # Frontend linting
   cd dashboard/frontend && npm run lint
   ```

4. **Update documentation**: If adding features, update relevant docs

### Creating the Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open PR on GitHub** with:
   - Clear, descriptive title
   - Detailed description of changes
   - Link to related issues
   - Screenshots/GIFs for UI changes
   - Test results summary

3. **Use the PR template** (`.github/PULL_REQUEST_TEMPLATE.md`)

### PR Review Process

- **Automated checks**: CI/CD pipeline runs tests and linting
- **Code review**: At least one maintainer review required
- **Discussion**: Address reviewer feedback constructively
- **Updates**: Push additional commits to address feedback
- **Merge**: Maintainer will merge once approved

---

## Issue Reporting

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** for solutions
3. **Try latest version** to confirm bug still exists

### Creating an Issue

Use the appropriate issue template:

- **Bug Report** (`.github/ISSUE_TEMPLATE/bug_report.md`)
- **Feature Request** (`.github/ISSUE_TEMPLATE/feature_request.md`)
- **Documentation Issue** (`.github/ISSUE_TEMPLATE/documentation.md`)

Include:
- Clear, descriptive title
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs and screenshots
- Configuration files (sanitized)

---

## Testing Guidelines

### Python Unit Tests

- **Location**: `src/tests/`
- **Framework**: pytest
- **Coverage**: Aim for >80% coverage
- **Naming**: `test_<feature>_<scenario>.py`

**Example**:
```python
import pytest
from src.policy_engine.policy_validator import PolicyValidator

def test_policy_validator_accepts_valid_policy():
    """Test that validator accepts valid policy configurations."""
    validator = PolicyValidator()
    policy = {"type": "model_size", "max_size_mb": 100}
    
    assert validator.validate(policy) == True

def test_policy_validator_rejects_invalid_policy():
    """Test that validator rejects invalid policy configurations."""
    validator = PolicyValidator()
    policy = {"type": "unknown_type"}
    
    with pytest.raises(ValueError):
        validator.validate(policy)
```

### Frontend Tests

- **Location**: `dashboard/frontend/src/__tests__/`
- **Framework**: Vitest + React Testing Library
- **Coverage**: Test user interactions and state management

**Example**:
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { FlTrainingCard } from '../components/FlTrainingCard';

describe('FlTrainingCard', () => {
  it('renders training round and accuracy', () => {
    render(<FlTrainingCard rounds={5} accuracy={92.5} />);
    
    expect(screen.getByText(/Training Round 5/i)).toBeInTheDocument();
    expect(screen.getByText(/Accuracy: 92.50%/i)).toBeInTheDocument();
  });
});
```

### Integration Tests

- Test full workflows (FL training, policy enforcement, network scenarios)
- Use Docker Compose for test environments
- Document test setup and teardown procedures

---

## Additional Resources

- **Main Documentation**: https://flopynetdocs-a960.eu.onamber.cloud/
- **GitHub Issues**: https://github.com/abdulmeLINK/flopy-net/issues
- **Discussions**: https://github.com/abdulmeLINK/flopy-net/discussions

---

## Questions?

If you have questions not covered in this guide:

1. Check the [documentation](https://flopynetdocs-a960.eu.onamber.cloud/)
2. Search [existing issues](https://github.com/abdulmeLINK/flopy-net/issues)
3. Create a new [discussion](https://github.com/abdulmeLINK/flopy-net/discussions)

Thank you for contributing to FLOPY-NET! 🚀
