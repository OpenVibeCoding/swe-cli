#!/usr/bin/env python3
"""Test the async MCP connect implementation."""

import sys
import asyncio
sys.path.insert(0, '/Users/quocnghi/codes/swe-cli')

from unittest.mock import Mock, MagicMock
from swecli.ui_textual.controllers.command_router import CommandRouter

async def test_mcp_connect_handling():
    print("=== Testing Async MCP Connect Implementation ===")

    # Mock app and conversation
    mock_app = Mock()
    mock_conversation = Mock()
    mock_conversation.add_system_message = Mock()

    mock_app.conversation = mock_conversation
    mock_app._start_local_spinner = Mock()
    mock_app._stop_local_spinner = Mock()

    # Mock runner with MCP manager
    mock_mcp_manager = Mock()
    mock_mcp_manager.connect_sync = Mock(return_value=True)
    mock_mcp_manager.get_server_tools = Mock(return_value=[
        {'name': 'tool1', 'description': 'Test tool 1'},
        {'name': 'tool2', 'description': 'Test tool 2'}
    ])

    mock_runner = Mock()
    mock_runner.repl = Mock()
    mock_runner.repl.mcp_manager = mock_mcp_manager
    mock_runner._refresh_runtime_tooling = Mock()

    mock_app.runner = mock_runner

    # Also set up direct mcp_manager attribute for easier access
    mock_app.mcp_manager = mock_mcp_manager

    # Create command router
    router = CommandRouter(mock_app)

    print("1. Testing /mcp connect github command...")

    # Test the async MCP connect command
    await router._handle_mcp_command("/mcp connect github")

    print("2. Checking method calls...")

    # Verify spinner was started and stopped with correct message
    mock_app._start_local_spinner.assert_called_once_with("Connecting to github")
    mock_app._stop_local_spinner.assert_called_once()

    # Check what messages were sent
    calls = mock_conversation.add_system_message.call_args_list
    print(f"   Number of system messages: {len(calls)}")
    for i, call in enumerate(calls):
        print(f"   Message {i+1}: {call[0][0]}")

    # Verify MCP manager was called
    print(f"   connect_sync call count: {mock_mcp_manager.connect_sync.call_count}")
    print(f"   get_server_tools call count: {mock_mcp_manager.get_server_tools.call_count}")

    mock_mcp_manager.connect_sync.assert_called_once_with('github')
    mock_mcp_manager.get_server_tools.assert_called_once_with('github')

    print("3. Checking output format...")

    # Check the messages sent to conversation
    calls = mock_conversation.add_system_message.call_args_list

    # Should have at least 1 message: final result
    assert len(calls) >= 1, f"Expected at least 1 message, got {len(calls)}"

    # Check the messages contain the expected format
    messages = [call[0][0] for call in calls]

    # Find the result message (should contain ⏺ and ⎿)
    result_msg = None
    for msg in messages:
        if '⏺ MCP' in msg and '⎿' in msg and 'Connected' in msg:
            result_msg = msg
            break

    assert result_msg is not None, "Expected to find result message with ⏺ and ⎿ format"
    print(f"   Found result message: {result_msg[:50]}...")

    # Verify it contains the expected elements
    assert 'github' in result_msg, "Result should mention github"
    assert 'tools available' in result_msg, "Result should mention tools count"
    assert '⏺ MCP (github)' in result_msg, "Should have ⏺ MCP format"
    assert '⎿' in result_msg, "Should have ⎿ format"

    print("   ✅ Message format is correct!")

    # Check that refresh was called
    mock_runner._refresh_runtime_tooling.assert_called_once()

    print("4. Testing error handling...")

    # Test connection failure
    mock_conversation.add_system_message.reset_mock()
    mock_mcp_manager.connect_sync.return_value = False

    await router._handle_mcp_command("/mcp connect invalid-server")

    # Should still be called but with error message
    error_calls = mock_conversation.add_system_message.call_args_list
    error_messages = [call[0][0] for call in error_calls]

    error_found = any('❌' in msg and 'invalid-server' in msg for msg in error_messages)
    assert error_found, "Should show error message for failed connection"

    print("   ✅ Error handling works!")

    print("🎉 ALL TESTS PASSED!")
    print()
    print("KEY IMPROVEMENTS:")
    print("✅ MCP connect is now non-blocking (async)")
    print("✅ Uses spinner during connection")
    print("✅ Displays results with ⏺ MCP (server) (time) format")
    print("✅ Uses ⎿ symbol for status messages")
    print("✅ Automatically refreshes runtime tooling after connection")
    print("✅ Proper error handling with user-friendly messages")

if __name__ == "__main__":
    asyncio.run(test_mcp_connect_handling())