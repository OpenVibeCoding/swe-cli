"""Utility helpers for working with tool-related file paths."""

from __future__ import annotations


def sanitize_path(path: str) -> str:
    """Remove mention prefixes ("@"/"#") from file paths used in tools."""
    if not path:
        return path

    # Trim leading mention markers
    while path and path[0] in {"@", "#"}:
        path = path[1:]

    # Remove markers within path components
    parts = []
    for component in path.split("/"):
        while component and component[0] in {"@", "#"}:
            component = component[1:]
        if component:
            parts.append(component)

    return "/".join(parts) if parts else path
