"""LangChain Deep Agent implementation for advanced task planning and execution."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_fireworks import ChatFireworks
from langchain_openai import ChatOpenAI

from swecli.core.abstract import BaseAgent
from swecli.core.agents.components.langchain.tools import ToolRegistryAdapter
from swecli.models.config import AppConfig

# Import deepagents if available, handle import gracefully
try:
    from deepagents import create_deep_agent
    _DEEPAGENTS_AVAILABLE = True
except ImportError:
    _DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None


class DeepAgentInterruptMonitor:
    """Monitor for interrupting Deep Agent operations."""

    def __init__(self, task_monitor: Optional[Any] = None):
        """Initialize the interrupt monitor.

        Args:
            task_monitor: Optional task monitor for interrupt checking
        """
        self.task_monitor = task_monitor
        self._should_interrupt = False
        self._lock = threading.Lock()

    def should_interrupt(self) -> bool:
        """Check if interrupt has been requested.

        Returns:
            True if interrupt should occur
        """
        with self._lock:
            if self._should_interrupt:
                return True

        # Check task monitor if available
        if self.task_monitor:
            try:
                if hasattr(self.task_monitor, "should_interrupt"):
                    return self.task_monitor.should_interrupt()
                elif hasattr(self.task_monitor, "is_interrupted"):
                    return self.task_monitor.is_interrupted()
            except Exception:
                # If task monitor check fails, continue without interrupt
                pass

        return False

    def set_interrupt(self) -> None:
        """Set the interrupt flag."""
        with self._lock:
            self._should_interrupt = True

    def clear_interrupt(self) -> None:
        """Clear the interrupt flag."""
        with self._lock:
            self._should_interrupt = False


class InterruptibleDeepAgent:
    """Wrapper for Deep Agent that supports interrupt handling."""

    def __init__(self, deep_agent: Any, interrupt_monitor: DeepAgentInterruptMonitor):
        """Initialize the interruptible wrapper.

        Args:
            deep_agent: The actual Deep Agent instance
            interrupt_monitor: Monitor for checking interrupts
        """
        self.deep_agent = deep_agent
        self.interrupt_monitor = interrupt_monitor

    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the Deep Agent with interrupt support.

        Args:
            payload: Payload to send to the Deep Agent

        Returns:
            Response from the Deep Agent or interrupt result
        """
        # Check for interrupt before starting
        if self.interrupt_monitor.should_interrupt():
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Operation interrupted by user before execution started.",
                    }
                ]
            }

        # For Deep Agents, we need to handle interrupt during execution
        # Since Deep Agents run in LangGraph, we'll use threading approach
        result_container = {"result": None, "error": None, "interrupted": False}
        exception_container = {"exception": None}

        def execute_with_interrupt():
            """Execute the Deep Agent in a separate thread."""
            try:
                result = self.deep_agent.invoke(payload)
                result_container["result"] = result
            except Exception as e:
                exception_container["exception"] = e

        # Start the execution thread
        execution_thread = threading.Thread(target=execute_with_interrupt, daemon=True)
        execution_thread.start()

        # Monitor for interrupts while execution runs
        while execution_thread.is_alive():
            if self.interrupt_monitor.should_interrupt():
                # Mark as interrupted - we can't actually stop the thread safely
                # but we can return an interrupt response immediately
                result_container["interrupted"] = True

                # Give the thread a moment to finish naturally
                execution_thread.join(timeout=0.5)

                if execution_thread.is_alive():
                    # Thread is still running, return interrupt response
                    return {
                        "messages": [
                            {
                                "role": "assistant",
                                "content": "Operation interrupted by user. The Deep Agent may still be running in the background.",
                            }
                        ]
                    }
                else:
                    # Thread finished naturally
                    break

            # Small delay to prevent busy-waiting
            time.sleep(0.1)

        # Check for exceptions
        if exception_container["exception"]:
            raise exception_container["exception"]

        # Check if execution was interrupted
        if result_container["interrupted"] and result_container["result"] is None:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Operation was interrupted during execution.",
                    }
                ]
            }

        # Return the actual result
        return result_container["result"]


class DeepLangChainAgent(BaseAgent):
    """Agent that uses LangChain Deep Agents for advanced planning and execution."""

    def __init__(
        self,
        config: AppConfig,
        tool_registry: Any,
        mode_manager: Any,
        working_dir: Optional[Any] = None,
    ) -> None:
        """Initialize the Deep LangChain Agent.

        Args:
            config: Application configuration
            tool_registry: Registry of available tools
            mode_manager: Mode manager for plan/normal mode switching
            working_dir: Working directory for context
        """
        super().__init__(config, tool_registry, mode_manager)
        self._working_dir = working_dir
        self._deep_agent = None
        self._tool_adapter = None

        # TODO: Initialize deep agent and tool adapter in subsequent steps
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize deep agent components."""
        if not _DEEPAGENTS_AVAILABLE:
            print("Warning: deepagents library not available, Deep Agent functionality disabled")
            return

        try:
            # Create the LangChain model based on provider
            model = self._create_model()

            # Initialize tool adapter
            self._tool_adapter = ToolRegistryAdapter(self.tool_registry)

            # Get tools
            tools = self._tool_adapter.get_langchain_tools()
            print(f"[DEBUG] Initializing Deep Agent with {len(tools)} tools:")
            for tool in tools[:5]:  # Show first 5
                print(f"  - {tool.name}: {tool.description[:60]}...")

            # Create the deep agent with model and tools
            deep_agent = create_deep_agent(
                model=model,
                tools=tools
            )
            print(f"[DEBUG] Deep Agent created successfully")

            # Wrap with interruptible support
            self._interrupt_monitor = DeepAgentInterruptMonitor()
            self._deep_agent = InterruptibleDeepAgent(deep_agent, self._interrupt_monitor)

        except Exception as e:
            print(f"Warning: Failed to initialize Deep Agent: {e}")
            self._deep_agent = None

    def _create_model(self) -> BaseChatModel:
        """Create LangChain model based on configuration."""
        provider = getattr(self.config, 'model_provider', 'fireworks')
        model_name = getattr(self.config, 'model', 'accounts/fireworks/models/llama-v3p1-8b-instruct')
        temperature = getattr(self.config, 'temperature', 0.7)
        max_tokens = getattr(self.config, 'max_tokens', 4096)

        if provider == 'fireworks' or 'fireworks' in model_name:
            api_key = getattr(self.config, 'fireworks_api_key', None) or getattr(self.config, 'api_key', None) or os.getenv('FIREWORKS_API_KEY')
            base_url = getattr(self.config, 'api_base_url', None) or "https://api.fireworks.ai/inference/v1"

            return ChatFireworks(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        elif provider == 'openai' or 'gpt' in model_name.lower():
            api_key = getattr(self.config, 'openai_api_key', None) or getattr(self.config, 'api_key', None) or os.getenv('OPENAI_API_KEY')
            base_url = getattr(self.config, 'openai_base_url', None)

            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        elif provider == 'anthropic' or 'claude' in model_name.lower():
            api_key = getattr(self.config, 'anthropic_api_key', None) or getattr(self.config, 'api_key', None) or os.getenv('ANTHROPIC_API_KEY')
            base_url = getattr(self.config, 'anthropic_base_url', None)

            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        else:
            # Default to Fireworks
            api_key = getattr(self.config, 'api_key', None) or os.getenv('FIREWORKS_API_KEY')
            return ChatFireworks(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def _convert_messages_to_langchain(self, messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """Convert SWE-CLI message format to LangChain message format.

        Args:
            messages: List of SWE-CLI format messages

        Returns:
            List of LangChain BaseMessage instances
        """
        langchain_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                # Handle tool calls if present
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    # Convert tool calls to LangChain format
                    langchain_tool_calls = []
                    for tool_call in tool_calls:
                        langchain_tool_calls.append(
                            ToolCall(
                                name=tool_call.get("function", {}).get("name", ""),
                                args=json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                                id=tool_call.get("id", ""),
                            )
                        )
                    langchain_messages.append(AIMessage(content=content, tool_calls=langchain_tool_calls))
                else:
                    langchain_messages.append(AIMessage(content=content))
            elif role == "tool":
                # Handle tool results
                tool_call_id = msg.get("tool_call_id", "")
                langchain_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

        return langchain_messages

    def _convert_message_from_langchain(self, message: BaseMessage) -> Dict[str, Any]:
        """Convert LangChain message to SWE-CLI format.

        Args:
            message: LangChain BaseMessage instance

        Returns:
            SWE-CLI format message dictionary
        """
        if isinstance(message, SystemMessage):
            return {"role": "system", "content": message.content}
        elif isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            result = {"role": "assistant", "content": message.content or ""}

            # Convert tool calls if present
            if message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tool_call.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tool_call.get("name", ""),
                                "arguments": json.dumps(tool_call.get("args", {})),
                            },
                        }
                    )
                result["tool_calls"] = tool_calls

            return result
        elif isinstance(message, ToolMessage):
            return {
                "role": "tool",
                "content": message.content,
                "tool_call_id": message.tool_call_id,
            }
        else:
            # Fallback for other message types
            return {"role": "assistant", "content": str(message)}

    def build_system_prompt(self) -> str:
        """Build system prompt for the deep agent.

        Returns:
            System prompt string
        """
        # TODO: Implement proper system prompt building
        return "You are an AI assistant that helps with software engineering tasks."

    def build_tool_schemas(self) -> List[Dict[str, Any]]:
        """Build tool schemas for the deep agent.

        Returns:
            List of tool schema dictionaries
        """
        # TODO: Implement tool schema building using ToolRegistryAdapter
        return []

    
    def call_llm(
        self,
        messages: List[Dict[str, Any]],
        task_monitor: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute an LLM call using the deep agent.

        Args:
            messages: List of messages in SWE-CLI format
            task_monitor: Optional task monitor for interrupt handling

        Returns:
            Response dictionary compatible with existing interface
        """
        try:
            # Check if deep agent is available
            if not self._deep_agent:
                return {
                    "success": False,
                    "error": "Deep Agent not initialized",
                }

            # Convert SWE-CLI messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)

            # Prepare the payload for deep agent
            payload = {
                "messages": langchain_messages
            }

            # Update interrupt monitor with task monitor
            if hasattr(self, '_interrupt_monitor') and self._interrupt_monitor:
                self._interrupt_monitor.task_monitor = task_monitor

            # Check for immediate interrupts
            if task_monitor and hasattr(task_monitor, "should_interrupt") and task_monitor.should_interrupt():
                return {
                    "success": False,
                    "error": "Interrupted by user",
                    "interrupted": True,
                }

            # Invoke the deep agent with interrupt support
            result = self._deep_agent.invoke(payload)

            # Extract the response from deep agent result
            # Deep agents typically return {"messages": [...]}
            if "messages" in result and result["messages"]:
                # Get the last message (assistant's response)
                last_message = result["messages"][-1]

                # Convert back to SWE-CLI format
                swe_message = self._convert_message_from_langchain(last_message)

                # Update token count if task monitor is provided
                if task_monitor and hasattr(task_monitor, "update_tokens"):
                    # Deep agents may not provide token usage, so we'll estimate
                    total_tokens = self._estimate_tokens(messages, swe_message)
                    if total_tokens > 0:
                        task_monitor.update_tokens(total_tokens)

                return {
                    "success": True,
                    "message": swe_message,
                    "content": swe_message.get("content", ""),
                    "tool_calls": swe_message.get("tool_calls"),
                    "usage": None,  # Deep agents may not provide usage info
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid response from Deep Agent: no messages found",
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Deep Agent execution failed: {str(e)}",
            }

    def _estimate_tokens(self, input_messages: List[Dict[str, Any]], output_message: Dict[str, Any]) -> int:
        """Estimate token count for messages when usage info is not available.

        Args:
            input_messages: Input messages in SWE-CLI format
            output_message: Output message in SWE-CLI format

        Returns:
            Estimated total token count
        """
        try:
            import tiktoken

            # Use a common encoding (GPT-3.5-turbo works well for estimation)
            encoding = tiktoken.get_encoding("cl100k_base")

            total_tokens = 0

            # Count input tokens
            for msg in input_messages:
                content = msg.get("content", "")
                total_tokens += len(encoding.encode(content))

                # Add tokens for tool calls if present
                if "tool_calls" in msg:
                    for tool_call in msg["tool_calls"]:
                        func_name = tool_call.get("function", {}).get("name", "")
                        func_args = tool_call.get("function", {}).get("arguments", "{}")
                        total_tokens += len(encoding.encode(f"{func_name}{func_args}"))

            # Count output tokens
            content = output_message.get("content", "")
            total_tokens += len(encoding.encode(content))

            # Add tokens for tool calls in output
            if "tool_calls" in output_message:
                for tool_call in output_message["tool_calls"]:
                    func_name = tool_call.get("function", {}).get("name", "")
                    func_args = tool_call.get("function", {}).get("arguments", "{}")
                    total_tokens += len(encoding.encode(f"{func_name}{func_args}"))

            return total_tokens

        except Exception:
            # Fallback: simple character-based estimation
            # Rough approximation: 1 token ≈ 4 characters
            total_chars = 0

            for msg in input_messages:
                total_chars += len(msg.get("content", ""))

            total_chars += len(output_message.get("content", ""))

            return max(1, total_chars // 4)

    def update_runtime_dependencies(
        self,
        mode_manager: Any,
        approval_manager: Any,
        undo_manager: Any,
        session_manager: Any,
    ) -> None:
        """Update runtime dependencies for the deep agent.

        Args:
            mode_manager: Mode manager instance
            approval_manager: Approval manager instance
            undo_manager: Undo manager instance
            session_manager: Session manager instance
        """
        # Update the tool adapter with runtime dependencies
        if self._tool_adapter and hasattr(self._tool_adapter, 'update_execution_context'):
            self._tool_adapter.update_execution_context(
                mode_manager=mode_manager,
                approval_manager=approval_manager,
                undo_manager=undo_manager,
                session_manager=session_manager,
            )

        # Store dependencies for potential use in other methods
        self._mode_manager = mode_manager
        self._approval_manager = approval_manager
        self._undo_manager = undo_manager
        self._session_manager = session_manager

    def refresh_tools(self) -> None:
        """Refresh the tool adapter when registry changes."""
        if self._tool_adapter:
            # Clear the cached tools to force regeneration
            if hasattr(self._tool_adapter, '_langchain_tools'):
                self._tool_adapter._langchain_tools = None

            # Re-initialize the deep agent with fresh tools
            if self._deep_agent and _DEEPAGENTS_AVAILABLE:
                try:
                    model = self._create_model()
                    fresh_tools = self._tool_adapter.get_langchain_tools()
                    self._deep_agent = create_deep_agent(
                        model=model,
                        tools=fresh_tools
                    )
                except Exception as e:
                    print(f"Warning: Failed to refresh deep agent tools: {e}")

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names.

        Returns:
            List of tool names
        """
        if not self._tool_adapter:
            return []

        try:
            tools = self._tool_adapter.get_langchain_tools()
            return [tool.name for tool in tools]
        except Exception:
            return []

    def get_tool_count(self) -> int:
        """Get number of available tools.

        Returns:
            Number of tools
        """
        return len(self.get_available_tools())

    def interrupt_execution(self) -> bool:
        """Manually trigger an interrupt for the current execution.

        Returns:
            True if interrupt was set successfully
        """
        if hasattr(self, '_interrupt_monitor') and self._interrupt_monitor:
            try:
                self._interrupt_monitor.set_interrupt()
                return True
            except Exception:
                return False
        return False

    def clear_interrupt(self) -> None:
        """Clear any pending interrupt flags."""
        if hasattr(self, '_interrupt_monitor') and self._interrupt_monitor:
            try:
                self._interrupt_monitor.clear_interrupt()
            except Exception:
                pass

    def is_interruptible(self) -> bool:
        """Check if the agent supports interrupt operations.

        Returns:
            True if interrupts are supported
        """
        return hasattr(self, '_interrupt_monitor') and hasattr(self, '_deep_agent')

    def run_sync(
        self,
        message: str,
        deps: Any,
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run the agent synchronously with a message.

        Args:
            message: User message to process
            deps: Runtime dependencies
            message_history: Optional message history

        Returns:
            Response dictionary with content and metadata
        """
        if not self._deep_agent:
            return {
                "content": "Deep Agent not initialized",
                "messages": [],
                "success": False,
                "error": "Deep Agent not available",
            }

        # Build message history
        messages = message_history or []

        # Add system message if not present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.build_system_prompt()})

        # Add user message
        messages.append({"role": "user", "content": message})

        # Convert to LangChain format
        langchain_messages = self._convert_messages_to_langchain(messages)

        print(f"[DEBUG] DeepAgent: Starting stream with {len(langchain_messages)} messages")
        print(f"[DEBUG] DeepAgent: Last message: {messages[-1]}")

        try:
            # Use Deep Agent's stream method
            # We're using the raw deep_agent (not the interruptible wrapper yet)
            payload = {"messages": langchain_messages}

            print("[DEBUG] DeepAgent: Calling deep_agent.stream()...")

            # Collect stream events and track all messages
            collected_content = []
            all_stream_messages = []
            final_ai_message = None
            tool_calls_made = []

            for chunk in self._deep_agent.deep_agent.stream(payload):
                print(f"[DEBUG] DeepAgent: Stream chunk keys: {chunk.keys() if isinstance(chunk, dict) else type(chunk)}")

                if isinstance(chunk, dict):
                    # Check for model responses
                    if "model" in chunk and "messages" in chunk["model"]:
                        for msg in chunk["model"]["messages"]:
                            all_stream_messages.append(msg)

                            # Extract content
                            if hasattr(msg, "content") and msg.content:
                                collected_content.append(str(msg.content))
                                final_ai_message = msg

                            # Check for tool calls
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                print(f"[DEBUG] DeepAgent: Tool calls detected: {len(msg.tool_calls)}")
                                for tc in msg.tool_calls:
                                    tool_calls_made.append(tc)
                                    print(f"[DEBUG] DeepAgent: Tool call - {tc.get('name', 'unknown')}")

                    # Check for tool execution results
                    elif "tools" in chunk and "messages" in chunk["tools"]:
                        print(f"[DEBUG] DeepAgent: Tool execution results received")
                        for msg in chunk["tools"]["messages"]:
                            all_stream_messages.append(msg)
                            if hasattr(msg, "content"):
                                print(f"[DEBUG] DeepAgent: Tool result preview: {str(msg.content)[:100]}...")

                    # Also check direct messages
                    elif "messages" in chunk:
                        messages_value = chunk["messages"]
                        # Handle Overwrite wrapper
                        if hasattr(messages_value, "value"):
                            messages_value = messages_value.value

                        if isinstance(messages_value, list):
                            for msg in messages_value:
                                if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                                    if hasattr(msg, "content") and msg.content:
                                        collected_content.append(str(msg.content))
                                        final_ai_message = msg

            print(f"[DEBUG] DeepAgent: Stream completed")
            print(f"[DEBUG] DeepAgent: - Collected {len(collected_content)} content pieces")
            print(f"[DEBUG] DeepAgent: - Tool calls made: {len(tool_calls_made)}")
            print(f"[DEBUG] DeepAgent: - Total stream messages: {len(all_stream_messages)}")

            # Build final response
            final_content = "\n\n".join(collected_content) if collected_content else "No content received"

            # Add all the stream messages to our message history
            for msg in all_stream_messages:
                swe_msg = self._convert_message_from_langchain(msg)
                if swe_msg:
                    messages.append(swe_msg)

            return {
                "content": final_content,
                "messages": messages,
                "success": True,
                "tool_calls_made": len(tool_calls_made),
            }

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[DEBUG] DeepAgent: Error occurred: {e}")
            print(f"[DEBUG] DeepAgent: Traceback:\n{error_trace}")

            return {
                "content": f"Deep Agent error: {str(e)}",
                "messages": messages,
                "success": False,
                "error": str(e),
            }