"""Utility functions for autocomplete system."""

import os
import time
from pathlib import Path
from typing import List, Optional


class FileFinder:
    """Utility class for finding files in directory trees with caching."""

    # Cache duration in seconds
    CACHE_TTL = 30.0
    # Maximum files to cache
    MAX_CACHE_SIZE = 5000

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
        # Cache: list of (relative_path_str_lower, Path) tuples
        self._cache: Optional[List[tuple[str, Path]]] = None
        self._cache_time: float = 0.0
        self._cache_working_dir: Optional[Path] = None

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._cache is None:
            return False
        if self._cache_working_dir != self.working_dir:
            return False
        if time.time() - self._cache_time > self.CACHE_TTL:
            return False
        return True

    def _build_cache(self) -> None:
        """Build the file cache by walking the directory tree once."""
        cache: List[tuple[str, Path]] = []

        try:
            for root, dirs, files in os.walk(self.working_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in self._exclude_dirs]

                root_path = Path(root)

                # Add directories
                for dirname in dirs:
                    dir_path = root_path / dirname
                    try:
                        rel_path = dir_path.relative_to(self.working_dir)
                        cache.append((str(rel_path).lower(), dir_path))
                    except ValueError:
                        continue

                # Add files
                for filename in files:
                    file_path = root_path / filename
                    try:
                        rel_path = file_path.relative_to(self.working_dir)
                        cache.append((str(rel_path).lower(), file_path))
                    except ValueError:
                        continue

                    # Limit cache size
                    if len(cache) >= self.MAX_CACHE_SIZE:
                        break

                if len(cache) >= self.MAX_CACHE_SIZE:
                    break

        except (PermissionError, OSError):
            pass

        # Sort by path length then alphabetically for consistent ordering
        cache.sort(key=lambda x: (len(x[0]), x[0]))

        self._cache = cache
        self._cache_time = time.time()
        self._cache_working_dir = self.working_dir

    def find_files(self, query: str, max_results: int = 50, include_dirs: bool = False) -> List[Path]:
        """Find files matching query using cached file list.

        Args:
            query: Search query
            max_results: Maximum number of results
            include_dirs: Whether to include directories in results

        Returns:
            List of matching file paths
        """
        # Rebuild cache if needed
        if not self._is_cache_valid():
            self._build_cache()

        if self._cache is None:
            return []

        query_lower = query.lower()
        matches: List[Path] = []

        for rel_path_lower, file_path in self._cache:
            # Filter directories if not requested
            if not include_dirs and file_path.is_dir():
                continue

            # Match query
            if not query_lower or query_lower in rel_path_lower:
                matches.append(file_path)
                if len(matches) >= max_results:
                    break

        return matches

    def invalidate_cache(self) -> None:
        """Invalidate the cache to force a refresh on next query."""
        self._cache = None


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
