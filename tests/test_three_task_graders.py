"""Ensure three task-specific grader modules exist and return valid scores."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestThreeTaskGraders(unittest.TestCase):
    def test_each_grader_module_exposes_task_id_and_grade(self) -> None:
        for mod_name, expected_id in (
            ("graders.easy_grader", "easy"),
            ("graders.medium_grader", "medium"),
            ("graders.hard_grader", "hard"),
        ):
            m = importlib.import_module(mod_name)
            self.assertEqual(getattr(m, "TASK_ID"), expected_id, mod_name)
            self.assertTrue(callable(getattr(m, "grade")), f"{mod_name}.grade missing")
            ge = getattr(m, "grade_episode", None)
            if ge is not None:
                self.assertTrue(callable(ge))

    def test_grade_returns_strict_open_interval(self) -> None:
        from graders.easy_grader import grade as grade_easy

        # Pick first scenario id from dataset
        data = json.loads((ROOT / "data" / "scam_dataset.json").read_text(encoding="utf-8"))
        self.assertGreater(len(data), 0)
        sid = data[0]["id"]
        s = grade_easy(["ignore"], sid, None)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)

    def test_openenv_yaml_lists_at_least_three_tasks(self) -> None:
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
            path = ROOT / str(g).replace("\\", "/")
            self.assertTrue(path.is_file(), f"grader file missing: {path}")
        self.assertEqual(set(ids), {"easy", "medium", "hard"})

    def test_task_graders_json_matches(self) -> None:
        doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
        rows = doc.get("tasks", [])
        self.assertGreaterEqual(len(rows), 3)
        for row in rows:
            rel = row.get("grader_file")
            self.assertIsNotNone(rel)
            self.assertTrue((ROOT / rel).is_file())

    def test_task_packages_reference_grader_files(self) -> None:
        from tasks.easy_task import GRADER_FILE as e
        from tasks.hard_task import GRADER_FILE as h
        from tasks.medium_task import GRADER_FILE as m

        for rel in (e, m, h):
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
