"""File operation tools for reading, searching, and navigating codebases."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from swecli.models.config import AppConfig


class FileOperations:
    """Tools for file operations."""

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize file operations.

        Args:
            config: Application configuration
            working_dir: Working directory for operations
        """
        self.config = config
        self.working_dir = working_dir

    def read_file(self, file_path: str, line_start: Optional[int] = None,
                  line_end: Optional[int] = None) -> str:
        """Read a file's contents.

        Args:
            file_path: Path to the file (relative or absolute)
            line_start: Optional starting line number (1-indexed)
            line_end: Optional ending line number (1-indexed, inclusive)

        Returns:
            File contents or line range

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file read is not permitted
        """
        path = self._resolve_path(file_path)

        # Check permissions
        if not self.config.permissions.file_read.is_allowed(str(path)):
            raise PermissionError(f"Reading {path} is not permitted")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            if line_start is not None or line_end is not None:
                lines = f.readlines()
                start = (line_start - 1) if line_start else 0
                end = line_end if line_end else len(lines)
                return "".join(lines[start:end])
            return f.read()

    def glob_files(self, pattern: str, max_results: int = 100) -> list[str]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py", "src/**/*.ts")
            max_results: Maximum number of results to return

        Returns:
            List of matching file paths (relative to working_dir)
        """
        matches = []
        try:
            for path in self.working_dir.glob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(self.working_dir)
                    matches.append(str(rel_path))
                    if len(matches) >= max_results:
                        break
        except Exception as e:
            return [f"Error: {str(e)}"]

        return matches

    def grep_files(
        self,
        pattern: str,
        path: Optional[str] = None,
        context_lines: int = 0,
        max_results: int = 50,
        case_insensitive: bool = False,
    ) -> list[dict[str, any]]:
        """Search for pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: Optional path/directory to search in (relative to working_dir)
            context_lines: Number of context lines to include
            max_results: Maximum number of matches
            case_insensitive: Case insensitive search

        Returns:
            List of matches with file, line number, and content
        """
        matches = []

        try:
            # Use ripgrep if available for better performance
            cmd = ["rg", "--json", pattern]

            if case_insensitive:
                cmd.append("-i")
            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])

            # Add the search path if specified
            if path:
                search_path = self.working_dir / path
                cmd.append(str(search_path))

            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        if data["type"] == "match":
                            match_data = data["data"]
                            file_path = match_data["path"]["text"]
                            # Convert to absolute path
                            abs_path = str(self.working_dir / file_path)
                            matches.append({
                                "file": abs_path,
                                "line": match_data["line_number"],
                                "content": match_data["lines"]["text"].strip(),
                            })
                            if len(matches) >= max_results:
                                break
                    except:
                        continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to Python-based search if rg is not available
            matches = self._python_grep(pattern, path, max_results, case_insensitive)

        return matches

    def _python_grep(
        self, pattern: str, file_pattern: Optional[str],
        max_results: int, case_insensitive: bool
    ) -> list[dict[str, any]]:
        """Fallback grep implementation using Python."""
        matches = []
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)

        glob_pattern = file_pattern or "**/*"
        for path in self.working_dir.glob(glob_pattern):
            if not path.is_file():
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = path.relative_to(self.working_dir)
                            matches.append({
                                "file": str(rel_path),
                                "line": line_num,
                                "content": line.strip(),
                            })
                            if len(matches) >= max_results:
                                return matches
            except Exception:
                continue

        return matches

    def list_directory(self, path: str = ".", max_depth: int = 2) -> str:
        """List directory contents as a tree.

        Args:
            path: Directory path (relative or absolute)
            max_depth: Maximum depth to traverse

        Returns:
            Directory tree as string
        """
        dir_path = self._resolve_path(path)

        if not dir_path.exists():
            return f"Directory not found: {dir_path}"

        if not dir_path.is_dir():
            return f"Not a directory: {dir_path}"

        return self._build_tree(dir_path, max_depth=max_depth)

    def _build_tree(self, path: Path, prefix: str = "", max_depth: int = 2,
                    current_depth: int = 0) -> str:
        """Build a tree representation of directory structure."""
        if current_depth >= max_depth:
            return ""

        lines = []
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            # Filter out common ignore patterns
            items = [
                item for item in items
                if not any(
                    pattern in item.name
                    for pattern in [
                        "__pycache__",
                        ".git",
                        "node_modules",
                        ".pytest_cache",
                        "*.pyc",
                    ]
                )
            ]

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "

                rel_path = item.relative_to(self.working_dir)
                lines.append(f"{prefix}{current_prefix}{item.name}")

                if item.is_dir():
                    subtree = self._build_tree(
                        item,
                        prefix + next_prefix,
                        max_depth,
                        current_depth + 1,
                    )
                    if subtree:
                        lines.append(subtree)

        except PermissionError:
            lines.append(f"{prefix}[Permission Denied]")

        return "\n".join(lines)

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory.

        Args:
            path: Path string (relative or absolute)

        Returns:
            Resolved Path object
        """
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.working_dir / p).resolve()
