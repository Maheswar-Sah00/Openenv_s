"""Legacy alias: hard → progressive_thread."""

from tasks.task_registry import (
    CANONICAL_GRADER_FILE,
    CANONICAL_GRADER_MODULE,
    MAX_STEPS_BY_TASK,
)

TASK_ID = "hard"
MAX_STEPS = MAX_STEPS_BY_TASK["hard"]
GRADER_MODULE = CANONICAL_GRADER_MODULE
GRADER_FILE = CANONICAL_GRADER_FILE
