"""Legacy alias: hard → progressive_thread."""

from tasks.task_registry import (
    MAX_STEPS_BY_TASK,
    grader_file_for,
    grader_module_for,
)

TASK_ID = "hard"
MAX_STEPS = MAX_STEPS_BY_TASK["hard"]
GRADER_FILE = grader_file_for("progressive_thread")
GRADER_MODULE = grader_module_for("progressive_thread")
