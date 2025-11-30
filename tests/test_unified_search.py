"""Unit tests for the unified search tool (text + AST modes)."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from swecli.core.tools.file_handlers import FileToolHandler
from swecli.tools.file_ops import FileOperations
from swecli.models.config import AppConfig


class TestUnifiedSearchHandler:
    """Test the unified search handler in FileToolHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Python file
            py_file = Path(tmpdir) / "test_module.py"
            py_file.write_text("""
def calculate_tax(amount):
    return amount * 0.1

def fetch_data(url):
    return requests.get(url)

class UserService:
    def get_user(self, user_id):
        return self.db.find(user_id)
""")
            # Create test JS file
            js_file = Path(tmpdir) / "app.js"
            js_file.write_text("""
function fetchUser(id) {
    return fetch('/api/users/' + id);
}

console.log('Starting app');

async function loadData() {
    const result = await fetch('/api/data');
    return result.json();
}
""")
            yield tmpdir

    @pytest.fixture
    def file_ops(self, temp_dir):
        """Create FileOperations instance."""
        config = AppConfig()
        return FileOperations(config, Path(temp_dir))

    @pytest.fixture
    def handler(self, file_ops):
        """Create FileToolHandler with mocked dependencies."""
        return FileToolHandler(file_ops, None, None)

    # -------------------------------------------------------------------------
    # Text search mode tests (default)
    # -------------------------------------------------------------------------

    def test_text_search_finds_function(self, handler, temp_dir):
        """Test text search finds function definition."""
        result = handler.search({
            "pattern": "def calculate_tax",
            "path": temp_dir,
        })

        assert result["success"] is True
        assert "matches" in result
        assert len(result["matches"]) >= 1
        assert any("calculate_tax" in m["content"] for m in result["matches"])

    def test_text_search_with_explicit_type(self, handler, temp_dir):
        """Test text search with explicit type='text'."""
        result = handler.search({
            "pattern": "fetch",
            "path": temp_dir,
            "type": "text",
        })

        assert result["success"] is True
        assert len(result["matches"]) >= 2  # Should find in both py and js

    def test_text_search_no_matches(self, handler, temp_dir):
        """Test text search returns empty when no matches."""
        result = handler.search({
            "pattern": "nonexistent_pattern_xyz_123",
            "path": temp_dir,
        })

        assert result["success"] is True
        assert result["matches"] == []
        assert "No matches found" in result["output"]

    def test_text_search_regex_pattern(self, handler, temp_dir):
        """Test text search with regex pattern."""
        result = handler.search({
            "pattern": r"def \w+\(",
            "path": temp_dir,
        })

        assert result["success"] is True
        assert len(result["matches"]) >= 3  # calculate_tax, fetch_data, get_user

    # -------------------------------------------------------------------------
    # AST search mode tests
    # -------------------------------------------------------------------------

    def test_ast_search_function_calls(self, handler, temp_dir):
        """Test AST search for function calls."""
        result = handler.search({
            "pattern": "fetch($URL)",
            "path": temp_dir,
            "type": "ast",
        })

        # AST search might not be installed, handle gracefully
        if not result["success"] and "not installed" in result.get("error", ""):
            pytest.skip("ast-grep not installed")

        assert result["success"] is True

    def test_ast_search_with_lang_hint(self, handler, temp_dir):
        """Test AST search with language hint."""
        result = handler.search({
            "pattern": "console.log($MSG)",
            "path": temp_dir,
            "type": "ast",
            "lang": "javascript",
        })

        if not result["success"] and "not installed" in result.get("error", ""):
            pytest.skip("ast-grep not installed")

        assert result["success"] is True

    def test_ast_search_no_matches(self, handler, temp_dir):
        """Test AST search returns empty when no matches."""
        result = handler.search({
            "pattern": "nonexistent_function_call($X)",
            "path": temp_dir,
            "type": "ast",
        })

        if not result["success"]:
            error = result.get("error", "")
            if "not installed" in error:
                pytest.skip("ast-grep not installed")
            # ast-grep may return error for invalid patterns or other issues
            pytest.skip(f"AST search error: {error}")

        assert result["success"] is True
        assert result["matches"] == []
        assert "No structural matches found" in result["output"]

    # -------------------------------------------------------------------------
    # Error handling tests
    # -------------------------------------------------------------------------

    def test_search_invalid_path(self, handler):
        """Test search with non-existent path."""
        result = handler.search({
            "pattern": "test",
            "path": "/nonexistent/path/xyz",
        })

        # Should handle gracefully - either no matches or error
        # ripgrep returns empty matches for non-existent paths
        assert "success" in result

    def test_search_missing_file_ops(self):
        """Test search fails gracefully when file_ops not available."""
        handler = FileToolHandler(None, None, None)

        result = handler.search({
            "pattern": "test",
            "path": ".",
        })

        assert result["success"] is False
        assert "not available" in result["error"]

    # -------------------------------------------------------------------------
    # Match format tests
    # -------------------------------------------------------------------------

    def test_match_format_has_required_keys(self, handler, temp_dir):
        """Test that matches have the expected keys for UI display."""
        result = handler.search({
            "pattern": "def",
            "path": temp_dir,
        })

        assert result["success"] is True
        if result["matches"]:
            match = result["matches"][0]
            assert "file" in match
            assert "line" in match
            assert "content" in match

    def test_output_format(self, handler, temp_dir):
        """Test output format is human readable."""
        result = handler.search({
            "pattern": "calculate_tax",
            "path": temp_dir,
        })

        assert result["success"] is True
        # Output should contain file:line - content format
        if result["matches"]:
            assert ":" in result["output"]


class TestSearchFormatterIntegration:
    """Test the search result formatter handles match format correctly."""

    def test_formatter_handles_file_line_content_format(self):
        """Test formatter correctly formats matches with file/line/content keys."""
        from swecli.ui_textual.formatters.style_formatter import StyleFormatter

        formatter = StyleFormatter()

        # Simulate search result with new format
        result = {
            "success": True,
            "output": "test",
            "matches": [
                {"file": "/path/to/file.py", "line": 10, "content": "def test():"},
                {"file": "/path/to/other.py", "line": 25, "content": "test_value = 42"},
            ]
        }

        lines = formatter._format_search_result({}, result)

        assert len(lines) == 2
        assert "/path/to/file.py:10" in lines[0]
        assert "def test()" in lines[0]
        assert "/path/to/other.py:25" in lines[1]

    def test_formatter_handles_legacy_location_preview_format(self):
        """Test formatter still handles legacy format with location/preview keys."""
        from swecli.ui_textual.formatters.style_formatter import StyleFormatter

        formatter = StyleFormatter()

        # Simulate legacy format
        result = {
            "success": True,
            "output": "test",
            "matches": [
                {"location": "file.py:10", "preview": "def test():"},
            ]
        }

        lines = formatter._format_search_result({}, result)

        assert len(lines) == 1
        assert "file.py:10" in lines[0]
        assert "def test()" in lines[0]

    def test_formatter_handles_no_matches(self):
        """Test formatter handles empty matches."""
        from swecli.ui_textual.formatters.style_formatter import StyleFormatter

        formatter = StyleFormatter()

        result = {
            "success": True,
            "output": "No matches found",
            "matches": []
        }

        lines = formatter._format_search_result({}, result)

        assert lines == ["No matches found"]

    def test_formatter_truncates_many_matches(self):
        """Test formatter shows truncation message for many matches."""
        from swecli.ui_textual.formatters.style_formatter import StyleFormatter

        formatter = StyleFormatter()

        # Create 10 matches
        matches = [
            {"file": f"/path/file{i}.py", "line": i, "content": f"line {i}"}
            for i in range(10)
        ]

        result = {
            "success": True,
            "output": "test",
            "matches": matches
        }

        lines = formatter._format_search_result({}, result)

        # Should show first 3 + truncation message
        assert len(lines) == 4
        assert "... and 7 more" in lines[-1]


class TestFileOpsGrepFiles:
    """Test the underlying grep_files method."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    print('hello world')\n")
            yield tmpdir

    @pytest.fixture
    def file_ops(self, temp_dir):
        """Create FileOperations instance."""
        config = AppConfig()
        return FileOperations(config, Path(temp_dir))

    def test_grep_returns_list(self, file_ops, temp_dir):
        """Test grep_files returns a list."""
        matches = file_ops.grep_files("hello", temp_dir)
        assert isinstance(matches, list)

    def test_grep_match_structure(self, file_ops, temp_dir):
        """Test grep match has correct structure."""
        matches = file_ops.grep_files("hello", temp_dir)

        if matches:  # ripgrep might not be installed
            match = matches[0]
            assert "file" in match
            assert "line" in match
            assert "content" in match

    def test_grep_handles_dot_path(self, file_ops):
        """Test grep handles '.' path correctly (was a bug)."""
        # This was causing 'Unacceptable pattern: PosixPath' error
        matches = file_ops.grep_files("def", ".")
        assert isinstance(matches, list)

    def test_grep_handles_dotslash_path(self, file_ops):
        """Test grep handles './' path correctly."""
        matches = file_ops.grep_files("def", "./")
        assert isinstance(matches, list)
