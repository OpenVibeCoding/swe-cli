"""Tests for paste handling inside ChatTextArea."""

from textual.events import Paste

from swecli.ui_textual.chat_app import ChatTextArea


def test_small_paste_inserts_directly() -> None:
    textarea = ChatTextArea(paste_threshold=10)
    textarea.load_text("")

    textarea.on_paste(Paste("hello"))

    assert textarea.text == "hello"


def test_large_paste_uses_placeholder_and_cache() -> None:
    textarea = ChatTextArea(paste_threshold=10)
    textarea.load_text("")

    large_content = "x" * 20
    textarea.on_paste(Paste(large_content))

    tokenized = textarea.text
    assert tokenized != large_content
    assert "PASTE" in tokenized
    assert textarea.resolve_large_pastes(tokenized) == large_content

    textarea.clear_large_pastes()
    assert textarea.resolve_large_pastes(tokenized) == tokenized
