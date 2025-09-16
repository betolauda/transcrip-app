# Testing Guide

This document provides comprehensive guidance on testing the Spanish Audio Transcription API.

## Overview

The project implements a comprehensive testing strategy covering:
- **Unit Tests**: Individual component testing with 80%+ coverage
- **Integration Tests**: Service interaction and workflow testing
- **API Tests**: Complete endpoint testing with security validation
- **Security Tests**: File upload safety and vulnerability testing
- **Performance Tests**: Load testing and resource usage validation

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
├── fixtures/
│   ├── __init__.py
│   └── test_data.py           # Sample data and file generators
├── utils/
│   ├── __init__.py
│   └── test_helpers.py        # Testing utilities
├── unit/                      # Unit tests for individual components
│   ├── repositories/
│   └── services/
├── integration/               # Service interaction tests
├── api/                       # API endpoint tests
├── security/                  # Security-focused tests
└── performance/               # Performance and load tests
```

## Quick Start

### Prerequisites

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Or use Make
make install-dev
```

### Running Tests

```bash
# Run complete test suite with quality gates
make test

# Run tests without performance tests (faster)
make test-quick

# Run specific test categories
make test-unit
make test-integration
make test-api
make test-security
make test-performance
```

### Using the Test Runner

The comprehensive test runner provides unified testing with quality gates:

```bash
# Full test suite
python scripts/test_runner.py

# Skip performance tests
python scripts/test_runner.py --skip-performance

# Custom project root
python scripts/test_runner.py --project-root /path/to/project
```

## Test Categories

### Unit Tests

Tests individual components in isolation with mocked dependencies.

**Coverage**: 80%+ line coverage required
**Location**: `tests/unit/`
**Command**: `make test-unit`

Key areas:
- Repository database operations
- Service business logic
- File validation and security
- Term detection algorithms
- Error handling

### Integration Tests

Tests service interactions and complete workflows.

**Location**: `tests/integration/`
**Command**: `make test-integration`

Key scenarios:
- Transcription → Glossary update workflow
- Term detection → Candidate promotion
- Concurrent service operations
- Database transaction integrity
- Configuration integration

### API Tests

Tests FastAPI endpoints with realistic HTTP scenarios.

**Location**: `tests/api/`
**Command**: `make test-api`

Coverage:
- File upload endpoint with security validation
- Glossary retrieval endpoints
- Candidate management endpoints
- Error handling consistency
- Integration workflows

### Security Tests

Focused testing for security vulnerabilities and file safety.

**Location**: `tests/security/`
**Command**: `make test-security`

Validation:
- File upload security (MIME spoofing, malicious content)
- Path traversal protection
- File size and type validation
- Input sanitization
- SQL injection prevention

### Performance Tests

Load testing and resource usage validation.

**Location**: `tests/performance/`
**Command**: `make test-performance`

Metrics:
- Single transcription performance (< 2s)
- Concurrent throughput (> 2 files/second)
- Memory usage stability (< 100MB growth)
- Text processing rate (> 10k chars/second)
- End-to-end workflow timing (< 4s)

## Configuration

### Environment Variables

Tests use these environment variables:

```bash
# Test database (in-memory for speed)
DB_PATH=:memory:

# Fast Whisper model for testing
WHISPER_MODEL=tiny

# API base URL for integration tests
API_BASE_URL=http://localhost:8000
```

### Pytest Configuration

Configuration in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    security: Security tests
    performance: Performance tests
    slow: Slow-running tests
addopts =
    --strict-markers
    --strict-config
    --verbose
env =
    DB_PATH = :memory:
    WHISPER_MODEL = tiny
```

### Coverage Configuration

Coverage settings in `.coveragerc`:

- **Source**: `src/` directory
- **Omit**: Virtual environments, tests, migrations
- **Threshold**: 80% minimum line coverage
- **Reports**: XML, HTML, and terminal output

## Quality Gates

The testing framework enforces these quality gates:

### Test Coverage
- **Minimum**: 80% line coverage
- **Target**: 90%+ line coverage
- **Branch Coverage**: Tracked and reported

### Security
- **Bandit**: No medium+ severity issues
- **Safety**: No known vulnerabilities in dependencies
- **File Upload**: All security tests must pass

### Code Quality
- **Flake8**: No linting violations
- **Black**: Code must be formatted
- **isort**: Imports must be sorted
- **MyPy**: Type checking must pass

### Performance
- **Transcription**: < 2s per file
- **Throughput**: > 2 files/second concurrent
- **Memory**: < 100MB growth under load
- **End-to-End**: < 4s complete workflow

## Fixtures and Test Data

### Database Fixtures

```python
@pytest.fixture
def db_repository():
    """In-memory database for testing."""

@pytest.fixture
def populated_db_repository():
    """Database with sample data."""
```

### Service Fixtures

```python
@pytest.fixture
def transcription_service():
    """TranscriptionService with test configuration."""

@pytest.fixture
def glossary_service():
    """GlossaryService with test database."""
```

### File Fixtures

```python
@pytest.fixture
def sample_mp3_content():
    """Generate MP3 file content for testing."""

@pytest.fixture
def malicious_file_content():
    """Generate malicious file for security testing."""
```

### Mock Fixtures

```python
@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for fast testing."""
```

## Test Data

Sample data in `tests/fixtures/test_data.py`:

- **SAMPLE_TRANSCRIPTS**: Economic and Argentine expression samples
- **SAMPLE_ECONOMIC_TERMS**: Test economic vocabulary
- **SAMPLE_ARGENTINE_EXPRESSIONS**: Test Argentine slang
- **File Generators**: MP3 and malicious file creation functions

## Running Tests in CI/CD

GitHub Actions configuration runs tests automatically:

### On Pull Request
- Unit tests with coverage
- Integration tests
- Security scans
- Code quality checks

### On Main Branch
- Full test suite including performance
- Coverage reporting to Codecov
- Security artifact generation
- Quality gate enforcement

### Commands for CI

```bash
# Install dependencies
make install

# Run CI test suite
make ci-test

# Run quality checks
make ci-quality
```

## Debugging Tests

### Running Individual Tests

```bash
# Single test file
pytest tests/unit/services/test_transcription_service.py -v

# Single test method
pytest tests/unit/services/test_transcription_service.py::TestTranscriptionService::test_transcribe_audio_success -v

# Tests matching pattern
pytest -k "transcription" -v
```

### Test Output and Logging

```bash
# Detailed output
pytest -vv

# Show print statements
pytest -s

# Show coverage with missing lines
pytest --cov=src --cov-report=term-missing
```

### Common Issues

1. **Database Locks**: Ensure tests use `:memory:` database
2. **File Permissions**: Use `temporary_file` helper for test files
3. **Mock Issues**: Verify mock patches target correct modules
4. **Async Issues**: Use `pytest-asyncio` for async test functions

## Extending Tests

### Adding New Unit Tests

1. Create test file in appropriate `tests/unit/` subdirectory
2. Import required fixtures from `conftest.py`
3. Follow naming convention: `test_<functionality>_<scenario>`
4. Include docstrings describing test purpose
5. Use appropriate assertions and mocks

### Adding Integration Tests

1. Focus on service interactions and workflows
2. Use real database operations (in-memory)
3. Test error propagation and transaction handling
4. Verify data consistency across services

### Adding Performance Tests

1. Establish baseline metrics
2. Use statistical analysis for timing
3. Test under various load conditions
4. Generate performance reports for CI

## Best Practices

### Test Organization
- One test class per service/component
- Group related tests in test classes
- Use descriptive test and class names
- Include comprehensive docstrings

### Test Data
- Use fixtures for reusable test data
- Generate realistic but deterministic data
- Clean up resources in fixture teardown
- Avoid hard-coded values

### Assertions
- Use specific assertions (not just `assert True`)
- Test both positive and negative cases
- Include edge cases and error conditions
- Verify all aspects of the result

### Mocking
- Mock external dependencies consistently
- Use appropriate mock return values
- Verify mock interactions when needed
- Don't over-mock - test real code paths

### Performance
- Separate slow tests with markers
- Use in-memory databases for speed
- Mock expensive operations
- Measure what matters for user experience

## Troubleshooting

### Common Test Failures

1. **Coverage Below Threshold**
   - Add tests for uncovered lines
   - Check for unreachable code
   - Verify test configuration

2. **Security Test Failures**
   - Update test data for new threats
   - Verify file validation logic
   - Check dependency vulnerabilities

3. **Performance Test Failures**
   - Adjust thresholds for test environment
   - Optimize slow operations
   - Use faster mock implementations

4. **Integration Test Failures**
   - Check service configuration
   - Verify database schema
   - Validate test environment setup

### Getting Help

- Check test output for specific error messages
- Review test documentation and examples
- Examine fixture definitions in `conftest.py`
- Look at similar tests for patterns
- Run individual tests for isolation