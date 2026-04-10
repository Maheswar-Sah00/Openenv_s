"""Legacy alias: medium → verify_warn_chain."""

from tasks.task_registry import (
    MAX_STEPS_BY_TASK,
    grader_file_for,
    grader_module_for,
)

TASK_ID = "medium"
MAX_STEPS = MAX_STEPS_BY_TASK["medium"]
GRADER_FILE = grader_file_for("verify_warn_chain")
GRADER_MODULE = grader_module_for("verify_warn_chain")
