# DOMjudge CLI

Modern CLI tool for managing DOMjudge contests and infrastructure.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (installed automatically)

## Setup

```bash
git clone <repo>
cd domjudge-cli
make setup
```

That's it. Everything is installed.

## Development

```bash
make format      # Format code
make lint        # Run linters
make typecheck   # Type check
make test        # Run tests
make check       # Run everything
```

## Usage

```bash
dom --help
```

## Project Structure

```
dom/
├── cli/            # CLI commands
├── core/           # Business logic
├── infrastructure/ # External integrations
├── types/          # Type definitions
└── utils/          # Utilities
```

## Tools

- **uv** - Fast package management
- **ruff** - Linting
- **black** - Formatting
- **mypy** - Type checking
- **pytest** - Testing
- **pre-commit** - Git hooks

## CI/CD

- **CI**: Runs on every PR (lint, test, type-check)
- **Publish**: Automatic on GitHub releases

## Contributing

1. `make setup`
2. Make changes
3. `make check`
4. Commit (hooks run automatically)
5. Push

Code must pass: format check, lint, type check, and tests.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## License

MIT
