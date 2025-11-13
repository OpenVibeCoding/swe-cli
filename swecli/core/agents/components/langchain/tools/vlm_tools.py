"""LangChain tool wrappers for SWE-CLI VLM (Vision Language Model) operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


class AnalyzeImageTool(SWECLIToolWrapper):
    """LangChain wrapper for analyze_image tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="analyze_image",
            description=(
                "Analyze an image using a Vision Language Model. Use this to understand "
                "screenshots, diagrams, charts, code images, or any visual content. "
                "The image_path parameter specifies the path to the image file, and "
                "prompt parameter describes what you want to know about the image. "
                "The model will provide detailed analysis of the visual content."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, image_path: str, prompt: str, **kwargs) -> str:
        """Execute analyze_image tool."""
        return super()._run(image_path=image_path, prompt=prompt, **kwargs)