"""LangChain LLM adapter to replace custom HTTP client."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List, Optional, Sequence, Union

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
from langchain_core.outputs import ChatResult, LLMResult
from langchain_fireworks import ChatFireworks
from langchain_openai import ChatOpenAI

from swecli.core.agents.components.http_client import HttpResult
from swecli.core.agents.components.langchain.tools import ToolRegistryAdapter

_LOG = logging.getLogger(__name__)


class LangChainInterruptMonitor:
    """Monitor for checking interrupt requests during LangChain operations."""

    def __init__(self, task_monitor: Any):
        self.task_monitor = task_monitor
        self._should_interrupt = False

    def should_interrupt(self) -> bool:
        """Check if interrupt has been requested."""
        if not self.task_monitor:
            return False

        if hasattr(self.task_monitor, "should_interrupt"):
            return self.task_monitor.should_interrupt()
        elif hasattr(self.task_monitor, "is_interrupted"):
            return self.task_monitor.is_interrupted()

        return False


class InterruptibleChatModel:
    """Wrapper for LangChain models that supports interrupt handling."""

    def __init__(self, model: BaseChatModel):
        self.model = model

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        **kwargs: Any,
    ) -> Any:
        """Invoke the model with interrupt support."""
        # Extract task_monitor from kwargs if present, remove before passing to model
        task_monitor = kwargs.pop("task_monitor", None)

        if task_monitor is None:
            # Fast path - no interrupt monitoring needed
            return self.model.invoke(messages, **kwargs)

        # Interrupt-aware execution path
        result_container: Dict[str, Any] = {"result": None, "error": None}
        exception_container: Dict[str, Any] = {"exception": None}

        def make_request() -> None:
            try:
                result_container["result"] = self.model.invoke(messages, **kwargs)
            except Exception as exc:
                exception_container["exception"] = exc

        request_thread = threading.Thread(target=make_request, daemon=True)
        request_thread.start()

        monitor = LangChainInterruptMonitor(task_monitor)

        # Use event-based waiting for instant interrupt response
        while request_thread.is_alive():
            # Wait for interrupt event or timeout - this wakes up IMMEDIATELY on interrupt
            if hasattr(monitor.task_monitor, 'wait_for_interrupt'):
                interrupted = monitor.task_monitor.wait_for_interrupt(timeout=0.01)
                if interrupted:
                    # Interrupt was signaled - stop immediately
                    from langchain_core.outputs import ChatResult
                    return ChatResult(
                        generations=[],
                        llm_output={"error": "Interrupted by user"},
                    )
            else:
                # Fallback to polling if wait_for_interrupt not available
                if monitor.should_interrupt():
                    from langchain_core.outputs import ChatResult
                    return ChatResult(
                        generations=[],
                        llm_output={"error": "Interrupted by user"},
                    )
                request_thread.join(timeout=0.01)

        if exception_container["exception"]:
            raise exception_container["exception"]

        return result_container["result"]


class LangChainLLMAdapter:
    """Adapter for LangChain LLMs that maintains compatibility with existing interface."""

    def __init__(self, config: Any):
        """Initialize the adapter with configuration.

        Args:
            config: AppConfig instance containing model configuration
        """
        self.config = config
        self._models: Dict[str, InterruptibleChatModel] = {}
        self._response_cleaner = getattr(config, '_response_cleaner', None)
        self._tool_adapter: Optional[ToolRegistryAdapter] = None

    def set_tool_registry(self, tool_registry: Any) -> None:
        """Set the tool registry for LangChain tool integration.

        Args:
            tool_registry: SWE-CLI tool registry instance
        """
        self._tool_adapter = ToolRegistryAdapter(tool_registry)

    def get_langchain_tools(self) -> list:
        """Get LangChain-compatible tools.

        Returns:
            List of LangChain BaseTool instances
        """
        if self._tool_adapter is None:
            return []
        return self._tool_adapter.get_langchain_tools()

    def get_model(self, model_type: str = "normal") -> InterruptibleChatModel:
        """Get LangChain model for the specified type.

        Args:
            model_type: Type of model ("normal", "thinking", "vision")

        Returns:
            InterruptibleChatModel instance
        """
        if model_type not in self._models:
            self._models[model_type] = self._create_model(model_type)
        return self._models[model_type]

    def _create_model(self, model_type: str) -> InterruptibleChatModel:
        """Create LangChain model based on configuration.

        Args:
            model_type: Type of model to create

        Returns:
            InterruptibleChatModel wrapping the LangChain model
        """
        # Get model configuration from config
        model_name = getattr(self.config, f"{model_type}_model", None) or getattr(self.config, "model", None)
        if not model_name:
            model_name = "accounts/fireworks/models/llama-v3p1-8b-instruct"  # Default fallback

        # Determine provider from model name
        if "fireworks" in model_name or "accounts/fireworks" in model_name:
            base_model = self._create_fireworks_model(model_name)
        elif "gpt" in model_name.lower() or "openai" in model_name.lower():
            base_model = self._create_openai_model(model_name)
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            base_model = self._create_anthropic_model(model_name)
        else:
            # Default to Fireworks for unknown models
            base_model = self._create_fireworks_model(model_name)

        return InterruptibleChatModel(base_model)

    def _create_fireworks_model(self, model_name: str) -> ChatFireworks:
        """Create a Fireworks model instance."""
        api_key = getattr(self.config, "fireworks_api_key", None)
        if not api_key:
            import os
            api_key = os.getenv("FIREWORKS_API_KEY")

        base_url = getattr(self.config, "api_base_url", None)
        if not base_url:
            base_url = "https://api.fireworks.ai/inference/v1"

        return ChatFireworks(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=getattr(self.config, "temperature", 0.7),
            max_tokens=getattr(self.config, "max_tokens", 4096),
            timeout=getattr(self.config, "timeout", 300),
        )

    def _create_openai_model(self, model_name: str) -> ChatOpenAI:
        """Create an OpenAI model instance."""
        api_key = getattr(self.config, "openai_api_key", None)
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")

        base_url = getattr(self.config, "openai_base_url", None)

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=getattr(self.config, "temperature", 0.7),
            max_tokens=getattr(self.config, "max_tokens", 4096),
            timeout=getattr(self.config, "timeout", 300),
        )

    def _create_anthropic_model(self, model_name: str) -> ChatAnthropic:
        """Create an Anthropic model instance."""
        api_key = getattr(self.config, "anthropic_api_key", None)
        if not api_key:
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY")

        base_url = getattr(self.config, "anthropic_base_url", None)

        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=getattr(self.config, "temperature", 0.7),
            max_tokens=getattr(self.config, "max_tokens", 4096),
            timeout=getattr(self.config, "timeout", 300),
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
                    # Handle LangChain ToolCall objects
                    if hasattr(tool_call, 'name') and hasattr(tool_call, 'args'):
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
                    else:
                        # Handle dict format (fallback)
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

    def call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        *,
        task_monitor: Optional[Any] = None,
        model_type: str = "normal",
    ) -> Dict[str, Any]:
        """Execute an LLM call using LangChain while maintaining existing interface.

        Args:
            messages: List of messages in SWE-CLI format
            tools: Optional list of tool schemas
            task_monitor: Optional task monitor for interrupt handling
            model_type: Type of model to use ("normal", "thinking", "vision")

        Returns:
            Response dictionary compatible with existing interface
        """
        try:
            # Get the LangChain model
            langchain_model = self.get_model(model_type)

            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)

            # Prepare kwargs for the model call (exclude task_monitor)
            kwargs = {}

            # Handle tools - prefer LangChain tools if available, fall back to schemas
            if self._tool_adapter is not None:
                # Use LangChain tools directly
                langchain_tools = self._tool_adapter.get_langchain_tools()
                if langchain_tools:
                    langchain_model = langchain_model.model.bind_tools(langchain_tools)
                    kwargs["tools"] = langchain_tools
            elif tools:
                # Fall back to traditional tool schemas
                langchain_model = langchain_model.model.bind_tools(tools)
                kwargs["tools"] = tools

            # Make the LLM call with interrupt support
            # task_monitor is handled by our InterruptibleChatModel wrapper
            kwargs["task_monitor"] = task_monitor
            result = langchain_model.invoke(langchain_messages, **kwargs)

            # Check for interruption
            if hasattr(result, "llm_output") and result.llm_output and "error" in result.llm_output:
                return {
                    "success": False,
                    "error": result.llm_output["error"],
                    "interrupted": True,
                }

            # Extract the AI message from the result
            # Handle both ChatResult (multiple generations) and direct AIMessage
            if hasattr(result, 'generations'):
                # ChatResult with generations
                if not result.generations:
                    return {
                        "success": False,
                        "error": "No generations returned from model",
                    }
                ai_message = result.generations[0].message
            else:
                # Direct AIMessage
                ai_message = result

            # Convert back to SWE-CLI format
            message_dict = self._convert_message_from_langchain(ai_message)

            # Apply response cleaning if available
            content = message_dict.get("content")
            if content and self._response_cleaner:
                content = self._response_cleaner.clean(content)
                message_dict["content"] = content

            # Extract usage information if available
            usage = None
            if hasattr(result, "llm_output") and result.llm_output:
                usage = result.llm_output.get("token_usage")

            # Update token count if task monitor is provided
            if task_monitor and usage and "total_tokens" in usage:
                total_tokens = usage.get("total_tokens", 0)
                if total_tokens > 0 and hasattr(task_monitor, "update_tokens"):
                    task_monitor.update_tokens(total_tokens)

            return {
                "success": True,
                "message": message_dict,
                "content": message_dict.get("content"),
                "tool_calls": message_dict.get("tool_calls"),
                "usage": usage,
            }

        except Exception as e:
            _LOG.exception("Error during LangChain LLM call")
            return {
                "success": False,
                "error": f"LangChain LLM call failed: {str(e)}",
            }

    def post_json(self, payload: Dict[str, Any], *, task_monitor: Optional[Any] = None) -> HttpResult:
        """Legacy compatibility method that mimics the original HTTP client interface.

        Args:
            payload: Request payload in the format expected by the original HTTP client
            task_monitor: Optional task monitor for interrupt handling

        Returns:
            HttpResult compatible with original interface
        """
        try:
            # Extract parameters from payload
            messages = payload.get("messages", [])
            tools = payload.get("tools")

            # Determine model type (default to "normal")
            model_type = "normal"
            model_name = payload.get("model", "")
            if "thinking" in model_name.lower():
                model_type = "thinking"
            elif "vision" in model_name.lower() or "image" in model_name.lower():
                model_type = "vision"

            # Call the LLM using the LangChain adapter
            response = self.call_llm(
                messages=messages,
                tools=tools,
                task_monitor=task_monitor,
                model_type=model_type,
            )

            if not response["success"]:
                return HttpResult(
                    success=False,
                    error=response.get("error", "Unknown error"),
                    interrupted=response.get("interrupted", False),
                )

            # Convert the response back to the format expected by callers
            mock_response = MockResponse(
                status_code=200,
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": response.get("content"),
                                "tool_calls": response.get("tool_calls"),
                            }
                        }
                    ],
                    "usage": response.get("usage"),
                },
            )

            return HttpResult(success=True, response=mock_response)

        except Exception as e:
            return HttpResult(success=False, error=str(e))


class MockResponse:
    """Mock response object to maintain compatibility with existing code."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]):
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        """Return the JSON data."""
        return self._json_data

    @property
    def text(self) -> str:
        """Return the text representation of the JSON data."""
        return json.dumps(self._json_data)