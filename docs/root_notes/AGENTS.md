# Repository Guidelines

## Project Structure & Module Organization
`swecli/` houses the runtime logic; `swecli/cli.py` is the entrypoint published via `project.scripts`. Subpackages `core/` provide agent orchestration (factories, services, config), `commands/` define CLI verbs, `ui/` handles Rich-driven output, and `tools/` plus `github_issue_resolve/` contain service integrations. Tests live in `tests/`, mirroring package modules. Documentation and demos sit in `docs/`, `_archived_docs/`, and `demo_video/`; keep generated assets out of version control.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` to isolate dependencies.
- `pip install -e .[dev]` installs runtime plus lint/test tooling.
- `swecli --help` sanity-checks the CLI wiring from local changes.
- `pytest` runs all unit and async tests in `tests/`.
- `ruff check swecli tests` enforces lint rules; add `--fix` for safe autofixes.
- `black swecli tests` formats with 100-column width; append `--check` for CI parity.
- `mypy swecli` validates the strict type contracts expected in `core/` services.

## Coding Style & Naming Conventions
Follow Black/Ruff defaults: 4-space indentation, double quotes preferred, imports grouped stdlib/third-party/local. Use snake_case for functions and modules, PascalCase for classes, and ALL_CAPS for constants. Provide type hints on public APIs; prefer dataclasses or Pydantic models for structured payloads. Keep CLI option names kebab-case to match existing commands.

## Testing Guidelines
Write tests beside matching modules (e.g., `tests/core/test_management.py`). Name files `test_<area>.py` and functions `test_<behavior>` for pytest auto-discovery. Use `pytest.mark.asyncio` for async flows and fixtures under `tests/conftest.py`. Target coverage of new logic and fail fast on regressions before opening PRs.

## Commit & Pull Request Guidelines
Keep commits atomic with present-tense imperative subjects (`add stats command output`). Reference related issues in the body when applicable and avoid bundling formatting churn with logic. PRs should include: a concise summary, reproduction or verification steps, screenshots for UI/Rich output, and confirmation that lint, type check, and tests passed.

## Agent-Specific Tips
Configuration lives under `swecli/core/config`; prefer `.env` files for secrets and load via the existing config helpers. When extending agents or tools, wire new implementations through the factory modules in `swecli/core/factories` so discoverability remains consistent.
