"""Scenario row loading from the local JSON dataset (no live DB)."""

from __future__ import annotations

import json
from pathlib import Path


def _dataset_path(data_path: Path | None = None) -> Path:
    if data_path is not None:
        return data_path
    return Path(__file__).resolve().parent.parent / "data" / "scam_dataset.json"


def load_scenario_by_id(scenario_id: str, data_path: Path | None = None) -> dict:
    path = _dataset_path(data_path)
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row["id"] == scenario_id:
            return row
    raise KeyError(scenario_id)


__all__ = ["load_scenario_by_id", "_dataset_path"]
