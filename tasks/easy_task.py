"""Legacy alias: easy → single_turn_triage."""

from tasks.task_registry import (
    MAX_STEPS_BY_TASK,
    grader_file_for,
    grader_module_for,
)

TASK_ID = "easy"
MAX_STEPS = MAX_STEPS_BY_TASK["easy"]
GRADER_FILE = grader_file_for("single_turn_triage")
GRADER_MODULE = grader_module_for("single_turn_triage")
