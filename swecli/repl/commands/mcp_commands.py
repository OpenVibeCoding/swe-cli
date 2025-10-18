"""MCP (Model Context Protocol) commands for REPL."""

import asyncio
from typing import TYPE_CHECKING, Optional, Callable

from rich.console import Console
from rich.table import Table

from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.mcp.manager import MCPManager


class MCPCommands(CommandHandler):
    """Handler for MCP-related commands: /mcp <subcommand>."""

    def __init__(
        self,
        console: Console,
        mcp_manager: "MCPManager",
        refresh_runtime_callback: Optional[Callable[[], None]] = None,
        agent=None,
    ):
        """Initialize MCP commands handler.

        Args:
            console: Rich console for output
            mcp_manager: MCP manager instance
            refresh_runtime_callback: Callback to refresh runtime tooling after MCP changes
            agent: Agent instance for debug info
        """
        super().__init__(console)
        self.mcp_manager = mcp_manager
        self.refresh_runtime = refresh_runtime_callback
        self.agent = agent

    def handle(self, args: str) -> CommandResult:
        """Handle MCP command with subcommands.

        Args:
            args: Subcommand and arguments

        Returns:
            CommandResult from subcommand execution
        """
        if not args:
            self._show_usage()
            return CommandResult(success=True, message="Usage displayed")

        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()
        subcmd_args = parts[1] if len(parts) > 1 else ""

        # Route to appropriate subcommand
        subcommand_map = {
            "list": self.list_servers,
            "status": self.status,
            "connect": lambda: self.connect(subcmd_args.strip()) if subcmd_args else self._error_no_server_name(),
            "disconnect": lambda: self.disconnect(subcmd_args.strip()) if subcmd_args else self._error_no_server_name(),
            "enable": lambda: self.enable(subcmd_args.strip()) if subcmd_args else self._error_no_server_name(),
            "disable": lambda: self.disable(subcmd_args.strip()) if subcmd_args else self._error_no_server_name(),
            "tools": lambda: self.show_tools(subcmd_args.strip() if subcmd_args else None),
            "test": lambda: self.test(subcmd_args.strip()) if subcmd_args else self._error_no_server_name(),
            "reload": self.reload,
            "debug": self.debug,
        }

        if subcmd in subcommand_map:
            return subcommand_map[subcmd]()
        else:
            self.print_error(f"Unknown MCP subcommand: {subcmd}")
            return CommandResult(success=False, message=f"Unknown subcommand: {subcmd}")

    def _show_usage(self) -> None:
        """Show MCP command usage."""
        self.print_warning("Usage: /mcp <subcommand> [args]")
        self.console.print("\nAvailable subcommands:")
        self.console.print("  list              - List configured MCP servers")
        self.console.print("  status            - Quick status overview")
        self.console.print("  connect <name>    - Connect to a specific server")
        self.console.print("  disconnect <name> - Disconnect from a server")
        self.console.print("  enable <name>     - Enable auto-start for a server")
        self.console.print("  disable <name>    - Disable auto-start for a server")
        self.console.print("  tools [<name>]    - Show tools from server(s)")
        self.console.print("  test <name>       - Test connection to a server")
        self.console.print("  reload            - Reload MCP configuration")
        self.console.print("  debug             - Show debug info (tools in agent)")

    def _error_no_server_name(self) -> CommandResult:
        """Return error for missing server name."""
        self.print_error("Error: Server name required")
        return CommandResult(success=False, message="Server name required")

    def list_servers(self) -> CommandResult:
        """List all configured MCP servers."""
        servers = self.mcp_manager.list_servers()

        if not servers:
            self.print_warning("No MCP servers configured")
            return CommandResult(success=True, message="No servers")

        table = Table(title="MCP Servers", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Command")
        table.add_column("Enabled", justify="center")
        table.add_column("Auto-start", justify="center")

        for name, config in servers.items():
            status = "[green]✓ Connected[/green]" if self.mcp_manager.is_connected(name) else "[dim]Disconnected[/dim]"
            enabled = "[green]✓[/green]" if config.enabled else "[red]✗[/red]"
            auto_start = "[green]✓[/green]" if config.auto_start else "[dim]-[/dim]"
            command = f"{config.command} {' '.join(config.args[:2])}" if config.args else config.command
            if len(command) > 50:
                command = command[:47] + "..."

            table.add_row(name, status, command, enabled, auto_start)

        self.console.print(table)
        return CommandResult(success=True, data=servers)

    def connect(self, server_name: str) -> CommandResult:
        """Connect to a specific MCP server."""
        if self.mcp_manager.is_connected(server_name):
            self.print_warning(f"Already connected to '{server_name}'")
            return CommandResult(success=True, message="Already connected")

        self.console.print(f"Connecting to '{server_name}'...")
        try:
            success = self.mcp_manager.connect_sync(server_name)
            if success:
                tools = self.mcp_manager.get_server_tools(server_name)
                self.print_success(f"Connected to '{server_name}' ({len(tools)} tools available)")

                # Refresh runtime tooling
                if self.refresh_runtime:
                    self.refresh_runtime()

                return CommandResult(success=True, message=f"Connected to {server_name}")
            else:
                self.print_error(f"Failed to connect to '{server_name}'")
                return CommandResult(success=False, message="Connection failed")
        except Exception as e:
            self.print_error(f"Error connecting to '{server_name}': {e}")
            return CommandResult(success=False, message=str(e))

    def disconnect(self, server_name: str) -> CommandResult:
        """Disconnect from a specific MCP server."""
        if not self.mcp_manager.is_connected(server_name):
            self.print_warning(f"Not connected to '{server_name}'")
            return CommandResult(success=True, message="Not connected")

        try:
            self.mcp_manager.disconnect_sync(server_name)
            self.print_success(f"Disconnected from '{server_name}'")

            # Refresh runtime tooling
            if self.refresh_runtime:
                self.refresh_runtime()

            return CommandResult(success=True, message=f"Disconnected from {server_name}")
        except Exception as e:
            self.print_error(f"Error disconnecting from '{server_name}': {e}")
            return CommandResult(success=False, message=str(e))

    def show_tools(self, server_name: Optional[str]) -> CommandResult:
        """Show tools from MCP server(s)."""
        if server_name:
            # Show tools from specific server
            if not self.mcp_manager.is_connected(server_name):
                self.print_warning(f"Not connected to '{server_name}'")
                return CommandResult(success=False, message="Not connected")

            tools = self.mcp_manager.get_server_tools(server_name)
            if not tools:
                self.print_warning(f"No tools available from '{server_name}'")
                return CommandResult(success=True, message="No tools")

            self.console.print(f"\n[bold]Tools from '{server_name}':[/bold]\n")
            for tool in tools:
                self.console.print(f"  [cyan]{tool['name']}[/cyan]")
                self.console.print(f"    {tool['description']}")
        else:
            # Show all tools from all connected servers
            all_tools = self.mcp_manager.get_all_tools()
            if not all_tools:
                self.print_warning("No MCP tools available (no servers connected)")
                return CommandResult(success=True, message="No tools")

            # Group by server
            by_server = {}
            for tool in all_tools:
                server = tool.get('mcp_server', 'unknown')
                if server not in by_server:
                    by_server[server] = []
                by_server[server].append(tool)

            self.console.print("\n[bold]Available MCP Tools:[/bold]\n")
            for server, tools in by_server.items():
                self.console.print(f"[bold cyan]{server}[/bold cyan] ({len(tools)} tools)")
                for tool in tools:
                    self.console.print(f"  [cyan]{tool['name']}[/cyan] - {tool['description']}")
                self.console.print()

        return CommandResult(success=True)

    def test(self, server_name: str) -> CommandResult:
        """Test connection to a specific MCP server."""
        servers = self.mcp_manager.list_servers()
        if server_name not in servers:
            self.print_error(f"Server '{server_name}' not found in configuration")
            return CommandResult(success=False, message="Server not found")

        self.console.print(f"Testing connection to '{server_name}'...")

        try:
            # Try to connect
            success = asyncio.run(self.mcp_manager.connect(server_name))
            if success:
                tools = self.mcp_manager.get_server_tools(server_name)
                self.print_success("Connection successful")
                self.console.print(f"  • Discovered {len(tools)} tools")

                # List first few tools
                if tools:
                    self.console.print("\n  Sample tools:")
                    for tool in tools[:5]:
                        self.console.print(f"    - {tool['name']}")
                    if len(tools) > 5:
                        self.console.print(f"    ... and {len(tools) - 5} more")

                return CommandResult(success=True, message="Test passed")
            else:
                self.print_error("Connection failed")
                return CommandResult(success=False, message="Connection failed")
        except Exception as e:
            self.print_error(f"Test failed: {e}")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return CommandResult(success=False, message=str(e))

    def debug(self) -> CommandResult:
        """Show MCP debug information."""
        self.console.print("\n[bold cyan]MCP Debug Information[/bold cyan]\n")

        # Show connected servers
        servers = self.mcp_manager.list_servers()
        connected = [name for name in servers if self.mcp_manager.is_connected(name)]
        self.console.print(f"Connected servers: {len(connected)}/{len(servers)}")
        for name in connected:
            tools = self.mcp_manager.get_server_tools(name)
            self.console.print(f"  - [cyan]{name}[/cyan]: {len(tools)} tools")

        # Show agent tool count
        if self.agent:
            self.console.print(f"\nCurrent agent: {self.agent.__class__.__name__}")
            if hasattr(self.agent, 'tool_schemas'):
                total_tools = len(self.agent.tool_schemas)
                mcp_tools = sum(1 for t in self.agent.tool_schemas if 'mcp__' in t.get('function', {}).get('name', ''))
                self.console.print(f"Agent tools: {total_tools} total ({mcp_tools} MCP tools)")

                if mcp_tools > 0:
                    self.console.print("\nMCP tools in agent:")
                    shown = 0
                    for tool in self.agent.tool_schemas:
                        tool_name = tool.get('function', {}).get('name', '')
                        if 'mcp__' in tool_name:
                            self.console.print(f"  - {tool_name}")
                            shown += 1
                            if shown >= 5:
                                remaining = mcp_tools - 5
                                if remaining > 0:
                                    self.console.print(f"  ... and {remaining} more")
                                break
            else:
                self.console.print("Agent has no tool_schemas attribute")

            # Check system prompt
            if hasattr(self.agent, 'system_prompt'):
                has_mcp_section = "MCP Tools" in self.agent.system_prompt
                self.console.print(f"\nSystem prompt has MCP section: {'[green]Yes[/green]' if has_mcp_section else '[red]No[/red]'}")
            else:
                self.console.print("\nAgent has no system_prompt attribute")

        self.console.print()
        return CommandResult(success=True)

    def status(self) -> CommandResult:
        """Show quick status overview of MCP servers."""
        servers = self.mcp_manager.list_servers()

        if not servers:
            self.print_warning("No MCP servers configured")
            return CommandResult(success=True, message="No servers")

        connected = [name for name in servers if self.mcp_manager.is_connected(name)]
        enabled = [name for name, cfg in servers.items() if cfg.enabled]

        self.console.print(f"\n[bold cyan]MCP Status[/bold cyan]")
        self.console.print(f"  Servers: {len(servers)} configured, {len(connected)} connected, {len(enabled)} enabled")

        if connected:
            total_tools = sum(len(self.mcp_manager.get_server_tools(name)) for name in connected)
            self.console.print(f"  Tools: {total_tools} available")
            self.console.print(f"\n  Connected: {', '.join(f'[cyan]{name}[/cyan]' for name in connected)}")

        if enabled and not connected:
            disconnected_enabled = [name for name in enabled if name not in connected]
            if disconnected_enabled:
                self.console.print(f"  Enabled but disconnected: {', '.join(f'[yellow]{name}[/yellow]' for name in disconnected_enabled)}")

        self.console.print()
        return CommandResult(success=True)

    def enable(self, server_name: str) -> CommandResult:
        """Enable auto-start for an MCP server."""
        servers = self.mcp_manager.list_servers()

        if server_name not in servers:
            self.print_error(f"Server '{server_name}' not found in configuration")
            return CommandResult(success=False, message="Server not found")

        if servers[server_name].enabled:
            self.print_warning(f"Server '{server_name}' is already enabled")
            return CommandResult(success=True, message="Already enabled")

        try:
            success = self.mcp_manager.enable_server(server_name)
            if success:
                self.print_success(f"Enabled auto-start for '{server_name}'")
                self.console.print(f"[dim]Server will connect automatically on next startup[/dim]")
                return CommandResult(success=True, message=f"Enabled {server_name}")
            else:
                self.print_error(f"Failed to enable '{server_name}'")
                return CommandResult(success=False, message="Enable failed")
        except Exception as e:
            self.print_error(f"Error enabling server: {e}")
            return CommandResult(success=False, message=str(e))

    def disable(self, server_name: str) -> CommandResult:
        """Disable auto-start for an MCP server."""
        servers = self.mcp_manager.list_servers()

        if server_name not in servers:
            self.print_error(f"Server '{server_name}' not found in configuration")
            return CommandResult(success=False, message="Server not found")

        if not servers[server_name].enabled:
            self.print_warning(f"Server '{server_name}' is already disabled")
            return CommandResult(success=True, message="Already disabled")

        try:
            success = self.mcp_manager.disable_server(server_name)
            if success:
                self.print_success(f"Disabled auto-start for '{server_name}'")
                self.console.print(f"[dim]Server will not connect automatically on next startup[/dim]")
                return CommandResult(success=True, message=f"Disabled {server_name}")
            else:
                self.print_error(f"Failed to disable '{server_name}'")
                return CommandResult(success=False, message="Disable failed")
        except Exception as e:
            self.print_error(f"Error disabling server: {e}")
            return CommandResult(success=False, message=str(e))

    def reload(self) -> CommandResult:
        """Reload MCP configuration from files."""
        try:
            self.console.print("Reloading MCP configuration...")

            # Reload configuration
            config = self.mcp_manager.load_configuration()

            # Show summary
            servers = self.mcp_manager.list_servers()
            enabled = [name for name, cfg in servers.items() if cfg.enabled]

            self.print_success("Configuration reloaded")
            self.console.print(f"  Found {len(servers)} server(s), {len(enabled)} enabled")

            # Refresh runtime tooling
            if self.refresh_runtime:
                self.refresh_runtime()
                self.console.print(f"[dim]Agent tools refreshed[/dim]")

            return CommandResult(success=True, message="Config reloaded")
        except Exception as e:
            self.print_error(f"Error reloading configuration: {e}")
            return CommandResult(success=False, message=str(e))
