"""Subagent specifications."""

from .code_explorer import CODE_EXPLORER_SUBAGENT
from .web_clone import WEB_CLONE_SUBAGENT
from .scaffolder import SCAFFOLDER_SUBAGENT
from .code_reviewer import CODE_REVIEWER_SUBAGENT
from .test_writer import TEST_WRITER_SUBAGENT
from .documentation import DOCUMENTATION_SUBAGENT

ALL_SUBAGENTS = [
    CODE_EXPLORER_SUBAGENT,
    WEB_CLONE_SUBAGENT,
    SCAFFOLDER_SUBAGENT,
    CODE_REVIEWER_SUBAGENT,
    TEST_WRITER_SUBAGENT,
    DOCUMENTATION_SUBAGENT,
]
