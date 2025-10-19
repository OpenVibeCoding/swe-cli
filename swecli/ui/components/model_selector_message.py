"""Model selector message component for interactive model switching."""

from typing import List, Tuple
from swecli.config import get_model_registry


def create_model_selector_message(selected_index: int) -> str:
    """Create an interactive model selector message with arrow key navigation.

    Args:
        selected_index: Index of currently selected item (0-based)

    Returns:
        Formatted message string with ANSI color codes
    """
    registry = get_model_registry()

    # Build list of all items (providers and their models)
    items: List[Tuple[str, str, str, str]] = []  # (type, provider_id, model_id, display_text)

    for provider_info in registry.list_providers():
        # Add provider header
        items.append((
            "provider",
            provider_info.id,
            "",
            f"[{provider_info.name}] - {len(provider_info.models)} models"
        ))

        # Add models under this provider
        for model_info in provider_info.list_models():
            # Format model info
            recommended = "⭐ " if model_info.recommended else "   "
            context_str = f"{model_info.context_length // 1000}k"
            pricing_str = model_info.format_pricing()

            display = f"  {recommended}{model_info.name} ({context_str}, {pricing_str})"

            items.append((
                "model",
                provider_info.id,
                model_info.id,
                display
            ))

    # ANSI color codes
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    REVERSE = "\033[7m"  # Inverse/highlight

    # Build the message
    lines = []
    lines.append(f"{BOLD}{CYAN}╭─ Select Model ────────────────────────────────────────────╮{RESET}")
    lines.append(f"{CYAN}│{RESET}")
    lines.append(f"{CYAN}│{RESET} {BOLD}Use ↑/↓ arrows or j/k to navigate, Enter to select{RESET}")
    lines.append(f"{CYAN}│{RESET} {DIM}Press ESC or Ctrl+C to cancel{RESET}")
    lines.append(f"{CYAN}│{RESET}")
    lines.append(f"{CYAN}├───────────────────────────────────────────────────────────┤{RESET}")

    # Add items with selection highlighting
    for idx, (item_type, provider_id, model_id, display_text) in enumerate(items):
        is_selected = (idx == selected_index)

        if item_type == "provider":
            # Provider header
            if is_selected:
                lines.append(f"{CYAN}│{RESET} {REVERSE}{YELLOW}{display_text}{RESET}")
            else:
                lines.append(f"{CYAN}│{RESET} {YELLOW}{display_text}{RESET}")
        else:
            # Model item
            if is_selected:
                lines.append(f"{CYAN}│{RESET} {REVERSE}{GREEN}{display_text}{RESET}")
            else:
                lines.append(f"{CYAN}│{RESET} {display_text}")

    lines.append(f"{BOLD}{CYAN}╰───────────────────────────────────────────────────────────╯{RESET}")

    return "\n".join(lines)


def get_model_items():
    """Get list of selectable items (providers and models).

    Returns:
        List of tuples: (type, provider_id, model_id, display_text)
            - type: "provider" or "model"
            - provider_id: ID of the provider
            - model_id: ID of the model (empty for provider headers)
            - display_text: Text to display
    """
    registry = get_model_registry()
    items = []

    for provider_info in registry.list_providers():
        # Add provider header
        items.append((
            "provider",
            provider_info.id,
            "",
            f"[{provider_info.name}] - {len(provider_info.models)} models"
        ))

        # Add models under this provider
        for model_info in provider_info.list_models():
            items.append((
                "model",
                provider_info.id,
                model_info.id,
                model_info.name
            ))

    return items
