"""Ensure tasks/graders.py, task_registry, and manifests match (single grader file, six tasks)."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

import yaml

from tasks.task_registry import (
    CANONICAL_GRADER_FILE,
    CANONICAL_TASK_IDS,
    grader_file_for,
    resolve_task_id,
    scenario_in_task_pool,
)

ROOT = Path(__file__).resolve().parents[1]


class TestTaskGraders(unittest.TestCase):
    def test_tasks_graders_module_is_canonical(self) -> None:
        m = importlib.import_module("tasks.graders")
        self.assertEqual(set(m.TASK_IDS_WITH_GRADERS), set(CANONICAL_TASK_IDS))
        self.assertEqual(set(m.GRADERS.keys()), set(CANONICAL_TASK_IDS))
        self.assertTrue(callable(m.grade_action))
        self.assertTrue(callable(m.grade_episode))

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
        s = grade_action("single_turn_triage", ["ignore"], sid, None)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)

    def test_legacy_aliases_resolve(self) -> None:
        self.assertEqual(resolve_task_id("easy"), "single_turn_triage")
        self.assertEqual(resolve_task_id("medium"), "verify_warn_chain")
        self.assertEqual(resolve_task_id("hard"), "progressive_thread")

    def test_openenv_yaml_lists_six_tasks_all_use_tasks_graders_py(self) -> None:
        raw = (ROOT / "openenv.yaml").read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)
        self.assertIsInstance(doc, dict)
        tasks = doc.get("tasks")
        self.assertIsInstance(tasks, list, "openenv.yaml should define top-level 'tasks' list")
        self.assertGreaterEqual(len(tasks), 6)
        ids = []
        paths: set[str] = set()
        for row in tasks:
            self.assertIsInstance(row, dict)
            tid = row.get("id") or row.get("task_id")
            self.assertIsNotNone(tid)
            ids.append(tid)
            g = row.get("grader") or row.get("grader_file")
            self.assertIsNotNone(g, f"task {tid} missing grader path")
            norm = g.replace("\\", "/")
            self.assertEqual(
                norm,
                grader_file_for(tid),
                f"task {tid} should point at {CANONICAL_GRADER_FILE}, got {g}",
            )
            paths.add(norm)
            path = ROOT / norm
            self.assertTrue(path.is_file(), f"grader file missing: {path}")
        self.assertEqual(set(ids), set(CANONICAL_TASK_IDS))
        self.assertEqual(paths, {CANONICAL_GRADER_FILE})

    def test_task_graders_json_matches(self) -> None:
        doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
        rows = doc.get("tasks", [])
        self.assertGreaterEqual(len(rows), 6)
        files: set[str] = set()
        for row in rows:
            tid = row.get("task_id")
            rel = row.get("grader_file")
            mod = row.get("grader_module")
            self.assertIsNotNone(tid)
            self.assertEqual(rel.replace("\\", "/"), CANONICAL_GRADER_FILE)
            self.assertEqual(mod, "tasks.graders")
            self.assertTrue((ROOT / rel).is_file())
            files.add(rel.replace("\\", "/"))
        self.assertEqual(files, {CANONICAL_GRADER_FILE})

    def test_legacy_task_packages_reference_graders_py(self) -> None:
        from tasks.easy_task import GRADER_FILE as e
        from tasks.hard_task import GRADER_FILE as h
        from tasks.medium_task import GRADER_FILE as m

        for rel in (e, m, h):
            self.assertEqual(rel.replace("\\", "/"), CANONICAL_GRADER_FILE)
            self.assertEqual(grader_file_for(), CANONICAL_GRADER_FILE)

    def test_graders_exports_per_task_callables(self) -> None:
        from tasks.graders import grade_single_turn_triage, grade_verify_warn_chain

        self.assertTrue(callable(grade_single_turn_triage))
        self.assertTrue(callable(grade_verify_warn_chain))

    def test_each_task_pool_non_empty(self) -> None:
        data = json.loads((ROOT / "data" / "scam_dataset.json").read_text(encoding="utf-8"))
        for tid in CANONICAL_TASK_IDS:
            n = sum(1 for row in data if scenario_in_task_pool(row, tid))
            self.assertGreater(n, 0, f"no scenarios for task {tid}")


if __name__ == "__main__":
    unittest.main()
