"""Clean version of Deep LangChain Agent implementation."""

import json
import os
import time
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from swecli.core.abstract import BaseAgent
from swecli.core.agents.components.langchain.tools import ToolRegistryAdapter
from swecli.models.config import AppConfig

# Import deepagents if available, handle import gracefully
try:
    from deepagents import create_deep_agent
    _DEEPAGENTS_AVAILABLE = True
except ImportError:
    _DEEPAGENTS_AVAILABLE = False


class DeepAgentInterruptMonitor:
    """Monitor for interrupting Deep Agent execution."""

    def __init__(self, task_monitor: Optional[Any] = None):
        """Initialize the interrupt monitor.

        Args:
            task_monitor: Optional task monitor for interrupt checking
        """
        self.task_monitor = task_monitor
        self._should_interrupt = False
        import threading
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

    def request_interrupt(self) -> None:
        """Request interrupt."""
        with self._lock:
            self._should_interrupt = True


class InterruptibleDeepAgent:
    """Wrapper around Deep Agent with interrupt support."""

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
                "success": False,
                "error": "Interrupted by user",
                "interrupted": True,
            }

        # Run Deep Agent in background thread to allow immediate interrupts
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        result_container = {"result": None, "error": None}
        should_interrupt = False

        def run_deep_agent():
            """Run Deep Agent in background thread."""
            try:
                result_container["result"] = self.deep_agent.invoke(payload)
            except Exception as e:
                result_container["error"] = e

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_deep_agent)

            # Check for interrupts while Deep Agent runs
            while future.running():
                # Check interrupt status from monitor
                if hasattr(self.interrupt_monitor, 'task_monitor') and self.interrupt_monitor.task_monitor:
                    should_interrupt = self.interrupt_monitor.task_monitor.should_interrupt()
                elif hasattr(self.interrupt_monitor, 'should_interrupt'):
                    should_interrupt = self.interrupt_monitor.should_interrupt()

                if should_interrupt:
                    # Cancel the future (best effort)
                    future.cancel()
                    return {
                        "success": False,
                        "error": "Interrupted by user",
                        "interrupted": True,
                    }

                # Sleep briefly to avoid busy waiting
                time.sleep(0.1)

            # Get the result (will raise any exceptions)
            try:
                future.result()  # Wait for completion and get any exceptions
            except Exception as e:
                # Check for interrupt-related errors from Deep Agent internals
                error_msg = str(e)
                if "greeting-responder" in error_msg or "agent of type" in error_msg:
                    # This appears to be an interrupt-related error from Deep Agent internals
                    return {
                        "success": False,
                        "error": "Interrupted by user",
                        "interrupted": True,
                    }
                else:
                    # Re-raise other exceptions
                    raise

        # Check for error from thread
        if result_container["error"]:
            raise result_container["error"]

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
        # Set working directory BEFORE calling super() since super() calls _initialize_components()
        self._working_dir = working_dir or os.getcwd()  # Default to current directory
        self._deep_agent = None
        self._tool_adapter = None

        super().__init__(config, tool_registry, mode_manager)

        # Initialize Deep Agent components AFTER base class initialization
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize deep agent components."""
        import logging
        import sys
        logger = logging.getLogger(__name__)

        logger.info("Starting Deep Agent initialization...")

        if not _DEEPAGENTS_AVAILABLE:
            logger.error("deepagents library not available! Please install: pip install deepagents")
            self._deep_agent = None
            return

        try:
            # Create the LangChain model based on provider
            model = self._create_model()

            # Initialize tool adapter
            if self.tool_registry is None:
                logger.error("Tool registry is None!")
                self._deep_agent = None
                return

            self._tool_adapter = ToolRegistryAdapter(self.tool_registry)

            # Get tools
            tools = self._tool_adapter.get_langchain_tools()
            logger.info(f"Got {len(tools)} tools for Deep Agent")

            # Get tool names for interrupt_on config
            tool_names = [tool.name for tool in tools]

            # Create the deep agent with model and tools
            # CRITICAL: Use interrupt_on to prevent automatic tool execution
            # This makes Deep Agent behave like a regular LLM that just returns tool_calls
            interrupt_config = {tool_name: True for tool_name in tool_names}
            deep_agent = create_deep_agent(
                model=model,
                tools=tools,
                interrupt_on=interrupt_config
            )

            # Wrap with interruptible support
            self._interrupt_monitor = DeepAgentInterruptMonitor()
            self._deep_agent = InterruptibleDeepAgent(deep_agent, self._interrupt_monitor)

        except Exception as e:
            logger.error(f"Failed to initialize Deep Agent: {e}", exc_info=True)
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

            from langchain_fireworks import ChatFireworks
            return ChatFireworks(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif provider == 'openai' or 'gpt' in model_name.lower():
            api_key = getattr(self.config, 'openai_api_key', None) or getattr(self.config, 'api_key', None) or os.getenv('OPENAI_API_KEY')
            base_url = getattr(self.config, 'api_base_url', None) or "https://api.openai.com/v1"

            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif provider == 'anthropic' or 'claude' in model_name.lower():
            api_key = getattr(self.config, 'anthropic_api_key', None) or getattr(self.config, 'api_key', None) or os.getenv('ANTHROPIC_API_KEY')

            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def build_system_prompt(self) -> str:
        """Build system prompt for Deep Agent.

        Returns:
            System prompt string
        """
        # Use the same SystemPromptBuilder as SwecliAgent for consistency
        from swecli.core.agents.components.system_prompt import SystemPromptBuilder
        return SystemPromptBuilder(self.tool_registry, self._working_dir).build()

    def build_tool_schemas(self) -> List[Dict[str, Any]]:
        """Build tool schemas for Deep Agent.

        Returns:
            List of tool schemas
        """
        # Deep Agent handles its own tools via ToolRegistryAdapter
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
            NOTE: Returns tool_calls like SwecliAgent, query_processor handles execution
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Check if deep agent is available
            if not self._deep_agent:
                return {
                    "success": False,
                    "error": "Deep Agent not initialized",
                }

            # Connect task_monitor to interrupt monitor for immediate interrupt checking
            if task_monitor and self._interrupt_monitor:
                self._interrupt_monitor.task_monitor = task_monitor

            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)

            # Simple approach: Use invoke() since we interrupt on tools (no auto-execution)
            # This makes Deep Agent behave like a regular LLM that returns tool_calls
            payload = {"messages": langchain_messages}

            logger.info(f"[DEEP_AGENT] Invoking Deep Agent with {len(langchain_messages)} messages")
            result = self._deep_agent.invoke(payload)

        except Exception as e:
            # Check for interrupt-related errors from Deep Agent
            error_msg = str(e)
            if "greeting-responder" in error_msg or "agent of type" in error_msg:
                # This appears to be an interrupt-related error from Deep Agent internals
                logger.info(f"[DEEP_AGENT] Caught interrupt error: {error_msg}")
                return {
                    "success": False,
                    "error": "Interrupted by user",
                    "interrupted": True,
                }
            else:
                # Log and return other errors
                logger.error(f"[DEEP_AGENT] Error: {e}", exc_info=True)
                return {
                    "success": False,
                    "content": f"Deep Agent error: {str(e)}",
                    "messages": messages,
                }

        # Check if response is already in final format (e.g., from interrupt)
        if "success" in result:
            # Response is already in final format (likely from interrupt), return it directly
            return result

        # Extract response like a regular LLM (this is outside the try block)
        all_messages = result.get("messages", [])
        if not all_messages:
            logger.warning("Deep Agent returned no messages")
            return {
                "content": "No response generated",
                "messages": messages,
                "success": False,
                "error": "No messages from Deep Agent",
            }

        # Get the last AI message (should have tool_calls)
        ai_message = None
        tool_calls_for_response = []

        for msg in all_messages:
            if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                ai_message = msg
                # Extract tool calls in SWE-CLI format
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    logger.info(f"[DEEP_AGENT] Found {len(msg.tool_calls)} tool calls")
                    tool_calls_for_response = []
                    for tc in msg.tool_calls:
                        tool_calls_for_response.append({
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {})),
                            },
                        })

        # Convert content
        content = ai_message.content if ai_message else "No content"

        logger.info(f"[DEEP_AGENT] Returning response with {len(tool_calls_for_response)} tool calls")

        # Return in SAME format as SwecliAgent
        return {
            "success": True,
            "message": {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls_for_response if tool_calls_for_response else None,
            },
            "content": content,
            "tool_calls": tool_calls_for_response if tool_calls_for_response else None,  # KEY: Return tool_calls like SwecliAgent
        }

    def run_sync(
        self,
        message: str,
        deps: Any,
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run a synchronous interaction for CLI commands.

        Args:
            message: User message to process
            deps: Dependencies (unused in this implementation)
            message_history: Optional message history to continue from

        Returns:
            Response dictionary with content, messages, and success status
        """
        messages = message_history or []

        # Add system message if not present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.build_system_prompt()})

        # Add user message
        messages.append({"role": "user", "content": message})

        max_iterations = 10
        for _ in range(max_iterations):
            # Check for interrupt request
            if hasattr(self, 'web_state') and self.web_state.is_interrupt_requested():
                self.web_state.clear_interrupt()
                return {
                    "content": "Task interrupted by user",
                    "messages": messages,
                    "success": False,
                    "interrupted": True,
                }

            # Call LLM with Deep Agent
            response = self.call_llm(messages)

            if not response.get("success"):
                return {
                    "content": response.get("error", "Unknown error"),
                    "messages": messages,
                    "success": False,
                }

            message_payload = response.get("message", {}) or {}
            content = response.get("content", message_payload.get("content", ""))
            tool_calls = response.get("tool_calls") or message_payload.get("tool_calls")

            # Add assistant message to history
            assistant_message = {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            }
            messages.append(assistant_message)

            # If no tool calls, we're done
            if not tool_calls:
                return {
                    "content": content,
                    "messages": messages,
                    "success": True,
                }

            # Execute tools using the tool registry
            # NOTE: This mirrors what query_processor does for CLI usage
            for tool_call in tool_calls:
                try:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    # Execute tool through tool registry
                    result = self.tool_registry.execute_tool(
                        tool_name,
                        tool_args,
                        mode_manager=self.mode_manager,
                    )

                    # Add tool result to messages
                    tool_result = result.get("output", "") if result["success"] else f"Error: {result.get('error', 'Tool execution failed')}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })

                except Exception as e:
                    # Add error result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": f"Error executing tool: {str(e)}",
                    })

        # Max iterations reached
        return {
            "content": "Reached maximum iterations without completion",
            "messages": messages,
            "success": False,
        }

    def _convert_messages_to_langchain(self, messages: List[Dict[str, Any]]) -> List[Any]:
        """Convert SWE-CLI messages to LangChain format.

        Args:
            messages: List of messages in SWE-CLI format

        Returns:
            List of LangChain messages
        """
        from langchain_core.messages import (
            HumanMessage,
            SystemMessage,
            AIMessage,
            ToolMessage,
        )

        langchain_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                langchain_messages.append(SystemMessage(content=content or ""))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content or ""))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content or ""))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                langchain_messages.append(ToolMessage(
                    content=content or "",
                    tool_call_id=tool_call_id,
                ))
            else:
                # Skip unknown message types
                continue

        return langchain_messages

    def _estimate_tokens(self, input_messages: List[Dict[str, Any]], output_message: Dict[str, Any]) -> int:
        """Estimate token count for messages when usage info is not available."""
        # Simple estimation: roughly 4 characters per token
        total_chars = 0

        for msg in input_messages:
            total_chars += len(str(msg.get("content", "")))

        total_chars += len(str(output_message.get("content", "")))

        return max(1, total_chars // 4)

    def refresh_tools(self) -> None:
        """Refresh tools from registry."""
        if self._tool_adapter:
            try:
                self._tool_adapter.refresh_tools()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to refresh deep agent tools: {e}", exc_info=True)

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        if self._tool_adapter:
            return self._tool_adapter.get_tool_names()
        return []