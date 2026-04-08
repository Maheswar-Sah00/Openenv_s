#!/usr/bin/env python3
"""
Merge external CSV / JSON (e.g. Kaggle SMS spam, phishing email exports) into data/scam_dataset.json.

You must download datasets yourself and respect their licenses. This tool only maps rows into the
env schema (single-turn, difficulty=easy by default) and dedupes by message text.

Examples:
  python scripts/merge_external_datasets.py \\
    --input ~/Downloads/sms.csv --text-column v2 --label-column v1 \\
    --scam-values spam,1 --legit-values ham,0

  python scripts/merge_external_datasets.py \\
    --input a.jsonl b.jsonl --format jsonl --json-text message --json-label label

  python scripts/merge_external_datasets.py --input extra_scenarios.json --format native
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validate_dataset import assert_dataset_ok

URL_RE = re.compile(r"https?://|www\.|bit\.ly/|\.ru/|\.tk\b|upi\.pay|\.xyz\b", re.I)
URGENT_WORDS = (
    "urgent",
    "immediately",
    "blocked",
    "expire",
    "otp",
    "verify now",
    "suspend",
    "last chance",
    "act now",
    "click",
)


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _hash_id(source_slug: str, text: str) -> str:
    h = hashlib.sha256(f"{source_slug}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"ext_{source_slug}_{h}"


def _heuristic_urgency(text: str) -> float:
    low = text.lower()
    score = 0.45
    for w in URGENT_WORDS:
        if w in low:
            score += 0.06
    if URL_RE.search(text):
        score += 0.08
    return max(0.0, min(1.0, score))


def _link_present(text: str) -> bool:
    return bool(URL_RE.search(text))


def _parse_values(s: str) -> set[str]:
    return {x.strip().lower() for x in s.split(",") if x.strip()}


def _label_to_truth(raw: str, scam_vals: set[str], legit_vals: set[str]) -> str | None:
    v = raw.strip().lower()
    if v in scam_vals:
        return "scam"
    if v in legit_vals:
        return "legitimate"
    return None


def row_from_text(
    text: str,
    true_label: str,
    *,
    source_slug: str,
    difficulty: str,
    channel: str,
    language: str,
    tags: list[str],
) -> dict | None:
    t = (text or "").strip()
    if len(t) < 3:
        return None
    t = t[:4000]
    return {
        "id": _hash_id(source_slug, _norm_text(t)),
        "difficulty": difficulty,
        "true_label": true_label,
        "channel": channel,
        "language": language,
        "sender_type": "unknown",
        "message": t,
        "messages": [t],
        "link_present": _link_present(t),
        "urgency_score": _heuristic_urgency(t),
        "tags": tags + ["external_import", source_slug],
    }


def load_csv_rows(
    path: Path,
    text_col: str,
    label_col: str,
    scam_vals: set[str],
    legit_vals: set[str],
    encoding: str,
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    with path.open(newline="", encoding=encoding, errors="replace") as f:
        reader = csv.DictReader(f)
        if text_col not in reader.fieldnames or label_col not in reader.fieldnames:
            raise ValueError(f"{path}: columns missing — have {reader.fieldnames}, need {text_col!r} {label_col!r}")
        for row in reader:
            txt = (row.get(text_col) or "").strip()
            lab = row.get(label_col) or ""
            truth = _label_to_truth(lab, scam_vals, legit_vals)
            if truth is None or not txt:
                continue
            out.append((txt, truth))
    return out


def load_jsonl_rows(
    path: Path,
    text_key: str,
    label_key: str,
    scam_vals: set[str],
    legit_vals: set[str],
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        txt = str(obj.get(text_key) or "").strip()
        lab = str(obj.get(label_key) or "")
        truth = _label_to_truth(lab, scam_vals, legit_vals)
        if truth is None or not txt:
            continue
        out.append((txt, truth))
    return out


def load_json_array_rows(
    path: Path,
    text_key: str,
    label_key: str,
    scam_vals: set[str],
    legit_vals: set[str],
) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: JSON root must be an array")
    out: list[tuple[str, str]] = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        txt = str(obj.get(text_key) or "").strip()
        lab = str(obj.get(label_key) or "")
        truth = _label_to_truth(lab, scam_vals, legit_vals)
        if truth is None or not txt:
            continue
        out.append((txt, truth))
    return out


def load_native_scenarios(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "scenarios" in data:
        data = data["scenarios"]
    if not isinstance(data, list):
        raise ValueError(f"{path}: native format expects JSON array of scenario objects")
    return list(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge external datasets into scam_dataset.json")
    parser.add_argument("--base", type=Path, default=ROOT / "data" / "scam_dataset.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "scam_dataset.json")
    parser.add_argument("--input", type=Path, action="append", dest="inputs", required=True)
    parser.add_argument(
        "--format",
        choices=("auto", "csv", "jsonl", "json_array", "native"),
        default="auto",
    )
    parser.add_argument("--text-column", default="text", help="CSV column for message body")
    parser.add_argument("--label-column", default="label", help="CSV column for class label")
    parser.add_argument("--json-text", default="text", help="JSON/JSONL key for message")
    parser.add_argument("--json-label", default="label", help="JSON/JSONL key for label")
    parser.add_argument(
        "--scam-values",
        default="spam,scam,1,fraud,phishing,malicious",
        help="Comma-separated label values mapped to true_label=scam (case-insensitive)",
    )
    parser.add_argument(
        "--legit-values",
        default="ham,legitimate,0,benign,ok,good",
        help="Comma-separated label values mapped to true_label=legitimate",
    )
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"), default="easy")
    parser.add_argument("--channel", default="sms", choices=("sms", "email", "whatsapp", "in_app"))
    parser.add_argument("--language", default="en")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    scam_vals = _parse_values(args.scam_values)
    legit_vals = _parse_values(args.legit_values)
    overlap = scam_vals & legit_vals
    if overlap:
        print(f"Error: scam and legit value sets overlap: {overlap}", file=sys.stderr)
        raise SystemExit(1)

    base_rows: list[dict] = json.loads(args.base.read_text(encoding="utf-8"))
    seen_text: set[str] = set()
    for r in base_rows:
        if r.get("messages") and isinstance(r["messages"], list) and r["messages"]:
            seen_text.add(_norm_text(str(r["messages"][0])))

    existing_ids = {r["id"] for r in base_rows}
    added = 0
    skipped_dup = 0
    skipped_fmt = 0

    for inp in args.inputs:
        if not inp.is_file():
            print(f"Error: file not found: {inp}", file=sys.stderr)
            raise SystemExit(1)

        fmt = args.format
        if fmt == "auto":
            suf = inp.suffix.lower()
            if suf == ".csv":
                fmt = "csv"
            elif suf == ".jsonl":
                fmt = "jsonl"
            elif suf == ".json":
                peek = inp.read_text(encoding="utf-8", errors="replace")[:200].lstrip()
                if peek.startswith("["):
                    fmt = "json_array"
                else:
                    fmt = "jsonl"
            else:
                print(f"Error: cannot infer format for {inp}; set --format", file=sys.stderr)
                raise SystemExit(1)

        slug = re.sub(r"[^a-z0-9]+", "_", inp.stem.lower()).strip("_")[:40] or "file"

        if fmt == "native":
            for row in load_native_scenarios(inp):
                if not isinstance(row, dict):
                    skipped_fmt += 1
                    continue
                rid = row.get("id")
                if not rid:
                    skipped_fmt += 1
                    continue
                if rid in existing_ids:
                    skipped_dup += 1
                    continue
                msgs = row.get("messages")
                if isinstance(msgs, list) and msgs:
                    nt = _norm_text(str(msgs[0]))
                else:
                    nt = _norm_text(str(row.get("message") or ""))
                if not nt:
                    skipped_fmt += 1
                    continue
                if nt in seen_text:
                    skipped_dup += 1
                    continue
                base_rows.append(row)
                existing_ids.add(str(rid))
                seen_text.add(nt)
                added += 1
            continue

        pairs: list[tuple[str, str]]
        if fmt == "csv":
            pairs = load_csv_rows(
                inp, args.text_column, args.label_column, scam_vals, legit_vals, args.encoding
            )
        elif fmt == "jsonl":
            pairs = load_jsonl_rows(inp, args.json_text, args.json_label, scam_vals, legit_vals)
        elif fmt == "json_array":
            pairs = load_json_array_rows(inp, args.json_text, args.json_label, scam_vals, legit_vals)
        else:
            raise SystemExit(1)

        for txt, truth in pairs:
            nt = _norm_text(txt)
            if nt in seen_text:
                skipped_dup += 1
                continue
            rec = row_from_text(
                txt,
                truth,
                source_slug=slug,
                difficulty=args.difficulty,
                channel=args.channel,
                language=args.language,
                tags=[],
            )
            if rec is None:
                skipped_fmt += 1
                continue
            if rec["id"] in existing_ids:
                skipped_dup += 1
                continue
            base_rows.append(rec)
            existing_ids.add(rec["id"])
            seen_text.add(nt)
            added += 1

    print(
        f"Merged: +{added} new scenarios, skipped {skipped_dup} duplicates, skipped {skipped_fmt} bad/short rows. "
        f"Total {len(base_rows)}."
    )

    if args.dry_run:
        print("Dry run: not writing output.")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(base_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert_dataset_ok(base_rows)
    print(f"OK: validated and wrote {args.output}")


if __name__ == "__main__":
    main()
