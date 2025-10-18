"""Utility functions for autocomplete system."""

import os
from pathlib import Path
from typing import List


class FileFinder:
    """Utility class for finding files in directory trees."""

    def __init__(self, working_dir: Path):
        """Initialize file finder.

        Args:
            working_dir: Working directory to search in
        """
        self.working_dir = working_dir
        self._exclude_dirs = {
            ".git", ".hg", ".svn", "__pycache__", "node_modules",
            ".venv", "venv", ".pytest_cache", ".mypy_cache", ".tox",
            "dist", "build", ".eggs", "*.egg-info",
        }

    def find_files(self, query: str, max_results: int = 50) -> List[Path]:
        """Find files matching query.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of matching file paths
        """
        matches = []
        query_lower = query.lower()

        try:
            for root, dirs, files in os.walk(self.working_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in self._exclude_dirs]

                if len(matches) >= max_results:
                    break

                root_path = Path(root)

                for file in files:
                    file_path = root_path / file

                    try:
                        rel_path = file_path.relative_to(self.working_dir)
                        rel_path_str = str(rel_path).lower()
                    except ValueError:
                        continue

                    if not query_lower or query_lower in rel_path_str:
                        matches.append(file_path)

                        if len(matches) >= max_results:
                            break

        except (PermissionError, OSError):
            # Handle permission errors gracefully
            pass

        # Sort matches by relevance (shorter paths first, then alphabetically)
        matches.sort(key=lambda p: (len(str(p)), str(p)))

        return matches[:max_results]


class FileSizeFormatter:
    """Utility class for formatting file sizes."""

    @staticmethod
    def format_size(size: int) -> str:
        """Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def get_file_size(file_path: Path) -> str:
        """Get formatted file size for a file.

        Args:
            file_path: Path to file

        Returns:
            Formatted size string or empty string if unavailable
        """
        try:
            size = file_path.stat().st_size
            return FileSizeFormatter.format_size(size)
        except (OSError, FileNotFoundError):
            return ""