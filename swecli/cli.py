"""Command-line interface entry point for SWE-CLI."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from swecli.core.approval import ApprovalManager
from swecli.core.management import ConfigManager, ModeManager, OperationMode, SessionManager, UndoManager
from swecli.core.services import RuntimeService
from swecli.models.agent_deps import AgentDependencies
from swecli.models.message import ChatMessage, Role
from swecli.repl.repl import REPL
from swecli.repl.repl_chat import create_repl_chat
from swecli.setup import run_setup_wizard
from swecli.setup.wizard import config_exists
from swecli.tools.bash_tool import BashTool
from swecli.tools.edit_tool import EditTool
from swecli.tools.file_ops import FileOperations
from swecli.tools.web_fetch_tool import WebFetchTool
from swecli.tools.vlm_tool import VLMTool
from swecli.tools.web_screenshot_tool import WebScreenshotTool
from swecli.tools.write_tool import WriteTool


def main() -> None:
    """Main entry point for SWE-CLI CLI."""
    import sys

    # Clear terminal IMMEDIATELY at entry point before any other output
    # This prevents shell prompt from bleeding into the TUI
    sys.stdout.write("\033[3J")  # Clear scrollback buffer
    sys.stdout.write("\033[2J")  # Clear screen
    sys.stdout.write("\033[H")   # Move cursor to home
    sys.stdout.flush()

    parser = argparse.ArgumentParser(
        prog="swecli",
        description="SWE-CLI - AI-powered command-line tool for accelerated development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  swecli                          # Start interactive session (web server in background)
  swecli run ui                   # Start web UI dev server and open browser
  swecli -p "create hello.py"     # Non-interactive mode
  swecli -r abc123                # Resume session
  swecli --ui-port 3000           # Web UI on custom port
  swecli mcp list                 # List MCP servers
  swecli mcp add myserver uvx mcp-server-example
        """
    )

    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="SWE-CLI 0.1.0",
    )

    parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION_ID",
        help="Resume a previous session by ID",
    )

    parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Resume the most recent session for the current repository",
    )

    parser.add_argument(
        "--working-dir",
        "-d",
        metavar="PATH",
        help="Set working directory (defaults to current directory)",
    )

    parser.add_argument(
        "--prompt",
        "-p",
        metavar="TEXT",
        help="Execute a single prompt and exit (non-interactive mode)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logging",
    )

    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List saved sessions and exit",
    )

    parser.add_argument(
        "--ui-port",
        type=int,
        default=8080,
        metavar="PORT",
        help="Port for web UI server (default: 8080)",
    )

    parser.add_argument(
        "--ui-host",
        default="127.0.0.1",
        metavar="HOST",
        help="Host for web UI server (default: 127.0.0.1)",
    )

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Manage SWE-CLI configuration",
        description="Configure AI providers, models, and other settings",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Config operations")

    # config setup
    config_subparsers.add_parser(
        "setup",
        help="Run the interactive setup wizard"
    )

    # config show
    config_subparsers.add_parser(
        "show",
        help="Display current configuration"
    )

    # MCP subcommand
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Configure and manage MCP (Model Context Protocol) servers",
        description="Manage MCP servers for extending SWE-CLI with external tools and capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  swecli mcp list                                    # List all servers
  swecli mcp add myserver uvx mcp-server-sqlite      # Add SQLite MCP server
  swecli mcp add custom node server.js arg1 arg2     # Add custom server with args
  swecli mcp add api python api.py --env API_KEY=xyz # Add with environment variable
  swecli mcp get myserver                            # Show server details
  swecli mcp enable myserver                         # Enable a server
  swecli mcp remove myserver                         # Remove a server
        """
    )
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", help="MCP operations")

    # mcp list
    mcp_subparsers.add_parser(
        "list",
        help="List all configured MCP servers with their status"
    )

    # mcp get
    mcp_get = mcp_subparsers.add_parser(
        "get",
        help="Show detailed information about a specific MCP server"
    )
    mcp_get.add_argument("name", help="Name of the MCP server")

    # mcp add
    mcp_add = mcp_subparsers.add_parser(
        "add",
        help="Add a new MCP server to the configuration",
        description="Register a new MCP server that will be available to SWE-CLI"
    )
    mcp_add.add_argument("name", help="Unique name for the server")
    mcp_add.add_argument("command", help="Command to start the MCP server (e.g., 'uvx', 'node', 'python')")
    mcp_add.add_argument("args", nargs="*", help="Arguments to pass to the command")
    mcp_add.add_argument(
        "--env",
        nargs="*",
        metavar="KEY=VALUE",
        help="Environment variables for the server (e.g., API_KEY=xyz TOKEN=abc)"
    )
    mcp_add.add_argument(
        "--no-auto-start",
        action="store_true",
        help="Don't automatically start this server when SWE-CLI launches"
    )

    # mcp remove
    mcp_remove = mcp_subparsers.add_parser(
        "remove",
        help="Remove an MCP server from the configuration"
    )
    mcp_remove.add_argument("name", help="Name of the server to remove")

    # mcp enable
    mcp_enable = mcp_subparsers.add_parser(
        "enable",
        help="Enable an MCP server (will auto-start if configured)"
    )
    mcp_enable.add_argument("name", help="Name of the server to enable")

    # mcp disable
    mcp_disable = mcp_subparsers.add_parser(
        "disable",
        help="Disable an MCP server (won't auto-start)"
    )
    mcp_disable.add_argument("name", help="Name of the server to disable")

    # Run subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Run development tools",
        description="Run development servers and tools"
    )
    run_subparsers = run_parser.add_subparsers(dest="run_command", help="Run operations")

    # run ui
    run_subparsers.add_parser(
        "ui",
        help="Start the web UI development server (Vite) and open in browser"
    )

    args = parser.parse_args()

    # Handle config commands
    if args.command == "config":
        _handle_config_command(args)
        return

    # Handle MCP commands
    if args.command == "mcp":
        _handle_mcp_command(args)
        return

    # Handle run commands
    if args.command == "run":
        _handle_run_command(args)
        return

    console = Console()

    # Run setup wizard if config doesn't exist
    if not config_exists():
        if not run_setup_wizard():
            console.print("[yellow]Setup cancelled. Exiting.[/yellow]")
            sys.exit(0)

    # Set working directory
    working_dir = Path(args.working_dir) if args.working_dir else Path.cwd()
    if not working_dir.exists():
        console.print(f"[red]Error: Working directory does not exist: {working_dir}[/red]")
        sys.exit(1)

    try:
        # Initialize managers
        config_manager = ConfigManager(working_dir)
        config = config_manager.load_config()

        # Override verbose if specified
        if args.verbose:
            config.verbose = True

        # Ensure directories exist
        config_manager.ensure_directories()

        # Initialize session manager
        session_dir = Path(config.session_dir).expanduser()
        session_manager = SessionManager(session_dir)

        if args.list_sessions:
            _print_sessions(console, session_manager)
            return

        if args.resume and args.continue_session:
            console.print("[red]Error: Use either --resume or --continue, not both[/red]")
            sys.exit(1)

        resume_id = args.resume
        if args.continue_session and not resume_id:
            latest = session_manager.find_latest_session(working_dir)
            if not latest:
                console.print("[yellow]No previous session found for this repository[/yellow]")
                sys.exit(1)
            resume_id = latest.id
            console.print(f"[green]Continuing session {resume_id}[/green]")

        resumed_session = None
        if resume_id:
            try:
                resumed_session = session_manager.load_session(resume_id)
            except FileNotFoundError:
                console.print(f"[red]Error: Session {resume_id} not found[/red]")
                sys.exit(1)

        if resumed_session and resumed_session.working_directory:
            resolved = Path(resumed_session.working_directory).expanduser()
            if resolved != working_dir:
                working_dir = resolved
                config_manager = ConfigManager(working_dir)
                config = config_manager.load_config()
                config_manager.ensure_directories()
                session_dir = Path(config.session_dir).expanduser()
                session_manager = SessionManager(session_dir)
                session_manager.load_session(resume_id)
        elif not resume_id:
            session_manager.create_session(working_directory=str(working_dir))

        # Non-interactive mode
        if args.prompt:
            _run_non_interactive(config_manager, session_manager, args.prompt)
            return

        # Start web UI automatically (silently in background)
        web_server_thread = None
        mode_manager = ModeManager()
        approval_manager = ApprovalManager(console)
        undo_manager = UndoManager(config.max_undo_history)

        try:
            from swecli.web import start_server

            web_server_thread = start_server(
                config_manager=config_manager,
                session_manager=session_manager,
                mode_manager=mode_manager,
                approval_manager=approval_manager,
                undo_manager=undo_manager,
                host=args.ui_host,
                port=args.ui_port,
                open_browser=False,
            )

            # Small delay to ensure server is ready
            import time
            time.sleep(0.3)

        except ImportError:
            # Silently ignore if web dependencies not installed
            pass
        except Exception:
            # Silently ignore web server startup errors
            pass

        # Interactive REPL mode with chat UI
        # Check if continuing/resuming a session
        is_continuation = bool(args.resume or args.continue_session)
        chat_app = create_repl_chat(config_manager, session_manager, is_continuation=is_continuation)
        chat_app.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def _print_sessions(console: Console, session_manager: SessionManager) -> None:
    """Display saved sessions."""
    sessions = session_manager.list_sessions()

    if not sessions:
        console.print("[yellow]No saved sessions found.[/yellow]")
        return

    from itertools import groupby
    from operator import attrgetter
    from rich.table import Table

    sessions = [
        meta
        for meta in sessions
        if not (meta.message_count == 0 and meta.total_tokens == 0)
    ]

    if not sessions:
        console.print("[yellow]No completed sessions found.[/yellow]")
        return

    sessions.sort(key=lambda m: (m.working_directory or "", m.updated_at), reverse=True)

    for directory, items in groupby(sessions, key=attrgetter("working_directory")):
        dir_label = directory or "(unknown directory)"
        table = Table(
            title=f"Sessions for {dir_label}",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("ID", style="cyan")
        table.add_column("Updated")
        table.add_column("Messages", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Summary")

        for meta in list(items)[:5]:
            updated = meta.updated_at.strftime("%Y-%m-%d %H:%M")
            summary = meta.summary or "—"
            table.add_row(
                meta.id,
                updated,
                str(meta.message_count),
                str(meta.total_tokens),
                summary,
            )

        console.print(table)


def _handle_config_command(args) -> None:
    """Handle config subcommands.

    Args:
        args: Parsed command-line arguments
    """
    import json
    from pathlib import Path

    console = Console()

    if not args.config_command:
        console.print("[yellow]No config subcommand specified. Use --help for available commands.[/yellow]")
        sys.exit(1)

    if args.config_command == "setup":
        # Run setup wizard (can be used to reconfigure)
        if not run_setup_wizard():
            console.print("[yellow]Setup cancelled.[/yellow]")
            sys.exit(0)

    elif args.config_command == "show":
        # Display current configuration
        config_file = Path.home() / ".swecli" / "settings.json"

        if not config_file.exists():
            console.print("[yellow]No configuration found. Run 'swecli config setup' first.[/yellow]")
            sys.exit(1)

        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            from rich.table import Table

            table = Table(title="Current Configuration", show_header=True, header_style="bold cyan")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")

            # Display non-sensitive config values
            for key, value in config.items():
                if key == "api_key":
                    # Mask API key
                    if value:
                        masked = value[:8] + "*" * (len(value) - 12) + value[-4:] if len(value) > 12 else "*" * len(value)
                        table.add_row(key, masked)
                    else:
                        table.add_row(key, "[dim]Not set[/dim]")
                else:
                    table.add_row(key, str(value))

            console.print()
            console.print(table)
            console.print()
            console.print(f"[dim]Config file: {config_file}[/dim]")

        except json.JSONDecodeError:
            console.print(f"[red]Error: Invalid JSON in configuration file: {config_file}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error reading configuration: {e}[/red]")
            sys.exit(1)


def _handle_mcp_command(args) -> None:
    """Handle MCP subcommands.

    Args:
        args: Parsed command-line arguments
    """
    from swecli.mcp.manager import MCPManager
    from swecli.mcp.models import MCPServerConfig
    from rich.table import Table

    console = Console()
    mcp_manager = MCPManager()

    if not args.mcp_command:
        console.print("[yellow]No MCP subcommand specified. Use --help for available commands.[/yellow]")
        sys.exit(1)

    try:
        if args.mcp_command == "list":
            servers = mcp_manager.list_servers()

            if not servers:
                console.print("[yellow]No MCP servers configured[/yellow]")
                return

            table = Table(title="MCP Servers", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan")
            table.add_column("Command")
            table.add_column("Enabled", justify="center")
            table.add_column("Auto-start", justify="center")

            for name, config in servers.items():
                enabled = "[green]✓[/green]" if config.enabled else "[red]✗[/red]"
                auto_start = "[green]✓[/green]" if config.auto_start else "[dim]-[/dim]"
                command = f"{config.command} {' '.join(config.args[:2])}" if config.args else config.command
                if len(command) > 60:
                    command = command[:57] + "..."

                table.add_row(name, command, enabled, auto_start)

            console.print(table)

        elif args.mcp_command == "get":
            servers = mcp_manager.list_servers()
            if args.name not in servers:
                console.print(f"[red]Error: Server '{args.name}' not found[/red]")
                sys.exit(1)

            config = servers[args.name]
            console.print(f"\n[bold cyan]{args.name}[/bold cyan]\n")
            console.print(f"Command: {config.command}")
            if config.args:
                console.print(f"Args: {' '.join(config.args)}")
            if config.env:
                console.print("Environment variables:")
                for key, value in config.env.items():
                    console.print(f"  {key}={value}")
            console.print(f"Enabled: {'Yes' if config.enabled else 'No'}")
            console.print(f"Auto-start: {'Yes' if config.auto_start else 'No'}")
            console.print(f"Transport: {config.transport}")

        elif args.mcp_command == "add":
            # Parse environment variables
            env = {}
            if args.env:
                for env_var in args.env:
                    if "=" not in env_var:
                        console.print(f"[red]Error: Invalid environment variable format: {env_var}[/red]")
                        console.print("Use KEY=VALUE format")
                        sys.exit(1)
                    key, value = env_var.split("=", 1)
                    env[key] = value

            mcp_manager.add_server(
                name=args.name,
                command=args.command,
                args=args.args or [],
                env=env
            )

            # Update auto_start if specified
            if args.no_auto_start:
                config = mcp_manager.get_config()
                config.mcp_servers[args.name].auto_start = False
                from swecli.mcp.config import save_config
                save_config(config)

            console.print(f"[green]✓[/green] Added MCP server '{args.name}'")

        elif args.mcp_command == "remove":
            success = mcp_manager.remove_server(args.name)
            if success:
                console.print(f"[green]✓[/green] Removed MCP server '{args.name}'")
            else:
                console.print(f"[red]Error: Server '{args.name}' not found[/red]")
                sys.exit(1)

        elif args.mcp_command == "enable":
            success = mcp_manager.enable_server(args.name)
            if success:
                console.print(f"[green]✓[/green] Enabled MCP server '{args.name}'")
            else:
                console.print(f"[red]Error: Server '{args.name}' not found[/red]")
                sys.exit(1)

        elif args.mcp_command == "disable":
            success = mcp_manager.disable_server(args.name)
            if success:
                console.print(f"[green]✓[/green] Disabled MCP server '{args.name}'")
            else:
                console.print(f"[red]Error: Server '{args.name}' not found[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


def _handle_run_command(args) -> None:
    """Handle run subcommands.

    Args:
        args: Parsed command-line arguments
    """
    import subprocess
    import webbrowser
    import time
    from pathlib import Path

    console = Console()

    if not args.run_command:
        console.print("[yellow]No run subcommand specified. Use --help for available commands.[/yellow]")
        sys.exit(1)

    if args.run_command == "ui":
        try:
            # Find the web-ui directory
            import swecli
            import os

            package_dir = Path(swecli.__file__).parent

            # Check environment variable first
            env_path = os.getenv("SWECLI_WEB_UI_PATH")
            if env_path:
                web_ui_dir = Path(env_path)
                if web_ui_dir.exists() and (web_ui_dir / "package.json").exists():
                    console.print(f"[cyan]📦 Using web-ui from SWECLI_WEB_UI_PATH: {web_ui_dir}[/cyan]")
                else:
                    console.print(f"[yellow]⚠ SWECLI_WEB_UI_PATH is set but directory is invalid: {web_ui_dir}[/yellow]")
                    web_ui_dir = None

            if not env_path or not web_ui_dir:
                # Check multiple locations
                possible_locations = [
                    # 1. Repository root (for development)
                    package_dir.parent / "web-ui",
                    # 2. Current directory (if user is in repo)
                    Path.cwd() / "web-ui",
                    # 3. Package installation directory
                    package_dir / "web-ui",
                    # 4. Check parent directories up to 3 levels
                    package_dir.parent.parent / "web-ui",
                ]

                web_ui_dir = None
                for location in possible_locations:
                    if location.exists() and (location / "package.json").exists():
                        web_ui_dir = location
                        break

                if not web_ui_dir:
                    console.print("[red]Error: web-ui directory not found[/red]")
                    console.print("\nChecked locations:")
                    for loc in possible_locations:
                        console.print(f"  • {loc}")
                    console.print("\n[yellow]Tip:[/yellow] Run this command from the swe-cli repository root,")
                    console.print("or set SWECLI_WEB_UI_PATH environment variable:")
                    console.print("[dim]  export SWECLI_WEB_UI_PATH=/path/to/swe-cli/web-ui[/dim]")
                    sys.exit(1)

            console.print(f"[cyan]📦 Found web-ui directory: {web_ui_dir}[/cyan]")

            # Check if node_modules exists
            node_modules = web_ui_dir / "node_modules"
            if not node_modules.exists():
                console.print("[yellow]⚠ node_modules not found. Running npm install...[/yellow]")
                console.print("[dim]This may take a few minutes on first run...[/dim]\n")

                # Run npm install
                install_process = subprocess.run(
                    ["npm", "install"],
                    cwd=web_ui_dir,
                    capture_output=False,
                    text=True
                )

                if install_process.returncode != 0:
                    console.print("[red]Error: npm install failed[/red]")
                    sys.exit(1)

                console.print("[green]✓ Dependencies installed successfully[/green]\n")

            # Start the dev server
            console.print("[cyan]🚀 Starting Vite dev server...[/cyan]")
            console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

            # Open browser after a short delay
            def open_browser_delayed():
                time.sleep(2)  # Wait for Vite to start
                url = "http://localhost:5173"
                console.print(f"[green]✓ Opening browser at {url}[/green]\n")
                webbrowser.open(url)

            import threading
            browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
            browser_thread.start()

            # Run npm run dev (blocking)
            subprocess.run(
                ["npm", "run", "dev"],
                cwd=web_ui_dir,
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping dev server...[/yellow]")
        except FileNotFoundError:
            console.print("[red]Error: npm not found. Please install Node.js and npm.[/red]")
            console.print("Visit: https://nodejs.org/")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            sys.exit(1)


def _run_non_interactive(
    config_manager: ConfigManager,
    session_manager: SessionManager,
    prompt: str,
) -> None:
    """Run a single prompt in non-interactive mode.

    Args:
        config_manager: Configuration manager
        session_manager: Session manager
        prompt: User prompt to execute
    """
    console = Console()
    config = config_manager.get_config()
    mode_manager = ModeManager()
    approval_manager = ApprovalManager(console)
    undo_manager = UndoManager(config.max_undo_history)

    file_ops = FileOperations(config, config_manager.working_dir)
    write_tool = WriteTool(config, config_manager.working_dir)
    edit_tool = EditTool(config, config_manager.working_dir)
    bash_tool = BashTool(config, config_manager.working_dir)
    web_fetch_tool = WebFetchTool(config, config_manager.working_dir)
    vlm_tool = VLMTool(config, config_manager.working_dir)
    web_screenshot_tool = WebScreenshotTool(config, config_manager.working_dir)

    runtime_service = RuntimeService(config_manager, mode_manager)
    runtime_suite = runtime_service.build_suite(
        file_ops=file_ops,
        write_tool=write_tool,
        edit_tool=edit_tool,
        bash_tool=bash_tool,
        web_fetch_tool=web_fetch_tool,
        vlm_tool=vlm_tool,
        web_screenshot_tool=web_screenshot_tool,
        mcp_manager=None,
    )

    agent = runtime_suite.agents.normal

    session = session_manager.get_current_session()
    if not session:
        session = session_manager.create_session(
            working_directory=str(config_manager.working_dir)
        )

    message_history = session.to_api_messages()

    deps = AgentDependencies(
        mode_manager=mode_manager,
        approval_manager=approval_manager,
        undo_manager=undo_manager,
        session_manager=session_manager,
        working_dir=config_manager.working_dir,
        console=console,
        config=config,
    )

    try:
        result = agent.run_sync(prompt, deps, message_history=message_history)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)

    if not result.get("success", False):
        error = result.get("error", "Unknown error")
        console.print(f"[red]Error: {error}[/red]")
        sys.exit(1)

    user_msg = ChatMessage(role=Role.USER, content=prompt)
    session_manager.add_message(user_msg, config.auto_save_interval)

    assistant_content = result.get("content", "") or ""
    assistant_msg = ChatMessage(role=Role.ASSISTANT, content=assistant_content)
    session_manager.add_message(assistant_msg, config.auto_save_interval)
    session_manager.save_session()

    console.print(assistant_content)


if __name__ == "__main__":
    main()
