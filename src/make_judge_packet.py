"""Create a frozen, stratified 50-example packet for judge/human calibration."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .judge import stratified_sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("reports/predictions.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/judge_calibration_template.csv"))
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    with args.predictions.open(encoding="utf-8", newline="") as handle:
        sample = stratified_sample(list(csv.DictReader(handle)), args.limit)
    fields = (
        "example_id", "customer_text", "intent", "action", "escalation_reason", "draft_reply",
        "evidence_customer_text", "evidence_historical_reply", "human_groundedness",
        "judge_groundedness", "human_helpfulness", "judge_helpfulness", "human_safety",
        "judge_safety", "human_tone", "judge_tone", "human_rater_id", "judge_model", "notes",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in sample:
            writer.writerow({key: " ".join(str(row.get(key, "")).split()) for key in fields})
    print(f"Wrote {len(sample)} frozen calibration rows to {args.output}.")


if __name__ == "__main__":
    main()
