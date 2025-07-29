# CI/CD Pipeline Documentation

This project uses GitHub Actions for continuous integration and deployment.

## Workflows

### Main CI/CD Pipeline (`.github/workflows/ci.yml`)

The CI/CD pipeline runs on:
- **Push** to `main` or `develop` branches
- **Pull requests** to `main` or `develop` branches

#### Jobs

1. **Test and Quality Check** (Python 3.12)
   - Code syntax validation
   - Code formatting with Black
   - Import sorting with isort
   - Linting with flake8
   - Unit and integration tests with pytest
   - Test coverage reporting
   - Security audit with pip-audit

2. **Python Compatibility** (Python 3.11, 3.13)
   - Basic syntax and import checks
   - Core functionality tests
   - Ensures compatibility across Python versions

## Development Workflow

### Before Committing
Run these commands locally to ensure CI passes:

```bash
# Install development dependencies
pip install black isort flake8 pytest pytest-asyncio pytest-httpx pytest-cov pip-audit

# Format code
black .
isort .

# Run linting
flake8 .

# Run tests
pytest tests/ -v

# Security check
pip-audit --desc
```

### Code Quality Standards

- **Black**: Code formatting (88 character line length)
- **isort**: Import sorting with Black compatibility
- **flake8**: Linting with complexity limit of 10
- **pytest**: Testing with async support
- **Coverage**: Minimum coverage reporting

### Configuration Files

- `pyproject.toml`: Black, isort, pytest, and coverage configuration
- `.flake8`: Flake8 linting configuration
- `requirements.txt`: Production dependencies
- `requirements-dev.txt`: Development dependencies

## Security

The pipeline includes:
- **pip-audit**: Vulnerability scanning of Python packages
- **Basic secret scanning**: Simple regex patterns for common secrets

## Python Version Support

- **Primary**: Python 3.12 (full test suite)
- **Compatibility**: Python 3.11, 3.13 (basic tests)

## Environment Variables

Tests use mock environment variables and don't require:
- `MERAKI_API_KEY` (mocked in tests)
- External API access

## Troubleshooting CI Failures

### Code Formatting Failures
```bash
black --check --diff .  # See formatting issues
black .                 # Fix formatting
```

### Import Sorting Failures
```bash
isort --check-only --diff .  # See import issues
isort .                      # Fix imports
```

### Linting Failures
```bash
flake8 .  # See linting issues
```

### Test Failures
```bash
pytest tests/ -v --tb=long  # Detailed test output
```

### Security Audit Warnings
- Review pip-audit output for known vulnerabilities
- Update dependencies if needed
- Add security exceptions if false positives

## Adding New Dependencies

1. Add to `requirements.txt` for production dependencies
2. Add to `requirements-dev.txt` for development dependencies
3. Update version pins for security
4. Test locally before committing

## Performance

- **Caching**: pip dependencies are cached across runs
- **Matrix builds**: Parallel execution for different Python versions
- **Selective testing**: Compatibility tests run basic subset only