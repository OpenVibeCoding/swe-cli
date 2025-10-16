# OpenCLI Agent Guidelines

## Commands
- **Build**: `pip install -e .`
- **Lint**: `ruff check .` and `black --check .`
- **Typecheck**: `mypy .`
- **Test single**: `pytest tests/test_file.py::test_name`
- **Test all**: `pytest`

## Code Style
- **Line length**: 100 characters
- **Python**: >=3.9, strict typing with mypy
- **Imports**: Group standard library, third-party, local
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: Use specific exceptions, avoid bare except
- **Formatting**: Black formatter, ruff linter
- **Docstrings**: Google-style with Args/Returns sections