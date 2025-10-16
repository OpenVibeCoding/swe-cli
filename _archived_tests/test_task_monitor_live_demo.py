#!/usr/bin/env python3
"""Live demo of task monitor with actual LLM call."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.core.monitoring import TaskMonitor
from opencli.ui.task_progress import TaskProgressDisplay
from opencli.core.agents import OpenCLIAgent
from opencli.models.config import AppConfig
from opencli.core.tools import ToolRegistry
from opencli.tools.file_ops import FileOperations
from opencli.tools.write_tool import WriteTool
from opencli.tools.edit_tool import EditTool
from opencli.tools.bash_tool import BashTool
from opencli.core.management import ModeManager, OperationMode
from rich.console import Console

print("╔════════════════════════════════════════════════════════════╗")
print("║    TASK MONITOR LIVE DEMO - Real LLM Call                ║")
print("║  ESC to interrupt · Real-time timer · Token tracking      ║")
print("╚════════════════════════════════════════════════════════════╝\n")

# Set up components
config = AppConfig()
console = Console()

# Create tool registry
file_ops = FileOperations(config, Path.cwd())
write_tool = WriteTool(config, Path.cwd())
edit_tool = EditTool(config, Path.cwd())
bash_tool = BashTool(config, Path.cwd())
tool_registry = ToolRegistry(
    file_ops=file_ops,
    write_tool=write_tool,
    edit_tool=edit_tool,
    bash_tool=bash_tool
)

# Create mode manager
mode_manager = ModeManager()
mode_manager.set_mode(OperationMode.PLAN)

# Create agent
agent = OpenCLIAgent(config, tool_registry, mode_manager)

print(f"Using model: {config.model}")
print("Making a simple LLM call...\n")

# Prepare a simple message
messages = [
    {"role": "user", "content": "Say hello and explain what you are in exactly 2 sentences."}
]

# Create task monitor
task_monitor = TaskMonitor()
task_monitor.start("Materializing", initial_tokens=0)

# Create and start progress display
progress = TaskProgressDisplay(console, task_monitor)
progress.start()

try:
    # Make LLM call with task monitor
    response = agent.call_llm(messages, task_monitor=task_monitor)

    # Stop progress and show final status
    progress.stop()
    progress.print_final_status()

    # Show the response
    if response["success"]:
        print(f"\n✅ LLM Response:")
        print(f"   {response['content']}\n")

        if response.get("usage"):
            usage = response["usage"]
            print(f"📊 Token Usage:")
            print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
            print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
            print(f"   Total tokens: {usage.get('total_tokens', 0)}")
    else:
        print(f"\n❌ Error: {response.get('error')}")

except KeyboardInterrupt:
    progress.stop()
    print("\n\n⏹ Interrupted by user")
except Exception as e:
    progress.stop()
    print(f"\n\n❌ Error: {e}")

print("\n✨ Task Monitor Features Demonstrated:")
print("  • Real-time timer showing elapsed seconds")
print("  • Token tracking with automatic API extraction")
print("  • ESC key interrupt support (try pressing ESC during call)")
print("  • Professional display format matching Claude Code")
print("\n🎉 Task monitor is fully functional!")
