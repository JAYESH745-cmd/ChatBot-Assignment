"""Merge a frozen AI-rubric score file into the matching human calibration set."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List


def read_csv(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, default=Path("data/judge_calibration.csv"))
    parser.add_argument("--scores", type=Path, default=Path("data/ai_judge_scores.csv"))
    args = parser.parse_args()
    rows = read_csv(args.calibration)
    scores = {row["example_id"]: row for row in read_csv(args.scores)}
    if {row["example_id"] for row in rows} != set(scores):
        raise SystemExit("Score IDs must exactly match calibration IDs.")
    for row in rows:
        score = scores[row["example_id"]]
        for dimension in ("groundedness", "helpfulness", "safety", "tone"):
            value = score[f"judge_{dimension}"]
            if value not in {"1", "2", "3", "4", "5"}:
                raise SystemExit(f"Invalid judge score on {row['example_id']}: {dimension}={value}")
            row[f"judge_{dimension}"] = value
        row["judge_model"] = score["judge_model"]
        existing = row.get("notes", "").strip()
        new_note = score.get("notes", "").strip()
        # The source score file is immutable: a second merge must not append a
        # duplicate rationale to the calibration artifact.
        row["notes"] = existing if not new_note or new_note in existing.split("; ") else "; ".join(
            item for item in (existing, new_note) if item
        )
    with args.calibration.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Merged {len(rows)} AI-rubric judge scores into {args.calibration}.")


if __name__ == "__main__":
    main()
