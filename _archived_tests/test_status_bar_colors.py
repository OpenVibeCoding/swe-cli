#!/usr/bin/env python3
"""Test status bar color changes when toggling modes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.core.management import ConfigManager
from opencli.core.management import SessionManager
from opencli.repl.repl_chat import create_repl_chat

def main():
    """Test status bar with mode toggling."""
    print("Testing status bar colors...")
    print("=" * 60)
    print()
    print("The status bar should show:")
    print("- [NORMAL] in ORANGE when in normal mode")
    print("- [PLAN] in LIGHT GREEN when in plan mode")
    print()
    print("Press Shift+Tab to toggle between modes")
    print("The color of [MODE] should change each time you toggle")
    print()
    print("=" * 60)
    print()

    # Create config and session managers
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Initialize session
    session_dir = Path(config.session_dir).expanduser()
    session_manager = SessionManager(session_dir)
    session_manager.create_session(working_directory=str(Path.cwd()))

    # Create chat REPL
    chat_repl = create_repl_chat(config_manager, session_manager)

    print("Starting OpenCLI...")
    print("Watch the status bar at the bottom!")
    print()

    # Run the application
    chat_repl.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
