# Tests Organization

This directory contains all tests for the domjudge-cli project, organized by test type.

## Structure

```
tests/
├── unit/              # Unit tests - fast, isolated tests of individual components
│   ├── infrastructure/  # Infrastructure layer tests (cache, rate limiter, secrets)
│   ├── utils/          # Utility module tests
│   └── validation/     # Validation rule tests
├── integration/       # Integration tests - test interactions between components
│   └── test_cli.py    # CLI integration tests
└── e2e/              # End-to-end tests - full user workflow simulations
    ├── test_cli.py          # CLI command tests
    ├── test_distribution.py # Package distribution tests
    ├── test_package.py      # Package structure tests
    └── test_templates.py    # Template rendering tests
```

## Test Types

### Unit Tests (`tests/unit/`)
Fast, isolated tests that verify individual functions, classes, or modules work correctly.

**Run only unit tests:**
```bash
pytest tests/unit/ -v
```

### Integration Tests (`tests/integration/`)
Tests that verify multiple components work together correctly.

**Run only integration tests:**
```bash
pytest tests/integration/ -v -m integration
```

### End-to-End Tests (`tests/e2e/`)
Comprehensive tests that simulate real user workflows and verify the entire system works correctly from the user's perspective.

**Run only e2e tests:**
```bash
pytest tests/e2e/ -v -m e2e
```

## Running Tests

**Run all tests:**
```bash
make test
# or
pytest tests/ -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=dom --cov-report=html
```

**Run specific test categories:**
```bash
# Only fast unit tests
pytest tests/unit/ -v

# Only slow e2e tests  
pytest tests/e2e/ -v -m e2e

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Test Markers

Tests are marked with pytest markers for selective execution:
- `@pytest.mark.unit` - Unit tests (fast)
- `@pytest.mark.integration` - Integration tests (moderate)
- `@pytest.mark.e2e` - End-to-end tests (slow)
- `@pytest.mark.slow` - Slow tests (can be skipped with `-m "not slow"`)

## Best Practices

1. **Unit tests** should be fast (<10ms each) and have no external dependencies
2. **Integration tests** can be slower but should still run locally without external services
3. **E2E tests** should simulate real user scenarios and catch issues that unit tests miss
4. All tests should be deterministic and not depend on execution order
5. Use fixtures from `conftest.py` for common test setup
