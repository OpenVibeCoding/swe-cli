"""Test the new rich output formatters."""

from rich.console import Console

from swecli.ui.formatters import OutputFormatter


def test_write_file_formatter():
    """Test write_file formatter."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 1: write_file (Success)")
    print("=" * 60 + "\n")

    tool_args = {
        "file_path": "test.py",
        "content": """def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")

if __name__ == "__main__":
    hello()
    goodbye()
""",
    }

    result = {
        "success": True,
        "output": "File created successfully",
    }

    panel = formatter.format_tool_result("write_file", tool_args, result)
    console.print(panel)


def test_bash_execute_formatter():
    """Test bash_execute formatter."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 2: bash_execute (Success)")
    print("=" * 60 + "\n")

    tool_args = {
        "command": "ls -la",
    }

    result = {
        "success": True,
        "output": """total 120
drwxr-xr-x  15 user  staff   480 Jan  1 12:00 .
drwxr-xr-x   3 user  staff    96 Jan  1 11:00 ..
-rw-r--r--   1 user  staff  1234 Jan  1 12:00 README.md
-rw-r--r--   1 user  staff   456 Jan  1 12:00 setup.py
drwxr-xr-x   5 user  staff   160 Jan  1 12:00 opencli
""",
    }

    panel = formatter.format_tool_result("bash_execute", tool_args, result)
    console.print(panel)


def test_edit_file_formatter():
    """Test edit_file formatter."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 3: edit_file (Success)")
    print("=" * 60 + "\n")

    tool_args = {
        "file_path": "main.py",
        "old_string": 'print("Hello")',
        "new_string": 'print("Hello, World!")',
    }

    result = {
        "success": True,
        "output": "Successfully replaced 1 occurrence",
    }

    panel = formatter.format_tool_result("edit_file", tool_args, result)
    console.print(panel)


def test_read_file_formatter():
    """Test read_file formatter."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 4: read_file (Success)")
    print("=" * 60 + "\n")

    tool_args = {
        "file_path": "config.json",
    }

    result = {
        "success": True,
        "output": """{
  "name": "SWE-CLI",
  "version": "1.0.0",
  "description": "AI-powered CLI",
  "model": "accounts/fireworks/models/glm-4p5"
}""",
    }

    panel = formatter.format_tool_result("read_file", tool_args, result)
    console.print(panel)


def test_error_formatter():
    """Test error formatting."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 5: write_file (Error)")
    print("=" * 60 + "\n")

    tool_args = {
        "file_path": "/root/protected.txt",
        "content": "test",
    }

    result = {
        "success": False,
        "error": "Permission denied: Cannot write to /root/protected.txt",
    }

    panel = formatter.format_tool_result("write_file", tool_args, result)
    console.print(panel)


def test_list_directory_formatter():
    """Test list_directory formatter."""
    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 60)
    print("Test 6: list_directory (Success)")
    print("=" * 60 + "\n")

    tool_args = {
        "path": "opencli/",
    }

    # Structured JSON output
    result = {
        "success": True,
        "output": """[
  {"name": "__init__.py", "is_dir": false},
  {"name": "repl", "is_dir": true},
  {"name": "core", "is_dir": true},
  {"name": "tools", "is_dir": true},
  {"name": "ui", "is_dir": true},
  {"name": "models", "is_dir": true}
]""",
    }

    panel = formatter.format_tool_result("list_directory", tool_args, result)
    console.print(panel)


def test_all():
    """Run all tests."""
    console = Console()

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Rich Output Formatters - Test Suite[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    test_write_file_formatter()
    test_bash_execute_formatter()
    test_edit_file_formatter()
    test_read_file_formatter()
    test_error_formatter()
    test_list_directory_formatter()

    console.print("\n[bold green]✅ All formatter tests completed![/bold green]\n")
    console.print("[dim]Notice the improvements:[/dim]")
    console.print("[dim]  • Rich panels with borders[/dim]")
    console.print("[dim]  • Tool icons (📝, ⚡, 📖, etc.)[/dim]")
    console.print("[dim]  • Status icons (✓, ✗)[/dim]")
    console.print("[dim]  • Syntax highlighting for code[/dim]")
    console.print("[dim]  • File size and line count[/dim]")
    console.print("[dim]  • Tree view for directories[/dim]")
    console.print("[dim]  • Color-coded success/error states[/dim]\n")


if __name__ == "__main__":
    test_all()
