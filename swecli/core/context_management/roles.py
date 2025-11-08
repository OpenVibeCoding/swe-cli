"""Native swecli ACE Roles implementation.

This module re-implements the ACE roles (Generator, Reflector, Curator)
natively within swecli, without external dependencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .delta import DeltaBatch
from .playbook import Playbook


def _safe_json_loads(text: str) -> Dict[str, Any]:
    """Safely load JSON, handling common LLM output issues."""
    # Strip markdown code blocks if present
    text = text.strip()

    # Handle opening fence (with or without language identifier)
    if text.startswith("```json"):
        text = text[7:].strip()
    elif text.startswith("```"):
        text = text[3:].strip()

    # Handle closing fence (if present)
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        # Check if this looks like incomplete JSON (truncated response)
        if "Unterminated string" in str(exc) or "Expecting" in str(exc):
            # Try to detect if this is a truncation issue
            if text.count('{') > text.count('}') or text.rstrip().endswith('"'):
                raise ValueError(f"LLM response appears to be truncated JSON. This may indicate the response was cut off mid-generation. Original error: {exc}\nPartial text: {text[:200]}...") from exc

        raise ValueError(f"LLM response is not valid JSON: {exc}\n{text}") from exc
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object from LLM.")
    return data


def _format_optional(value: Optional[str]) -> str:
    """Format optional values for prompts."""
    return value or "(none)"


@dataclass
class GeneratorOutput:
    """Output from the Generator role."""
    reasoning: str
    final_answer: str
    bullet_ids: List[str]
    raw: Dict[str, Any]


@dataclass
class BulletTag:
    """Bullet tagging information from Reflector."""
    id: str
    tag: str


@dataclass
class ReflectorOutput:
    """Output from the Reflector role."""
    reasoning: str
    error_identification: str
    root_cause_analysis: str
    correct_approach: str
    key_insight: str
    bullet_tags: List[BulletTag]
    raw: Dict[str, Any]


@dataclass
class CuratorOutput:
    """Output from the Curator role."""
    delta: DeltaBatch
    raw: Dict[str, Any]


class Generator:
    """
    Produces answers using the current playbook of strategies.

    The Generator is one of three core ACE roles. It takes a question and
    uses the accumulated strategies in the playbook to produce reasoned answers.
    """

    DEFAULT_PROMPT = """You are a helpful assistant with access to a playbook of learned strategies.

## Playbook
{playbook}

## Previous Reflection (if any)
{reflection}

## Question
{question}

## Additional Context
{context}

Using the strategies in the playbook above, provide a clear and helpful answer to the question.

Return your response as a JSON object with these fields:
- reasoning: Your step-by-step thinking process
- bullet_ids: List of playbook bullet IDs that influenced your answer (empty list if none)
- final_answer: Your actual answer to the question

Example response:
{
    "reasoning": "I considered the file operations strategy from the playbook...",
    "bullet_ids": ["fil-00001", "fil-00002"],
    "final_answer": "Based on the playbook strategies, you should first list the directory..."
}"""

    def __init__(
        self,
        llm_client: Any,  # swecli's AnyLLMClient
        prompt_template: str = DEFAULT_PROMPT,
        *,
        max_retries: int = 3,
        retry_prompt: str = "\n\nIMPORTANT: Return ONLY a single valid JSON object. Escape all quotes properly or use single quotes. Do not include any additional text outside the JSON.",
    ) -> None:
        self.llm_client = llm_client
        self.prompt_template = prompt_template
        self.max_retries = max_retries
        self.retry_prompt = retry_prompt

    def generate(
        self,
        *,
        question: str,
        context: Optional[str],
        playbook: Playbook,
        reflection: Optional[str] = None,
        **kwargs: Any,
    ) -> GeneratorOutput:
        """Generate an answer using the playbook strategies."""
        base_prompt = self.prompt_template.format(
            playbook=playbook.as_prompt() or "(empty playbook)",
            reflection=_format_optional(reflection),
            question=question,
            context=_format_optional(context),
        )
        prompt = base_prompt
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                # Convert to chat format for swecli's LLM client
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat_completion(messages)
                response_text = response.get("content", "")

                data = _safe_json_loads(response_text)
                reasoning = str(data.get("reasoning", ""))
                final_answer = str(data.get("final_answer", ""))
                bullet_ids = [
                    str(item)
                    for item in data.get("bullet_ids", [])
                    if isinstance(item, (str, int))
                ]
                return GeneratorOutput(
                    reasoning=reasoning,
                    final_answer=final_answer,
                    bullet_ids=bullet_ids,
                    raw=data,
                )
            except ValueError as err:
                last_error = err
                if attempt + 1 >= self.max_retries:
                    break
                # Append retry instruction to help LLM produce valid JSON
                prompt = base_prompt + self.retry_prompt

        raise RuntimeError("Generator failed to produce valid JSON.") from last_error


class Reflector:
    """
    Analyzes generator outputs to extract lessons and improve strategies.

    The Reflector is the second ACE role. It analyzes the Generator's output
    and environment feedback to understand what went right or wrong, classifying
    which playbook bullets were helpful, harmful, or neutral.
    """

    DEFAULT_PROMPT = """You are analyzing a response to identify what went right or wrong.

## Question
{question}

## Generator's Reasoning
{reasoning}

## Generator's Answer
{prediction}

## Ground Truth (if available)
{ground_truth}

## Feedback/Execution Result
{feedback}

## Relevant Playbook Excerpt
{playbook_excerpt}

Analyze the performance and provide insights. Focus on:
1. What went wrong in the reasoning or approach
2. The root cause of any errors
3. What would have been the correct approach
4. Key insights for future improvements
5. Which playbook bullets were helpful, harmful, or neutral

Return your response as a JSON object with these fields:
- reasoning: Your overall analysis
- error_identification: What specifically went wrong
- root_cause_analysis: Why it went wrong
- correct_approach: What should have been done instead
- key_insight: The most important lesson to learn
- bullet_tags: List of objects with "id" and "tag" fields ("helpful", "harmful", or "neutral")

Example response:
{
    "reasoning": "The generator failed to check file existence...",
    "error_identification": "Attempted to read non-existent file",
    "root_cause_analysis": "Missing validation step before file operations",
    "correct_approach": "Always verify file existence before reading",
    "key_insight": "File operations require existence checks",
    "bullet_tags": [
        {"id": "fil-00001", "tag": "helpful"},
        {"id": "fil-00002", "tag": "harmful"}
    ]
}"""

    def __init__(
        self,
        llm_client: Any,  # swecli's AnyLLMClient
        prompt_template: str = DEFAULT_PROMPT,
        *,
        max_retries: int = 3,
        retry_prompt: str = "\n\nIMPORTANT: Return ONLY a single valid JSON object. Escape all quotes properly or use single quotes. Do not include any additional text outside the JSON.",
    ) -> None:
        self.llm_client = llm_client
        self.prompt_template = prompt_template
        self.max_retries = max_retries
        self.retry_prompt = retry_prompt

    def reflect(
        self,
        *,
        question: str,
        generator_output: GeneratorOutput,
        playbook: Playbook,
        ground_truth: Optional[str] = None,
        feedback: Optional[str] = None,
        **kwargs: Any,
    ) -> ReflectorOutput:
        """Reflect on generator performance."""
        # Create playbook excerpt for referenced bullets
        playbook_excerpt = self._make_playbook_excerpt(playbook, generator_output.bullet_ids)

        base_prompt = self.prompt_template.format(
            question=question,
            reasoning=generator_output.reasoning,
            prediction=generator_output.final_answer,
            ground_truth=_format_optional(ground_truth),
            feedback=_format_optional(feedback),
            playbook_excerpt=playbook_excerpt or "(no bullets referenced)",
        )

        prompt = base_prompt
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                # Convert to chat format for swecli's LLM client
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat_completion(messages)
                response_text = response.get("content", "")

                data = _safe_json_loads(response_text)
                bullet_tags: List[BulletTag] = []
                tags_payload = data.get("bullet_tags", [])
                if isinstance(tags_payload, Sequence):
                    for item in tags_payload:
                        if (
                            isinstance(item, dict)
                            and "id" in item
                            and "tag" in item
                        ):
                            bullet_tags.append(
                                BulletTag(
                                    id=str(item["id"]), tag=str(item["tag"]).lower()
                                )
                            )

                return ReflectorOutput(
                    reasoning=str(data.get("reasoning", "")),
                    error_identification=str(data.get("error_identification", "")),
                    root_cause_analysis=str(data.get("root_cause_analysis", "")),
                    correct_approach=str(data.get("correct_approach", "")),
                    key_insight=str(data.get("key_insight", "")),
                    bullet_tags=bullet_tags,
                    raw=data,
                )
            except ValueError as err:
                last_error = err
                if attempt + 1 >= self.max_retries:
                    break
                # Append retry instruction to help LLM produce valid JSON
                prompt = base_prompt + self.retry_prompt

        raise RuntimeError("Reflector failed to produce valid JSON.") from last_error

    def _make_playbook_excerpt(self, playbook: Playbook, bullet_ids: Sequence[str]) -> str:
        """Create excerpt of playbook bullets for analysis."""
        lines: List[str] = []
        seen = set()
        for bullet_id in bullet_ids:
            if bullet_id in seen:
                continue
            bullet = playbook.get_bullet(bullet_id)
            if bullet:
                seen.add(bullet_id)
                lines.append(f"[{bullet.id}] {bullet.content}")
        return "\n".join(lines)


class Curator:
    """
    Transforms reflections into actionable playbook updates.

    The Curator is the third ACE role. It analyzes the Reflector's output
    and decides how to update the playbook - adding new strategies, updating
    existing ones, or removing harmful patterns.
    """

    DEFAULT_PROMPT = """You are curating a playbook of strategies to improve future performance.

## Progress Summary
{progress}

## Current Playbook Statistics
{stats}

## Reflector Analysis
{reflection}

## Current Playbook Content
{playbook}

## Question Context
{question_context}

Based on the reflector's analysis, decide what changes to make to the playbook. Your goal is to:
1. Add new strategies for successful approaches
2. Update existing strategies with better guidance
3. Tag strategies as helpful/harmful/neutral based on performance
4. Remove strategies that consistently cause problems

Return your response as a JSON object with these fields:
- reasoning: Your overall curation strategy
- operations: List of operations to perform on the playbook

Operations can be:
- ADD: Add new bullet (requires section, content)
- UPDATE: Modify existing bullet (requires bullet_id, optional content)
- TAG: Tag bullet as helpful/harmful/neutral (requires bullet_id, metadata with tag counts)
- REMOVE: Delete bullet (requires bullet_id)

Example response:
{
    "reasoning": "Based on the reflection, we need to add a file validation strategy...",
    "operations": [
        {
            "type": "ADD",
            "section": "file_operations",
            "content": "Always verify file existence before reading or writing"
        },
        {
            "type": "TAG",
            "bullet_id": "fil-00001",
            "metadata": {"helpful": 1}
        },
        {
            "type": "TAG",
            "bullet_id": "fil-00002",
            "metadata": {"harmful": 1}
        }
    ]
}"""

    def __init__(
        self,
        llm_client: Any,  # swecli's AnyLLMClient
        prompt_template: str = DEFAULT_PROMPT,
        *,
        max_retries: int = 3,
        retry_prompt: str = "\n\nIMPORTANT: Return ONLY a single valid JSON object. The JSON must be complete with ALL required fields:\n- reasoning (string)\n- operations (array)\nEscape all quotes properly and ensure the JSON is complete and well-formed.",
    ) -> None:
        self.llm_client = llm_client
        self.prompt_template = prompt_template
        self.max_retries = max_retries
        self.retry_prompt = retry_prompt

    def curate(
        self,
        *,
        reflection: ReflectorOutput,
        playbook: Playbook,
        question_context: str,
        progress: str,
        **kwargs: Any,
    ) -> CuratorOutput:
        """Generate delta operations to update the playbook."""
        base_prompt = self.prompt_template.format(
            progress=progress,
            stats=json.dumps(playbook.stats()),
            reflection=json.dumps(reflection.raw, ensure_ascii=False, indent=2),
            playbook=playbook.as_prompt() or "(empty playbook)",
            question_context=question_context,
        )

        prompt = base_prompt
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                # Convert to chat format for swecli's LLM client
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat_completion(messages)
                response_text = response.get("content", "")

                data = _safe_json_loads(response_text)
                delta = DeltaBatch.from_json(data)
                return CuratorOutput(delta=delta, raw=data)
            except ValueError as err:
                last_error = err
                if attempt + 1 >= self.max_retries:
                    break
                # Append retry instruction to help LLM produce valid JSON
                prompt = base_prompt + self.retry_prompt

        raise RuntimeError("Curator failed to produce valid JSON.") from last_error