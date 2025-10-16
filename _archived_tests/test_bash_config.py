#!/usr/bin/env python3
"""Test that bash execution is enabled in chat REPL configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.core.management import ConfigManager
from opencli.core.management import SessionManager
from opencli.repl.repl_chat import create_repl_chat

def test_bash_enabled():
    """Test that bash execution is enabled after chat REPL initialization."""
    print("Testing bash execution configuration...")

    # Create config and session managers
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Initialize session
    session_dir = Path(config.session_dir).expanduser()
    session_manager = SessionManager(session_dir)
    session_manager.create_session(working_directory=str(Path.cwd()))

    # Create chat REPL
    chat_repl = create_repl_chat(config_manager, session_manager)

    # Check if bash is enabled
    repl = chat_repl.repl
    config = repl.config

    # Check various possible config structures
    bash_enabled = False
    config_location = None

    if hasattr(config, 'permissions') and hasattr(config.permissions, 'bash'):
        bash_enabled = config.permissions.bash.enabled
        config_location = 'config.permissions.bash.enabled'
    elif hasattr(config, 'enable_bash'):
        bash_enabled = config.enable_bash
        config_location = 'config.enable_bash'
    else:
        print("❌ Could not find bash configuration!")
        return False

    print(f"\nBash configuration location: {config_location}")
    print(f"Bash enabled: {bash_enabled}")

    if bash_enabled:
        print("✅ SUCCESS: Bash execution is enabled!")

        # Try to get bash tool and check if it will allow execution
        try:
            bash_tool = repl.tool_registry.bash_tool
            print(f"\nBash tool found: {bash_tool.__class__.__name__}")
            print(f"Bash tool config.permissions.bash.enabled: {bash_tool.config.permissions.bash.enabled}")

            # Try a simple validation
            can_execute = bash_tool.config.permissions.bash.enabled
            if can_execute:
                print("✅ Bash tool is configured to allow execution")
            else:
                print("❌ Bash tool config still shows disabled")

        except Exception as e:
            print(f"⚠ Could not check bash tool: {e}")

        return True
    else:
        print("❌ FAILED: Bash execution is still disabled!")
        return False

if __name__ == "__main__":
    try:
        success = test_bash_enabled()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
