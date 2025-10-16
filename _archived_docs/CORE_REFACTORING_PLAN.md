
## Phase 8 Progress (Utilities & Cleanup)
- Relocated the action summarizer into `opencli/core/utils/` with compatibility stubs, completing the core directory reorganisation
- Verified CLI entrypoint and targeted pytest suite still pass after the migration
- All top-level core modules now either represent cohesive packages or compatibility wrappers for their new structure

## Phase 9 Progress (Session Continuation)
- Extended `SessionMetadata`/`SessionManager` to track working directories and locate the most recent session per repo
- Added `opencli --continue` to resume the latest session for the current repository with guard rails against missing sessions or conflicting flags
- Expanded automated coverage (`tests/test_session_manager.py`) alongside existing CLI tests to validate the new session lookup helpers

## Phase 10 Progress (Session Commands)
- Added `--list-sessions` and `--continue` to the CLI; continue resumes the latest session in the current repo, listing provides a rich table of saved sessions
- `SessionManager` now tracks working directories and exposes helpers to find/load the latest session for a path
- REPL `/resume` command defaults to the latest session when no ID is supplied
- Added tests covering session lookup helpers and the new resume behaviour (`tests/test_session_manager.py`, `tests/test_session_commands.py`)
