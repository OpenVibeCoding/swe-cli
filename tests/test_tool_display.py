import json
from types import SimpleNamespace

from swecli.repl.chat.tool_executor import ToolExecutor


class DummyConversation:
    def __init__(self):
        self.tool_calls = []
        self.tool_results = []
        self.assistant = []

    def add_tool_call(self, name, args):
        self.tool_calls.append((name, args))

    def add_tool_result(self, result):
        self.tool_results.append(result)

    def add_assistant_message(self, message):
        self.assistant.append(message)


class DummyChatApp:
    def __init__(self):
        self.conversation = DummyConversation()

    def _get_content_width(self):
        return 80


def make_executor(result_string: str) -> ToolExecutor:
    chat_app = DummyChatApp()
    formatter = SimpleNamespace(
        format_tool_result=lambda **_: result_string,
    )
    repl = SimpleNamespace(output_formatter=formatter)
    executor = ToolExecutor(repl=repl, chat_app=chat_app)
    return executor


def test_display_tool_result_claude_style():
    result_string = "⏺ Read(swecli/ui_textual/chat_app.py)\n  ⎿ Read 20 lines"
    executor = make_executor(result_string)

    tool_name = "Read"
    tool_args = {"file_path": "swecli/ui_textual/chat_app.py"}
    dummy_call = {
        "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
        "id": "dummy",
    }

    executor._display_tool_result(
        tool_call_display="Read(swecli/ui_textual/chat_app.py)",
        tool_name=tool_name,
        tool_args=tool_args,
        result={"success": True, "output": "Read 20 lines"},
    )

    conversation = executor.chat_app.conversation
    assert conversation.tool_calls == [("Read", "file_path='swecli/ui_textual/chat_app.py'")]
    assert conversation.tool_results == ["Read 20 lines"]
    assert conversation.assistant == []
