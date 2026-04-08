"""Validate scam_dataset.json: unique ids, required fields, label consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = ("id", "difficulty", "true_label", "sender_type", "channel", "messages", "urgency_score")
ALLOW_DIFF = frozenset({"easy", "medium", "hard"})
ALLOW_LABEL = frozenset({"scam", "legitimate"})


def assert_dataset_ok(rows: list[dict]) -> None:
    ids: set[str] = set()
    for i, row in enumerate(rows):
        for k in REQUIRED:
            if k not in row:
                raise ValueError(f"Row {i} missing key {k!r} (id={row.get('id')})")
        if row["difficulty"] not in ALLOW_DIFF:
            raise ValueError(f"Row {i} bad difficulty: {row.get('id')}")
        if row["true_label"] not in ALLOW_LABEL:
            raise ValueError(f"Row {i} bad true_label: {row.get('id')}")
        msgs = row["messages"]
        if not isinstance(msgs, list) or not msgs or not all(isinstance(m, str) and m.strip() for m in msgs):
            raise ValueError(f"Row {i} messages must be non-empty list of strings: {row.get('id')}")
        u = float(row["urgency_score"])
        if not 0.0 <= u <= 1.0:
            raise ValueError(f"Row {i} urgency_score out of [0,1]: {row.get('id')}")
        oid = row["id"]
        if oid in ids:
            raise ValueError(f"Duplicate id: {oid}")
        ids.add(oid)
        otp_idx = row.get("otp_message_index")
        if otp_idx is not None:
            oi = int(otp_idx)
            if oi < 0 or oi >= len(msgs):
                raise ValueError(f"otp_message_index out of range for {oid}")
        if row["difficulty"] == "hard" and row["true_label"] == "scam" and len(msgs) < 2:
            raise ValueError(f"Hard scam should have multi-turn messages: {oid}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    path = root / "data" / "scam_dataset.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert_dataset_ok(rows)
    print(f"OK: {len(rows)} scenarios validated at {path}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
