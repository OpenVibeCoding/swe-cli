"""Simple test script for command handlers integration (no MCP)."""

import sys
from pathlib import Path
from rich.console import Console

# Test imports
print("Testing command handler imports...")
try:
    from opencli.repl.commands import (
        SessionCommands,
        FileCommands,
        ModeCommands,
        HelpCommand,
        CommandResult,
    )
    print("✓ All command handlers imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test instantiation (without MCP)
print("\nTesting command handler instantiation...")
try:
    from opencli.core.management import (
        ConfigManager,
        SessionManager,
        ModeManager,
        UndoManager,
    )
    from opencli.core.approval import ApprovalManager
    from opencli.tools.file_ops import FileOperations

    console = Console()

    # Create minimal instances for testing
    config_manager = ConfigManager(working_dir=Path.cwd())
    session_manager = SessionManager(session_dir=Path.home() / ".opencli" / "sessions")
    mode_manager = ModeManager()
    undo_manager = UndoManager(max_history=100)
    approval_manager = ApprovalManager(console)
    file_ops = FileOperations(config_manager.get_config(), Path.cwd())

    # Test SessionCommands
    session_commands = SessionCommands(console, session_manager, config_manager)
    print("✓ SessionCommands instantiated")

    # Test FileCommands
    file_commands = FileCommands(console, file_ops)
    print("✓ FileCommands instantiated")

    # Test ModeCommands
    mode_commands = ModeCommands(console, mode_manager, undo_manager, approval_manager)
    print("✓ ModeCommands instantiated")

    # Test HelpCommand
    help_command = HelpCommand(console, mode_manager)
    print("✓ HelpCommand instantiated")

except Exception as e:
    print(f"✗ Instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test basic functionality
print("\nTesting basic command functionality...")
try:
    # Test help command
    result = help_command.handle("")
    assert result.success, "Help command should succeed"
    print("✓ HelpCommand.handle() works")

    # Test mode switch (show current)
    result = mode_commands.switch_mode("")
    assert result.success, "Mode command with no args should show current mode"
    print("✓ ModeCommands.switch_mode() works")

    # Test mode switch (to plan)
    result = mode_commands.switch_mode("plan")
    assert result.success, "Mode command should switch to plan mode"
    assert result.data.value == "plan", "Should return plan mode"
    print("✓ ModeCommands.switch_mode('plan') works")

    # Test mode switch (back to normal)
    result = mode_commands.switch_mode("normal")
    assert result.success, "Mode command should switch to normal mode"
    assert result.data.value == "normal", "Should return normal mode"
    print("✓ ModeCommands.switch_mode('normal') works")

    # Test file tree (with current directory)
    result = file_commands.show_tree(".")
    assert result.success, "Tree command should succeed"
    print("✓ FileCommands.show_tree('.') works")

    # Test session list
    result = session_commands.list_sessions()
    assert result.success, "List sessions should succeed (even if empty)"
    print("✓ SessionCommands.list_sessions() works")

    print("\n✅ All tests passed! Command handlers are working correctly.")
    print("\nNext steps:")
    print("  • Old methods in repl.py can now be removed")
    print("  • This will reduce repl.py by ~400 lines")
    print("  • Test with actual REPL to ensure everything works end-to-end")

except Exception as e:
    print(f"✗ Functionality test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
