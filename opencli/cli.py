"""Command-line interface entry point for OpenCLI."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from opencli.core.approval import ApprovalManager
from opencli.core.management import ConfigManager, ModeManager, OperationMode, SessionManager, UndoManager
from opencli.core.services import RuntimeService
from opencli.models.agent_deps import AgentDependencies
from opencli.models.message import ChatMessage, Role
from opencli.repl.repl import REPL
from opencli.repl.repl_chat import create_repl_chat
from opencli.tools.bash_tool import BashTool
from opencli.tools.edit_tool import EditTool
from opencli.tools.file_ops import FileOperations
from opencli.tools.web_fetch_tool import WebFetchTool
from opencli.tools.write_tool import WriteTool


def main() -> None:
    """Main entry point for OpenCLI CLI."""
    parser = argparse.ArgumentParser(
        prog="opencli",
        description="OpenCLI - AI-powered command-line tool for accelerated development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  opencli                          # Start interactive session
  opencli -p "create hello.py"     # Non-interactive mode
  opencli -r abc123                # Resume session
  opencli mcp list                 # List MCP servers
  opencli mcp add myserver uvx mcp-server-example
        """
    )

    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="OpenCLI 0.1.0",
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

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # MCP subcommand
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Configure and manage MCP (Model Context Protocol) servers",
        description="Manage MCP servers for extending OpenCLI with external tools and capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  opencli mcp list                                    # List all servers
  opencli mcp add myserver uvx mcp-server-sqlite      # Add SQLite MCP server
  opencli mcp add custom node server.js arg1 arg2     # Add custom server with args
  opencli mcp add api python api.py --env API_KEY=xyz # Add with environment variable
  opencli mcp get myserver                            # Show server details
  opencli mcp enable myserver                         # Enable a server
  opencli mcp remove myserver                         # Remove a server
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
        description="Register a new MCP server that will be available to OpenCLI"
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
        help="Don't automatically start this server when OpenCLI launches"
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

    args = parser.parse_args()

    # Handle MCP commands
    if args.command == "mcp":
        _handle_mcp_command(args)
        return

    console = Console()

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

        # Interactive REPL mode with chat UI
        chat_app = create_repl_chat(config_manager, session_manager)
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


def _handle_mcp_command(args) -> None:
    """Handle MCP subcommands.

    Args:
        args: Parsed command-line arguments
    """
    from opencli.mcp.manager import MCPManager
    from opencli.mcp.models import MCPServerConfig
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
                from opencli.mcp.config import save_config
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

    runtime_service = RuntimeService(config_manager, mode_manager)
    runtime_suite = runtime_service.build_suite(
        file_ops=file_ops,
        write_tool=write_tool,
        edit_tool=edit_tool,
        bash_tool=bash_tool,
        web_fetch_tool=web_fetch_tool,
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
