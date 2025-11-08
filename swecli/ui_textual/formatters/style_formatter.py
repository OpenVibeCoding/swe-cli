"""Claude Code-style formatter used by the Textual UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from swecli.ui_textual.formatters_internal.formatter_base import STATUS_ICONS
from swecli.ui_textual.utils.tool_display import get_tool_display_parts
from swecli.ui_textual.constants import TOOL_ERROR_SENTINEL


class ClaudeStyleFormatter:
    """Minimalist formatter inspired by Claude Code's display style."""

    def format_tool_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> str:
        tool_display = self._format_tool_call(tool_name, tool_args)

        if tool_name == "read_file":
            result_lines = self._format_read_file_result(tool_args, result)
        elif tool_name == "write_file":
            result_lines = self._format_write_file_result(tool_args, result)
        elif tool_name == "edit_file":
            result_lines = self._format_edit_file_result(tool_args, result)
        elif tool_name == "search":
            result_lines = self._format_search_result(tool_args, result)
        elif tool_name in {"run_command", "bash_execute"}:
            result_lines = self._format_shell_result(tool_args, result)
        elif tool_name == "list_files":
            result_lines = self._format_list_files_result(tool_args, result)
        elif tool_name == "fetch_url":
            result_lines = self._format_fetch_url_result(tool_args, result)
        elif tool_name == "analyze_image":
            result_lines = self._format_analyze_image_result(tool_args, result)
        elif tool_name == "get_process_output":
            result_lines = self._format_process_output_result(tool_args, result)
        else:
            result_lines = self._format_generic_result(tool_name, tool_args, result)

        if result_lines:
            return f"⏺ {tool_display}\n" + "\n".join(f"  ⎿ {line}" for line in result_lines)
        return f"⏺ {tool_display}"

    def _format_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        verb, label = get_tool_display_parts(tool_name)
        display_name = f"{verb}({label})" if label else verb

        if not tool_args:
            return display_name

        arg_strs = []
        for key, value in tool_args.items():
            arg_str = self._format_argument(key, value)
            if arg_str:
                arg_strs.append(f"{key}={arg_str}")

        if arg_strs:
            return f"{self._highlight_function_name(display_name)}({', '.join(arg_strs)})"
        return self._highlight_function_name(display_name)

    def _highlight_function_name(self, function_name: str) -> str:
        COLOR = "\033[96m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
        return f"{COLOR}{BOLD}{function_name}{RESET}"

    @staticmethod
    def _error_line(message: str) -> str:
        return f"{TOOL_ERROR_SENTINEL} {message.strip()}"

    def _format_argument(self, key: str, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            if key in {"content", "new_string", "old_string", "text", "command"}:
                if len(value) > 80:
                    lines = value.count("\n") + 1
                    return f"<{len(value)} chars, {lines} lines>"
                first_line = value.split("\n", 1)[0]
                if len(first_line) > 50:
                    return repr(first_line[:47] + "...")
                return repr(first_line)
            if key in {"file_path", "path", "image_path"}:
                return repr(value)
            if key == "pattern":
                return repr(value)
            if key in {"old_content", "new_content"}:
                if len(value) > 50:
                    return repr(value[:47] + "...")
                return repr(value)

        value_repr = repr(value)
        if len(value_repr) > 100:
            return value_repr[:97] + "..."
        return value_repr

    def _format_read_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        output = result.get("output", "")
        size_bytes = len(output)
        size_kb = size_bytes / 1024
        lines = output.count("\n") + 1 if output else 0

        size_display = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{size_bytes} B"
        return [f"Read {lines} lines • {size_display}"]

    def _format_write_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        file_path = tool_args.get("file_path", "unknown")
        content = tool_args.get("content", "")
        size_bytes = len(content)
        size_kb = size_bytes / 1024
        lines = content.count("\n") + 1 if content else 0
        size_display = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{size_bytes} B"
        return [f"Created {Path(file_path).name} • {size_display} • {lines} lines"]

    def _format_edit_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        file_path = tool_args.get("file_path", "unknown")
        old_content = tool_args.get("old_content", "")
        new_content = tool_args.get("new_content", "")
        old_lines = old_content.splitlines() if old_content else []
        new_lines = new_content.splitlines() if new_content else []
        additions = len([line for line in new_lines if line not in old_lines])
        deletions = len([line for line in old_lines if line not in new_lines])

        return [f"Updated {Path(file_path).name} with {additions} additions and {deletions} removals"]

    def _format_search_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        matches = result.get("matches", [])
        if not matches:
            return ["No matches found"]

        summary = []
        for match in matches[:3]:
            location = match.get("location", "unknown")
            summary.append(f"{location}: {match.get('preview', '').strip()}")
        if len(matches) > 3:
            summary.append(f"... and {len(matches) - 3} more")

        return summary

    def _format_shell_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        command = (tool_args.get("command") or "").strip()
        stdout = (result.get("stdout") or result.get("output") or "").strip()
        stderr = (result.get("stderr") or "").strip()
        exit_code = result.get("exit_code", 0)

        normalized_cmd = command.lower()
        normalized_stdout = stdout.lower()

        if exit_code not in (None, 0):
            if stderr:
                first_err = stderr.splitlines()[0].strip()
                return [self._error_line(first_err)]
            return [self._error_line(f"Exit code {exit_code}")]

        if normalized_cmd.startswith("git ") or " git " in normalized_cmd:
            if "push" in normalized_cmd:
                return ["Changes pushed to remote"]
            if "commit" in normalized_cmd:
                return ["Changes committed"]
            if "pull" in normalized_cmd:
                return ["Changes pulled from remote"]
            return ["Git command completed"]

        if "npm install" in normalized_cmd:
            if "added" in normalized_stdout and "package" in normalized_stdout:
                return ["Packages installed successfully"]
            return ["npm install completed"]

        if stdout:
            lines = stdout.splitlines()
            first_line = lines[0].strip()
            if len(lines) == 1 and len(first_line) < 80:
                return [first_line]
            first_preview = first_line[:70] + ("..." if len(first_line) > 70 else "")
            return [f"{first_preview} ({len(lines)} lines)"]

        if stderr:
            first_err = stderr.splitlines()[0].strip()
            return [first_err]

        return ["Command completed with no output"]

    def _format_list_files_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        entries = result.get("entries", [])
        if not entries:
            return ["No files found"]
        return [f"{len(entries)} entries"]

    def _format_fetch_url_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        elapsed = result.get("elapsed", 0.0)
        status = result.get("status_code", 200)
        return [f"HTTP {status} in {elapsed:.2f}s"]

    def _format_analyze_image_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]
        return [result.get("summary", "Analysis complete")]

    def _format_process_output_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        lines = (result.get("output") or "").splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            return ["Process completed with no output"]

        first_line = lines[0]
        if len(lines) == 1 and len(first_line) < 80:
            return [first_line]

        preview = first_line[:70] + ("..." if len(first_line) > 70 else "")
        return [f"{preview} ({len(lines)} lines)"]

    def _format_generic_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        if not result.get("success"):
            return [self._error_line(result.get("error", "Unknown error"))]

        output = result.get("output")
        if isinstance(output, str):
            lines = output.strip().splitlines()
            if not lines:
                return []
            return lines[:3] + (["…"] if len(lines) > 3 else [])

        if isinstance(output, list):
            truncated = [str(item) for item in output[:3]]
            if len(output) > 3:
                truncated.append("…")
            return truncated

        if isinstance(output, dict):
            return [f"{key}: {value}" for key, value in list(output.items())[:3]]

        if output is None:
            status = result.get("status", "completed")
            return [STATUS_ICONS.get(status, "✅") + f" {status}"]

        return [str(output)]
