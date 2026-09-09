"""Merge an explicitly supplied reviewed ledger into the golden-set CSV.

The ledger is separate so every label has a concise audit note and the source
sampling columns remain intact. It accepts both independent human review and
explicitly marked author/AI-assisted review; evaluation reports those states
differently.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

from .taxonomy import INTENTS


def read_rows(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def apply(golden_path: Path, annotation_path: Path) -> int:
    golden = read_rows(golden_path)
    annotations = {row["example_id"]: row for row in read_rows(annotation_path)}
    golden_ids = {row["example_id"] for row in golden}
    if set(annotations) != golden_ids:
        missing = sorted(golden_ids - set(annotations))
        extra = sorted(set(annotations) - golden_ids)
        raise ValueError(f"Annotation IDs do not match golden IDs (missing={missing[:3]}, extra={extra[:3]}).")
    for row in golden:
        annotation = annotations[row["example_id"]]
        if annotation["intent"] not in INTENTS:
            raise ValueError(f"Invalid intent on {row['example_id']}: {annotation['intent']}")
        if annotation["expected_route"] not in {"auto_handle", "escalate"}:
            raise ValueError(f"Invalid route on {row['example_id']}")
        row.update({
            "intent": annotation["intent"],
            "expected_route": annotation["expected_route"],
            "escalation_reason": annotation["escalation_reason"],
            "review_status": annotation["review_status"],
            "review_notes": annotation["review_notes"],
        })
    with golden_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=golden[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(golden)
    return len(golden)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=Path("data/golden_eval.csv"))
    # A required explicit path prevents the historical bootstrap ledger from
    # accidentally overwriting the completed human-reviewed golden file.
    parser.add_argument("--annotations", type=Path, required=True)
    args = parser.parse_args()
    print(f"Applied {apply(args.golden, args.annotations)} labels to {args.golden}.")


if __name__ == "__main__":
    main()
