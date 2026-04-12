"""Legacy alias: medium → verify_warn_chain."""

from tasks.task_registry import (
    CANONICAL_GRADER_FILE,
    CANONICAL_GRADER_MODULE,
    MAX_STEPS_BY_TASK,
)

TASK_ID = "medium"
MAX_STEPS = MAX_STEPS_BY_TASK["medium"]
GRADER_MODULE = CANONICAL_GRADER_MODULE
GRADER_FILE = CANONICAL_GRADER_FILE
