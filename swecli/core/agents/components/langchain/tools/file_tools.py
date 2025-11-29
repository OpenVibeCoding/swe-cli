"""LangChain tool wrappers for SWE-CLI file operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


class WriteFileTool(SWECLIToolWrapper):
    """LangChain wrapper for write_file tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="write_file",
            description=(
                "Create a new file with the specified content. Use this when the user asks "
                "to create, write, or save a file. The file_path parameter specifies the "
                "full path to the file, and content parameter contains the file contents."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, file_path: str, content: str, **kwargs) -> str:
        """Execute write_file tool."""
        return super()._run(file_path=file_path, content=content, **kwargs)


class EditFileTool(SWECLIToolWrapper):
    """LangChain wrapper for edit_file tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="edit_file",
            description=(
                "Edit an existing file by replacing specific content. Use this when the user "
                "wants to modify parts of an existing file. The old_str parameter should "
                "exactly match the content to be replaced, and new_str contains the replacement. "
                "A backup is automatically created."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, file_path: str, old_str: str, new_str: str, **kwargs) -> str:
        """Execute edit_file tool."""
        return super()._run(file_path=file_path, old_str=old_str, new_str=new_str, **kwargs)


class ReadFileTool(SWECLIToolWrapper):
    """LangChain wrapper for read_file tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="read_file",
            description=(
                "Read the contents of a file. Use this to examine existing files, understand "
                "code structure, or review file contents. The file_path parameter specifies "
                "the full path to the file to read."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, file_path: str, **kwargs) -> str:
        """Execute read_file tool."""
        return super()._run(file_path=file_path, **kwargs)


class ListFilesTool(SWECLIToolWrapper):
    """LangChain wrapper for list_files tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="list_files",
            description=(
                "List files and directories in a specified path. Use this to explore the "
                "project structure, find relevant files, or understand directory contents. "
                "The path parameter specifies the directory to list."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, path: str, **kwargs) -> str:
        """Execute list_files tool."""
        return super()._run(path=path, **kwargs)


class SearchTool(SWECLIToolWrapper):
    """LangChain wrapper for search tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="search",
            description=(
                "Search for text patterns in files within a directory. Use this to find "
                "specific code patterns, function definitions, or text occurrences. "
                "The pattern parameter specifies what to search for, and path specifies "
                "where to search. Use regex patterns for advanced matching."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, pattern: str, path: str, **kwargs) -> str:
        """Execute search tool."""
        return super()._run(pattern=pattern, path=path, **kwargs)