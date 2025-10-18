Commands:
```bash
# Run single test
python -m pytest tests/test_context_compaction.py::test_specific_function -v
python -m pytest _archived_tests/test_chat_app.py -v

# Lint/format
ruff check . --fix
ruff format .
black swecli/
mypy swecli/ --strict

# Build & install
pip install -e .
python -m build  # requires: pip install build

# Dev setup
pip install -r requirements.txt
pip install -e ".[dev]"
```

Style:
- Python 3.9+ with modern typing
- 100-char line limit (black+ruff)
- Use `Path` from pathlib instead of strings
- Prefer dataclasses over dicts for config
- Use rich.panel.Panel, rich.console.Console for UI
- Import: `from typing import Any, Dict, List, Optional, Union`
- Error handling with try/except + rich traceback display
- Async functions marked with `async def` and `await`
- Classes use PascalCase, functions use snake_case
- Use Pydantic for models with Field(...)
- No print() - use console.print() for styled output