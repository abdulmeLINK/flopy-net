---
sidebar_position: 2
---

# Contributing Guidelines

Learn how to contribute to FLOPY-NET, including code standards, submission processes, and community guidelines.

## Getting Started

Thank you for your interest in contributing to FLOPY-NET! This guide will help you understand our development process and how to submit high-quality contributions.

### Before You Start

1. **Read the Documentation**: Familiarize yourself with FLOPY-NET's architecture and components
2. **Set Up Development Environment**: Follow the [Development Setup Guide](./setup.md)
3. **Check Existing Issues**: Look for existing issues or discussions related to your contribution
4. **Join the Community**: Engage with the community through GitHub Discussions

## Types of Contributions

We welcome various types of contributions:

### Code Contributions
- **Bug fixes**: Fix identified issues in the codebase
- **Feature enhancements**: Add new features or improve existing ones
- **Performance improvements**: Optimize system performance
- **Component development**: Create new FL algorithms, scenarios, or policies

### Documentation Contributions
- **API documentation**: Improve or add API documentation
- **Tutorials**: Create new tutorials or improve existing ones
- **User guides**: Enhance user documentation
- **Code comments**: Improve inline documentation

### Community Contributions
- **Issue reporting**: Report bugs or suggest enhancements
- **Testing**: Help test new features and bug fixes
- **Reviews**: Review pull requests from other contributors
- **Support**: Help other users in discussions and issues

## Code Standards

### Python Code Style

We follow PEP 8 with some modifications enforced by Black:

```python
# Good: Clear, descriptive naming
class FederatedLearningServer:
    def __init__(self, config: Dict[str, Any]):
        self.client_manager = ClientManager(config)
        self.aggregation_strategy = config.get("aggregation", "fedavg")
    
    async def handle_client_update(self, client_id: str, 
                                  model_update: Dict[str, Any]) -> bool:
        """
        Handle model update from client.
        
        Args:
            client_id: Unique identifier for the client
            model_update: Model parameters and metadata
            
        Returns:
            bool: True if update was processed successfully
            
        Raises:
            PolicyViolationError: If update violates policies
        """
        # Validate update against policies
        if not await self.policy_engine.validate_update(client_id, model_update):
            raise PolicyViolationError(f"Update from {client_id} violates policies")
        
        # Process the update
        return await self.aggregation_strategy.add_update(model_update)
```

### Code Quality Requirements

#### 1. Type Hints
Use type hints for all function parameters and return values:

```python
from typing import Dict, List, Optional, Union, Any

def process_client_data(client_data: Dict[str, Any], 
                       validation_rules: List[str]) -> Optional[Dict[str, Union[str, float]]]:
    """Process client data with validation."""
    # Implementation here
    pass
```

#### 2. Documentation
All public functions, classes, and modules must have docstrings:

```python
class PolicyEngine:
    """
    Core policy engine for FLOPY-NET governance and compliance.
    
    The PolicyEngine evaluates requests against configured policies and
    makes authorization decisions for system operations.
    
    Example:
        >>> engine = PolicyEngine(config)
        >>> result = await engine.evaluate_request(request)
        >>> if result.decision == "allow":
        >>>     # Proceed with operation
        >>>     pass
    
    Attributes:
        policies: List of active policies
        decision_cache: Cache for policy decisions
        evaluation_history: History of policy evaluations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the policy engine.
        
        Args:
            config: Configuration dictionary containing policy definitions,
                   cache settings, and evaluation parameters
                   
        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
```

#### 3. Error Handling
Use appropriate exception handling and custom exceptions:

```python
class FLOPYNETError(Exception):
    """Base exception for FLOPY-NET errors."""
    pass

class PolicyViolationError(FLOPYNETError):
    """Raised when an operation violates system policies."""
    
    def __init__(self, message: str, violated_policies: List[str] = None):
        super().__init__(message)
        self.violated_policies = violated_policies or []

class NetworkError(FLOPYNETError):
    """Raised when network operations fail."""
    pass

# Usage
try:
    await client.connect()
except NetworkError as e:
    logger.error(f"Failed to connect client: {e}")
    # Handle gracefully
except PolicyViolationError as e:
    logger.warning(f"Policy violation: {e}, Policies: {e.violated_policies}")
    # Report to policy engine
```

#### 4. Logging
Use structured logging throughout the codebase:

```python
import logging
import json

logger = logging.getLogger(__name__)

class FLServer:
    def start_training_round(self, round_number: int, participating_clients: List[str]):
        """Start a new training round."""
        logger.info(
            "Starting training round",
            extra={
                "round_number": round_number,
                "client_count": len(participating_clients),
                "clients": participating_clients,
                "component": "fl_server"
            }
        )
        
        try:
            # Training logic
            pass
        except Exception as e:
            logger.error(
                "Training round failed",
                extra={
                    "round_number": round_number,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "component": "fl_server"
                },
                exc_info=True
            )
```

### TypeScript/JavaScript Standards

For dashboard frontend development:

```typescript
// Good: Clear interfaces and error handling
interface ClientMetrics {
  clientId: string;
  accuracy: number;
  loss: number;
  participationRate: number;
  lastSeen: Date;
}

interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

class DashboardApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
    async getClientMetrics(experimentId: string): Promise<ClientMetrics[]> {
    try {
      const response = await fetch(this.baseUrl + '/api/fl-monitoring/clients?experiment=' + experimentId);
      
      if (!response.ok) {
        throw new Error('HTTP ' + response.status + ': ' + response.statusText);
      }
      
      const data: ApiResponse<ClientMetrics[]> = await response.json();
      return data.data;
      
    } catch (error) {
      console.error('Failed to fetch client metrics:', error);
      throw new Error('Failed to fetch client metrics: ' + error.message);
    }
  }
}
```

## Testing Requirements

### Test Coverage
All new code must have adequate test coverage:

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

### Test Structure

```python
# tests/unit/test_policy_engine.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.policy_engine.engine import PolicyEngine
from src.policy_engine.exceptions import PolicyViolationError

class TestPolicyEngine:
    """Test suite for PolicyEngine class."""
    
    @pytest.fixture
    def policy_config(self):
        """Sample policy configuration for testing."""
        return {
            "policies": [
                {
                    "name": "resource_limit",
                    "rules": [
                        {
                            "condition": "cpu_usage > 0.8",
                            "action": "deny",
                            "message": "CPU usage too high"
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def policy_engine(self, policy_config):
        """Create PolicyEngine instance for testing."""
        return PolicyEngine(policy_config)
    
    @pytest.mark.asyncio
    async def test_evaluate_request_allow(self, policy_engine):
        """Test that valid requests are allowed."""
        request = {
            "client_id": "test-client",
            "action": "join_training",
            "resources": {"cpu_usage": 0.5}
        }
        
        result = await policy_engine.evaluate_request(request)
        
        assert result["decision"] == "allow"
        assert result["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_evaluate_request_deny(self, policy_engine):
        """Test that policy violations are denied."""
        request = {
            "client_id": "test-client",
            "action": "join_training",
            "resources": {"cpu_usage": 0.9}  # Exceeds limit
        }
        
        result = await policy_engine.evaluate_request(request)
        
        assert result["decision"] == "deny"
        assert "resource_limit" in result["violated_policies"]
    
    @pytest.mark.asyncio
    async def test_policy_engine_caching(self, policy_engine):
        """Test that policy decisions are properly cached."""
        request = {
            "client_id": "test-client",
            "action": "join_training",
            "resources": {"cpu_usage": 0.5}
        }
        
        # First evaluation
        result1 = await policy_engine.evaluate_request(request)
        
        # Second evaluation (should use cache)
        result2 = await policy_engine.evaluate_request(request)
        
        assert result1 == result2
        # Verify cache was used (implementation specific)
        assert policy_engine.cache_hits > 0
```

### Testing Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Run tests for specific components
pytest tests/unit/test_policy_engine.py
pytest tests/integration/test_fl_workflow.py
```

## Submission Process

### 1. Issue Creation

Before starting work, create or find a relevant issue:

```markdown
## Bug Report

**Description**: Brief description of the bug

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python Version: [e.g., 3.9.7]
- FLOPY-NET Version: [e.g., 1.0.0-alpha.8]

**Additional Context**: Any additional information

---

## Feature Request

**Problem Statement**: Describe the problem this feature would solve

**Proposed Solution**: Describe your proposed solution

**Alternatives Considered**: Describe alternatives you've considered

**Implementation Details**: Technical details about implementation

**Breaking Changes**: Any potential breaking changes

**Testing Strategy**: How this feature should be tested
```

### 2. Branch Creation

Create a feature branch from `develop`:

```bash
# Sync with latest develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/policy-engine-improvements

# Or for bug fixes
git checkout -b hotfix/client-connection-bug
```

### 3. Development Process

1. **Write Tests First** (TDD approach recommended)
2. **Implement Feature**
3. **Update Documentation**
4. **Ensure Code Quality**

```bash
# Check code quality before committing
black src/
flake8 src/
mypy src/
pytest --cov=src

# Commit changes
git add .
git commit -m "feat(policy-engine): add adaptive policy evaluation

- Implement adaptive policy scoring based on historical data
- Add caching layer for improved performance  
- Update policy engine API to support confidence scores
- Add comprehensive test coverage

Closes #123"
```

### 4. Pull Request Guidelines

#### PR Title Format
Follow conventional commits:

- `feat(component): add new feature`
- `fix(component): fix bug description`
- `docs(component): update documentation`
- `test(component): add tests for feature`
- `refactor(component): refactor code for clarity`
- `perf(component): improve performance`

#### PR Description Template

```markdown
## Summary
Brief description of the changes in this PR.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Closes #123
Related to #456

## Changes Made
- Detailed list of changes
- Include any breaking changes
- Mention new dependencies

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

### Test Results
```
pytest --cov=src
==== 156 passed, 0 failed, 0 skipped ====
Coverage: 94%
```

## Deployment Testing
- [ ] Tested in development environment
- [ ] Tested with Docker Compose
- [ ] Dashboard functionality verified

## Documentation
- [ ] Code comments updated
- [ ] API documentation updated
- [ ] User documentation updated
- [ ] README updated (if needed)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### 5. Code Review Process

#### For Contributors
1. **Self-review**: Review your own code thoroughly
2. **Address feedback**: Respond to review comments promptly
3. **Update tests**: Add tests based on review feedback
4. **Rebase if needed**: Keep commit history clean

#### For Reviewers
1. **Review promptly**: Aim to review within 2-3 business days
2. **Be constructive**: Provide helpful feedback with suggestions
3. **Test the changes**: Pull and test the changes locally
4. **Check documentation**: Ensure documentation is updated

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment:

1. **Be respectful**: Treat all community members with respect
2. **Be inclusive**: Welcome newcomers and diverse perspectives  
3. **Be collaborative**: Work together to solve problems
4. **Be patient**: Help others learn and grow
5. **Give credit**: Acknowledge others' contributions

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General discussions and questions
- **Pull Requests**: Code review and collaboration
- **Documentation**: Comprehensive guides and references

### Recognition

We recognize contributions in several ways:

1. **Contributors file**: All contributors are listed in CONTRIBUTORS.md
2. **Release notes**: Significant contributions are mentioned in releases
3. **Community highlights**: Outstanding contributions are highlighted
4. **Maintainer status**: Active contributors may be invited as maintainers

## Release Process

### Version Management

We use semantic versioning (SemVer):
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Workflow

1. **Feature freeze**: No new features for release branch
2. **Testing**: Comprehensive testing of release candidate
3. **Documentation**: Update documentation and release notes
4. **Release**: Tag and publish release
5. **Post-release**: Monitor for issues and hotfixes

## Getting Help

If you need help:

1. **Check documentation**: Review existing documentation
2. **Search issues**: Look for similar issues or questions
3. **Ask in discussions**: Use GitHub Discussions for questions
4. **Create an issue**: For bugs or specific help requests

## Thank You

Your contributions help make FLOPY-NET better for everyone. Whether you're fixing bugs, adding features, improving documentation, or helping other users, every contribution is valuable and appreciated!

For questions about contributing, please reach out through GitHub Discussions or create an issue.
