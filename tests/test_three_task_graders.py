"""Ensure canonical tasks/graders.py and three tasks are wired for Phase 2 checks."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestThreeTaskGraders(unittest.TestCase):
    def test_tasks_graders_module_is_canonical(self) -> None:
        m = importlib.import_module("tasks.graders")
        self.assertEqual(m.TASK_IDS_WITH_GRADERS, ("easy", "medium", "hard"))
        self.assertTrue(callable(m.grade_action))
        self.assertTrue(callable(m.grade_episode))
        self.assertTrue(callable(m._grade_easy))
        self.assertTrue(callable(m._grade_medium))
        self.assertTrue(callable(m._grade_hard))

    def test_legacy_grader_wrappers_still_work(self) -> None:
        for mod_name, expected_id in (
            ("graders.easy_grader", "easy"),
            ("graders.medium_grader", "medium"),
            ("graders.hard_grader", "hard"),
        ):
            m = importlib.import_module(mod_name)
            self.assertEqual(getattr(m, "TASK_ID"), expected_id, mod_name)
            self.assertTrue(callable(getattr(m, "grade")), f"{mod_name}.grade missing")

    def test_grade_returns_strict_open_interval(self) -> None:
        from tasks.graders import grade_action

        data = json.loads((ROOT / "data" / "scam_dataset.json").read_text(encoding="utf-8"))
        self.assertGreater(len(data), 0)
        sid = data[0]["id"]
        s = grade_action("easy", ["ignore"], sid, None)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)

    def test_openenv_yaml_lists_three_tasks_with_tasks_graders_py(self) -> None:
        raw = (ROOT / "openenv.yaml").read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)
        self.assertIsInstance(doc, dict)
        tasks = doc.get("tasks")
        self.assertIsInstance(tasks, list, "openenv.yaml should define top-level 'tasks' list")
        self.assertGreaterEqual(len(tasks), 3)
        ids = []
        for row in tasks:
            self.assertIsInstance(row, dict)
            tid = row.get("id") or row.get("task_id")
            self.assertIsNotNone(tid)
            ids.append(tid)
            g = row.get("grader") or row.get("grader_file")
            self.assertIsNotNone(g, f"task {tid} missing grader path")
            self.assertEqual(
                g.replace("\\", "/"),
                "tasks/graders.py",
                f"task {tid} should point at tasks/graders.py, got {g}",
            )
            path = ROOT / str(g).replace("\\", "/")
            self.assertTrue(path.is_file(), f"grader file missing: {path}")
        self.assertEqual(set(ids), {"easy", "medium", "hard"})

    def test_task_graders_json_matches(self) -> None:
        doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
        rows = doc.get("tasks", [])
        self.assertGreaterEqual(len(rows), 3)
        for row in rows:
            rel = row.get("grader_file")
            self.assertEqual(rel.replace("\\", "/"), "tasks/graders.py")
            self.assertTrue((ROOT / rel).is_file())

    def test_task_packages_reference_tasks_graders(self) -> None:
        from tasks.easy_task import GRADER_FILE as e
        from tasks.hard_task import GRADER_FILE as h
        from tasks.medium_task import GRADER_FILE as m

        for rel in (e, m, h):
            self.assertEqual(rel.replace("\\", "/"), "tasks/graders.py")
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
