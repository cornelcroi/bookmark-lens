# Contributing to bookmark-lens

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bookmark-lens.git
cd bookmark-lens
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
python tests/test_simple.py
```

Or with pytest:
```bash
pytest tests/test_integration.py -v
```

## Code Style

We use:
- **black** for code formatting
- **ruff** for linting
- **mypy** for type checking

Run before committing:
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)

## Questions?

Feel free to open a discussion on GitHub or reach out via issues.
