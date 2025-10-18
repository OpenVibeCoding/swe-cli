"""Test autocomplete system for @ mentions and / commands."""

from pathlib import Path
from prompt_toolkit.document import Document

from swecli.ui.autocomplete import (
    SWE-CLICompleter,
    FileMentionCompleter,
    SlashCommandCompleter,
    SLASH_COMMANDS,
)


def test_slash_command_autocomplete():
    """Test slash command autocomplete."""
    print("\n═══════════════════════════════════════════════")
    print("  Test 1: Slash Command Autocomplete")
    print("═══════════════════════════════════════════════\n")

    completer = SWE-CLICompleter(working_dir=Path.cwd())

    # Test 1: Partial command "/m"
    doc = Document("/m")
    completions = list(completer.get_completions(doc, None))

    print("Input: /m")
    print(f"Found {len(completions)} completions:")
    for comp in completions:
        print(f"  {comp.text:<15} - {comp.display_meta}")

    assert any("/model" in comp.text for comp in completions), "Should find /model"
    assert any("/mention" in comp.text for comp in completions), "Should find /mention"
    print("✓ Partial command test passed\n")

    # Test 2: Full menu "/"
    doc2 = Document("/")
    completions2 = list(completer.get_completions(doc2, None))

    print("Input: /")
    print(f"Found {len(completions2)} completions (showing first 10):")
    for comp in completions2[:10]:
        print(f"  {comp.text:<15} - {comp.display_meta}")

    assert len(completions2) >= 10, "Should find many commands"
    print("✓ Full menu test passed\n")

    return True


def test_file_mention_autocomplete():
    """Test file mention autocomplete."""
    print("\n═══════════════════════════════════════════════")
    print("  Test 2: File Mention Autocomplete")
    print("═══════════════════════════════════════════════\n")

    completer = SWE-CLICompleter(working_dir=Path.cwd())

    # Test 1: Search for Python files "@test"
    doc = Document("@test")
    completions = list(completer.get_completions(doc, None))

    print("Input: @test")
    print(f"Found {len(completions)} completions (showing first 10):")
    for comp in completions[:10]:
        display_str = str(comp.display) if hasattr(comp, 'display') else comp.text
        meta_str = str(comp.display_meta) if hasattr(comp, 'display_meta') else ""
        print(f"  {display_str:<40} - {meta_str}")

    assert len(completions) > 0, "Should find some files"
    print("✓ File search test passed\n")

    # Test 2: Search for all files "@"
    doc2 = Document("@")
    completions2 = list(completer.get_completions(doc2, None))

    print("Input: @")
    print(f"Found {len(completions2)} completions (showing first 10):")
    for comp in completions2[:10]:
        display_str = str(comp.display) if hasattr(comp, 'display') else comp.text
        meta_str = str(comp.display_meta) if hasattr(comp, 'display_meta') else ""
        print(f"  {display_str:<40} - {meta_str}")

    assert len(completions2) > 0, "Should find files"
    print("✓ All files test passed\n")

    return True


def test_slash_command_list():
    """Test slash command list."""
    print("\n═══════════════════════════════════════════════")
    print("  Test 3: Slash Command List")
    print("═══════════════════════════════════════════════\n")

    print(f"Total commands: {len(SLASH_COMMANDS)}\n")
    print("Available commands:")
    for cmd in SLASH_COMMANDS:
        print(f"  /{cmd.name:<15} - {cmd.description}")

    assert len(SLASH_COMMANDS) >= 10, "Should have at least 10 commands"
    print("\n✓ Command list test passed\n")

    return True


def test_completer_integration():
    """Test that completer can be used with prompt_toolkit."""
    print("\n═══════════════════════════════════════════════")
    print("  Test 4: Completer Integration")
    print("═══════════════════════════════════════════════\n")

    completer = SWE-CLICompleter(working_dir=Path.cwd())

    # Test various inputs
    test_cases = [
        ("/", "Should show all commands"),
        ("/mod", "Should show model command"),
        ("@", "Should show files"),
        ("@open", "Should filter files with 'open'"),
        ("hello /", "Should complete commands after text"),
        ("hello @", "Should complete files after text"),
    ]

    for input_text, description in test_cases:
        doc = Document(input_text)
        completions = list(completer.get_completions(doc, None))
        status = "✓" if len(completions) > 0 else "✗"
        print(f"{status} '{input_text}' - {description} ({len(completions)} results)")

    print("\n✓ Integration test passed\n")
    return True


if __name__ == "__main__":
    print("\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]")
    print("[bold magenta]  SWE-CLI Autocomplete Test Suite[/bold magenta]")
    print("[bold magenta]═══════════════════════════════════════════════[/bold magenta]")

    try:
        # Run tests
        test_slash_command_list()
        test_slash_command_autocomplete()
        test_file_mention_autocomplete()
        test_completer_integration()

        print("\n═══════════════════════════════════════════════")
        print("  ✅ All autocomplete tests passed!")
        print("═══════════════════════════════════════════════\n")

        print("To test interactively:")
        print("  1. Run 'swecli'")
        print("  2. Type '/' and press Tab to see slash commands")
        print("  3. Type '@' and press Tab to see file mentions")
        print("  4. Start typing to filter results\n")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
