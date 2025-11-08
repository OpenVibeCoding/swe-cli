"""File-oriented tool handlers used by the registry."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Union, Any

from swecli.core.tools.context import ToolExecutionContext
from swecli.core.tools.path_utils import sanitize_path
from swecli.models.operation import Operation, OperationType


class FileToolHandler:
    """Handles file read/write/edit operations."""

    def __init__(self, file_ops: Any, write_tool: Any, edit_tool: Any) -> None:
        self._file_ops = file_ops
        self._write_tool = write_tool
        self._edit_tool = edit_tool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def write_file(self, args: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        if not self._write_tool:
            return {"success": False, "error": "WriteTool not available"}

        file_path = sanitize_path(args["file_path"])
        content = args["content"]
        create_dirs = args.get("create_dirs", True)

        operation = Operation(
            id=str(hash(f"{file_path}{content}{datetime.now()}")),
            type=OperationType.FILE_WRITE,
            target=file_path,
            parameters={"content": content, "create_dirs": create_dirs},
            created_at=datetime.now(),
        )

        approved_content = self._ensure_write_approval(operation, content, context)
        if approved_content is None:
            return {
                "success": False,
                "error": "Operation cancelled by user",
                "output": None,
            }

        write_result = self._write_tool.write_file(
            file_path,
            approved_content,
            create_dirs=create_dirs,
            operation=operation,
        )

        if write_result.success and context.undo_manager:
            context.undo_manager.record_operation(operation)

        return {
            "success": write_result.success,
            "output": f"File created: {file_path}" if write_result.success else None,
            "error": (write_result.error or "Write operation failed") if not write_result.success else None,
        }

    def edit_file(self, args: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        if not self._edit_tool:
            return {"success": False, "error": "EditTool not available"}

        file_path = sanitize_path(args["file_path"])
        old_content = args["old_content"]
        new_content = args["new_content"]
        match_all = args.get("match_all", False)

        operation = Operation(
            id=str(hash(f"{file_path}{old_content}{new_content}{datetime.now()}")),
            type=OperationType.FILE_EDIT,
            target=file_path,
            parameters={
                "old_content": old_content,
                "new_content": new_content,
                "match_all": match_all,
            },
            created_at=datetime.now(),
        )

        preview = self._edit_tool.edit_file(
            file_path,
            old_content,
            new_content,
            match_all=match_all,
            dry_run=True,
        )

        if not preview.success:
            return {
                "success": False,
                "error": preview.error,
                "output": None,
            }

        if not self._is_approved(operation, context, preview.diff):
            return {
                "success": False,
                "error": "Operation cancelled by user",
                "output": None,
            }

        edit_result = self._edit_tool.edit_file(
            file_path,
            old_content,
            new_content,
            match_all=match_all,
            backup=True,
        )

        if edit_result.success and context.undo_manager:
            context.undo_manager.record_operation(operation)

        return {
            "success": edit_result.success,
            "output": (
                f"File edited: {file_path} (+{edit_result.lines_added}/-{edit_result.lines_removed})"
                if edit_result.success
                else None
            ),
            "error": (edit_result.error or "Edit operation failed") if not edit_result.success else None,
            "file_path": file_path,
            "lines_added": edit_result.lines_added,
            "lines_removed": edit_result.lines_removed,
            "diff": edit_result.diff,
        }

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self._file_ops:
            return {"success": False, "error": "FileOperations not available"}

        file_path = sanitize_path(args["file_path"])
        try:
            content = self._file_ops.read_file(file_path)
            return {"success": True, "output": content, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "output": None}

    def list_files(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self._file_ops:
            return {"success": False, "error": "FileOperations not available"}

        raw_path = args.get("path")
        path = sanitize_path(raw_path) if raw_path is not None else "."
        pattern = args.get("pattern")
        max_results = args.get("max_results", 100)

        try:
            base_path = Path(path)
            if not base_path.is_absolute():
                base_path = (self._file_ops.working_dir / base_path).resolve()
        except Exception as exc:
            return {"success": False, "error": f"Invalid path: {exc}", "output": None}

        try:
            if pattern:
                search_root = base_path if base_path.is_dir() else base_path.parent
                if not search_root.exists():
                    return {
                        "success": True,
                        "output": f"Directory not found: {search_root}",
                        "error": None,
                    }
                files = self._file_ops.glob_files(
                    pattern,
                    max_results=max_results,
                    base_path=search_root,
                )
                output = "\n".join(files) if files else "No files found"
            else:
                output = self._file_ops.list_directory(str(base_path))

            return {"success": True, "output": output, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "output": None}

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self._file_ops:
            return {"success": False, "error": "FileOperations not available"}

        pattern = args["pattern"]
        path = sanitize_path(args.get("path", "."))

        try:
            matches = self._file_ops.grep_files(pattern, path)
            if not matches:
                output = "No matches found"
            else:
                lines = [
                    f"{match['file']}:{match['line']} - {match['content']}"
                    for match in matches[:50]
                ]
                if len(matches) > 50:
                    lines.append(f"\n... and {len(matches) - 50} more matches")
                output = "\n".join(lines)

            return {"success": True, "output": output, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "output": None}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_write_approval(
        self,
        operation: Operation,
        content: str,
        context: ToolExecutionContext,
    ) -> Union[str, None]:
        if not self._is_approval_required(operation, context):
            operation.approved = True
            return content

        approval_manager = context.approval_manager
        if not approval_manager:
            operation.approved = True
            return content

        preview = content[:500] + ("..." if len(content) > 500 else "")
        result = self._run_sync_approval(
            approval_manager,
            operation,
            preview,
        )
        if result is None:
            operation.approved = True
            return content

        if not result.approved:
            return None

        if result.edited_content:
            operation.parameters["content"] = result.edited_content
            return result.edited_content
        operation.approved = True
        return content

    def _is_approved(
        self,
        operation: Operation,
        context: ToolExecutionContext,
        preview: Union[str, None],
    ) -> bool:
        if not self._is_approval_required(operation, context):
            operation.approved = True
            return True

        approval_manager = context.approval_manager
        if not approval_manager:
            operation.approved = True
            return True

        result = self._run_sync_approval(
            approval_manager,
            operation,
            preview or "",
        )
        if result is None:
            operation.approved = True
            return True

        return bool(result.approved)

    def _is_approval_required(
        self,
        operation: Operation,
        context: ToolExecutionContext,
    ) -> bool:
        mode_manager = context.mode_manager
        if not mode_manager:
            return True
        return mode_manager.needs_approval(operation)

    @staticmethod
    def _run_sync_approval(approval_manager: Any, operation: Operation, preview: str, **extra_kwargs: Any):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                approval_manager.request_approval(
                    operation=operation,
                    preview=preview,
                    **extra_kwargs,
                )
            )
        operation.approved = True
        return None
