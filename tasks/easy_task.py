"""Legacy alias: easy → single_turn_triage."""

from tasks.task_registry import (
    CANONICAL_GRADER_FILE,
    CANONICAL_GRADER_MODULE,
    MAX_STEPS_BY_TASK,
)

TASK_ID = "easy"
MAX_STEPS = MAX_STEPS_BY_TASK["easy"]
GRADER_MODULE = CANONICAL_GRADER_MODULE
GRADER_FILE = CANONICAL_GRADER_FILE
