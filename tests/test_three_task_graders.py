"""Ensure tasks/graders.py, tasks/database.py, manifests, and per-task grader files match Phase 2 checks."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Per-task entry files (unique paths for static validators); logic in tasks/graders.py
EXPECTED_GRADER_BY_TASK_ID = {
    "easy": "tasks/grader_easy.py",
    "medium": "tasks/grader_medium.py",
    "hard": "tasks/grader_hard.py",
}


class TestThreeTaskGraders(unittest.TestCase):
    def test_tasks_graders_module_is_canonical(self) -> None:
        m = importlib.import_module("tasks.graders")
        self.assertEqual(m.TASK_IDS_WITH_GRADERS, ("easy", "medium", "hard"))
        self.assertEqual(set(m.GRADERS.keys()), {"easy", "medium", "hard"})
        self.assertTrue(callable(m.grade_action))
        self.assertTrue(callable(m.grade_episode))
        self.assertTrue(callable(m.grade_easy))
        self.assertTrue(callable(m.grade_medium))
        self.assertTrue(callable(m.grade_hard))

    def test_canonical_graders_py_exists(self) -> None:
        self.assertTrue((ROOT / "tasks" / "graders.py").is_file())

    def test_tasks_database_exists(self) -> None:
        db = importlib.import_module("tasks.database")
        self.assertTrue(hasattr(db, "load_scenario_by_id"))
        self.assertTrue((ROOT / "tasks" / "database.py").is_file())

    def test_graders_package_shim(self) -> None:
        from graders import grade_episode as ge_shim
        from tasks.graders import grade_episode as ge_canon

        self.assertIs(ge_shim, ge_canon)

    def test_grade_returns_strict_open_interval(self) -> None:
        from tasks.graders import grade_action

        data = json.loads((ROOT / "data" / "scam_dataset.json").read_text(encoding="utf-8"))
        self.assertGreater(len(data), 0)
        sid = data[0]["id"]
        s = grade_action("easy", ["ignore"], sid, None)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)

    def test_openenv_yaml_lists_three_tasks_with_distinct_grader_paths(self) -> None:
        raw = (ROOT / "openenv.yaml").read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)
        self.assertIsInstance(doc, dict)
        tasks = doc.get("tasks")
        self.assertIsInstance(tasks, list, "openenv.yaml should define top-level 'tasks' list")
        self.assertGreaterEqual(len(tasks), 3)
        ids = []
        paths: set[str] = set()
        for row in tasks:
            self.assertIsInstance(row, dict)
            tid = row.get("id") or row.get("task_id")
            self.assertIsNotNone(tid)
            ids.append(tid)
            g = row.get("grader") or row.get("grader_file")
            self.assertIsNotNone(g, f"task {tid} missing grader path")
            expected = EXPECTED_GRADER_BY_TASK_ID.get(tid)
            self.assertIsNotNone(expected, f"unexpected task id {tid}")
            norm = g.replace("\\", "/")
            self.assertEqual(
                norm,
                expected,
                f"task {tid} should point at {expected}, got {g}",
            )
            paths.add(norm)
            path = ROOT / norm
            self.assertTrue(path.is_file(), f"grader file missing: {path}")
        self.assertEqual(set(ids), {"easy", "medium", "hard"})
        self.assertEqual(len(paths), 3, "openenv tasks should use three distinct grader file paths")

    def test_task_graders_json_matches(self) -> None:
        doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
        rows = doc.get("tasks", [])
        self.assertGreaterEqual(len(rows), 3)
        files: set[str] = set()
        for row in rows:
            tid = row.get("task_id")
            rel = row.get("grader_file")
            self.assertIsNotNone(tid)
            expected = EXPECTED_GRADER_BY_TASK_ID.get(tid)
            self.assertIsNotNone(expected)
            self.assertEqual(rel.replace("\\", "/"), expected)
            self.assertTrue((ROOT / rel).is_file())
            files.add(rel.replace("\\", "/"))
        self.assertEqual(len(files), 3)

    def test_task_packages_reference_per_task_grader_files(self) -> None:
        from tasks.easy_task import GRADER_FILE as e
        from tasks.hard_task import GRADER_FILE as h
        from tasks.medium_task import GRADER_FILE as m

        got = {e.replace("\\", "/"), m.replace("\\", "/"), h.replace("\\", "/")}
        self.assertEqual(got, set(EXPECTED_GRADER_BY_TASK_ID.values()))
        for rel in (e, m, h):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_per_task_grader_modules_export_grade_episode(self) -> None:
        from tasks.grader_easy import grade_episode as ge
        from tasks.grader_medium import grade_episode as gm
        from tasks.grader_hard import grade_episode as gh
        from tasks.graders import grade_easy, grade_hard, grade_medium

        self.assertIs(ge, grade_easy)
        self.assertIs(gm, grade_medium)
        self.assertIs(gh, grade_hard)


if __name__ == "__main__":
    unittest.main()
