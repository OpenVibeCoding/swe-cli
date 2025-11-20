"""LangChain tool wrappers for SWE-CLI file operations.

NOTE: Most file operation tools (read_file, write_file, edit_file, ls, grep, glob)
are provided by Deep Agent's built-in FilesystemMiddleware. This file is kept for
potential future custom file tool extensions if needed.
"""

# All core file operations are now handled by Deep Agent's built-in tools:
# - read_file (built-in)
# - write_file (built-in)
# - edit_file (built-in)
# - ls (built-in - equivalent to our old list_files)
# - grep (built-in - equivalent to our old search)
# - glob (built-in - for pattern matching)
