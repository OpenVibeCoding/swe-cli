"""Model selector modal management for SWE-CLI chat interface."""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple


class ModelSelectorModalManager:
    """Manages model selector modal state, display, and user interactions."""

    def __init__(self, chat_app):
        """Initialize model selector modal manager.

        Args:
            chat_app: The ChatApplication instance for callbacks
        """
        self.chat_app = chat_app
        self.reset_state()

    def reset_state(self) -> None:
        """Reset model selector modal state to defaults."""
        self._selector_mode = False
        self._selector_selected_index = 0
        self._selector_result = {"done": False, "selected": False, "item": None}
        self._selector_items = []
        self._selection_mode = "normal"  # Default to normal model selection
        self._is_category_selector = False  # Track if showing category vs model selector
        self._normal_configured = False  # Track if normal model is configured

    def is_in_selector_mode(self) -> bool:
        """Check if selector mode is currently active."""
        return self._selector_mode

    async def show_model_selector(self, selection_mode: str = "normal") -> Tuple[bool, Optional[dict]]:
        """Show model selector modal with arrow key navigation.

        Args:
            selection_mode: Which model slot to select for ("normal", "thinking", "vlm")

        Returns:
            Tuple of (selected: bool, item: dict or None)
                item format: {"type": "model", "provider_id": str, "model_id": str, "mode": str}
        """
        from swecli.ui.components.model_selector_message import (
            create_model_selector_message,
            get_model_items
        )

        # Reset state for new selection
        self.reset_state()
        self._selection_mode = selection_mode

        # Get all items (providers and models) filtered by capability
        self._selector_items = get_model_items(selection_mode)

        # CRITICAL: Unlock input buffer before clearing it
        self.chat_app._input_locked = False

        # Clear input buffer
        self.chat_app.input_buffer.text = ""
        self.chat_app.input_buffer.cursor_position = 0

        # Set up selector mode state (activates key handlers)
        self._selector_mode = True

        # Add initial selector message to conversation (as assistant message for proper display)
        selector_msg = create_model_selector_message(self._selector_selected_index, self._selection_mode)
        self.chat_app.conversation.add_assistant_message(selector_msg)
        self.chat_app._update_conversation_buffer()

        # Position conversation for selector visibility
        self._position_conversation_for_selector()

        self.chat_app.app.invalidate()

        try:
            # Wait for user to make a selection
            result = await self._wait_for_user_selection()

        finally:
            # Clean up selector mode
            await self._cleanup_selector_mode()

        # Remove the selector message from conversation
        self._remove_selector_message()

        # Re-enable auto-scroll after selector is done
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            conversation_control._auto_scroll = True

        self.chat_app.app.invalidate()

        return (result["selected"], result["item"])

    def _position_conversation_for_selector(self) -> None:
        """Position conversation to show selector message properly."""
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            # Scroll to bottom to show the selector
            conversation_control.scroll_to_bottom()
            self.chat_app.app.invalidate()

    async def _wait_for_user_selection(self) -> dict:
        """Wait for user to make a selection."""
        while not self._selector_result["done"]:
            await asyncio.sleep(0.05)
        return self._selector_result

    async def _cleanup_selector_mode(self) -> None:
        """Clean up selector mode state."""
        self._selector_mode = False
        self.chat_app._input_locked = False
        self.chat_app.app.invalidate()

    def _remove_selector_message(self) -> None:
        """Remove the selector message from conversation."""
        if self.chat_app.conversation.messages:
            self.chat_app.conversation.messages.pop()
            self.chat_app._update_conversation_buffer()

    def handle_selector_up(self) -> bool:
        """Handle up arrow in selector mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._selector_mode:
            return False

        if self._selector_selected_index > 0:
            self._selector_selected_index -= 1
            self._update_selector_message()
        return True

    def handle_selector_down(self) -> bool:
        """Handle down arrow in selector mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._selector_mode:
            return False

        if self._selector_selected_index < len(self._selector_items) - 1:
            self._selector_selected_index += 1
            self._update_selector_message()
        return True

    def handle_selector_enter(self) -> bool:
        """Handle enter in selector mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._selector_mode:
            return False

        # Get selected item
        if 0 <= self._selector_selected_index < len(self._selector_items):
            item_tuple = self._selector_items[self._selector_selected_index]
            item_type = item_tuple[0]
            provider_id = item_tuple[1]
            model_id = item_tuple[2]

            # Handle model selection
            if item_type == "model":
                self._selector_result["selected"] = True
                self._selector_result["item"] = {
                    "type": "model",
                    "provider_id": provider_id,
                    "model_id": model_id,
                    "mode": self._selection_mode  # Include which mode was selected
                }
            # Handle category selection
            elif item_type == "category":
                # Check if this category is disabled
                if len(item_tuple) > 5 and item_tuple[5]:  # is_disabled flag
                    # Disabled category selected - do nothing, just return
                    return True

                self._selector_result["selected"] = True
                self._selector_result["item"] = {
                    "type": "category",
                    "category": provider_id  # category_id is stored in provider_id slot
                }
            # Handle back button
            elif item_type == "back":
                self._selector_result["selected"] = True
                self._selector_result["item"] = {
                    "type": "back"
                }
            else:
                # Provider header selected - do nothing, just return
                return True

        self._selector_result["done"] = True
        return True

    def handle_selector_escape(self) -> bool:
        """Handle escape in selector mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._selector_mode:
            return False

        self._selector_result["selected"] = False
        self._selector_result["done"] = True
        return True

    def _update_selector_message(self) -> None:
        """Update the selector message with new selection."""
        # Choose appropriate selector based on mode
        if self._is_category_selector:
            from swecli.ui.components.category_selector_message import create_category_selector_message
            selector_msg = create_category_selector_message(
                self._selector_selected_index,
                self._normal_configured
            )
        else:
            from swecli.ui.components.model_selector_message import create_model_selector_message
            selector_msg = create_model_selector_message(self._selector_selected_index, self._selection_mode)

        if self.chat_app.conversation.messages:
            # Update last message (the selector) - keep as assistant message
            self.chat_app.conversation.messages[-1] = (
                "assistant",
                selector_msg,
                self.chat_app.conversation.messages[-1][2] if len(self.chat_app.conversation.messages[-1]) > 2 else None,
            )
            self.chat_app._update_conversation_buffer()
            self.chat_app.app.invalidate()
