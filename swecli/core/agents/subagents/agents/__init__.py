"""Subagent specifications."""

from .explorer import EXPLORER_SUBAGENT
from .code_reviewer import CODE_REVIEWER_SUBAGENT
from .test_writer import TEST_WRITER_SUBAGENT
from .documentation import DOCUMENTATION_SUBAGENT

ALL_SUBAGENTS = [
    EXPLORER_SUBAGENT,
    CODE_REVIEWER_SUBAGENT,
    TEST_WRITER_SUBAGENT,
    DOCUMENTATION_SUBAGENT,
]
