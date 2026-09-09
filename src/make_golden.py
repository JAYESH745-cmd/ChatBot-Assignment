"""Sample a stratified annotation worksheet for the 200-row golden evaluation set.

The script records its provisional rule suggestion separately from the label
columns. Before a claim is made from this file, a human annotator must replace
the suggested values and mark `review_status=human_reviewed`. This prevents a
weak-supervision rule from quietly becoming its own test set.
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .taxonomy import INTENTS, pii_or_sensitive, weak_label


TARGETS = {
    "account_access_security": 25,
    "billing_subscription": 25,
    "order_delivery": 25,
    "repair_service": 25,
    "device_technical_issue": 30,
    "how_to": 30,
    "feedback_complaint": 20,
    "other": 20,
}


def suggested_route(intent: str, text: str) -> str:
    """A visible suggestion, deliberately not a ground-truth routing decision."""
    if pii_or_sensitive(text):
        return "escalate"
    if intent in {"account_access_security", "billing_subscription", "order_delivery", "repair_service", "other"}:
        return "escalate"
    return "auto_handle"


def load_rows(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sample_golden(rows: List[dict], seed: int) -> List[dict]:
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        buckets[weak_label(row["customer_text"])].append(row)
    rng = random.Random(seed)
    selected: List[dict] = []
    for intent in INTENTS:
        candidates = buckets[intent]
        if len(candidates) < TARGETS[intent]:
            raise ValueError(f"Only {len(candidates)} candidates for {intent}; expected {TARGETS[intent]}")
        selected.extend(rng.sample(candidates, TARGETS[intent]))
    rng.shuffle(selected)
    return selected


def write_golden(rows: List[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "example_id", "tweet_id", "customer_text", "historical_reply", "proposed_intent",
        "proposed_route", "intent", "expected_route", "escalation_reason", "review_status", "review_notes",
    )
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            proposal = weak_label(row["customer_text"])
            writer.writerow({
                "example_id": f"G{i:03d}",
                "tweet_id": row["tweet_id"],
                "customer_text": row["customer_text"],
                "historical_reply": row["historical_reply"],
                "proposed_intent": proposal,
                "proposed_route": suggested_route(proposal, row["customer_text"]),
                # Deliberately blank: these are the independent gold labels.
                "intent": "",
                "expected_route": "",
                "escalation_reason": "",
                "review_status": "requires_human_review",
                "review_notes": "",
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=Path, default=Path("data/apple_support_slice.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/golden_eval.csv"))
    parser.add_argument("--seed", type=int, default=20260910)
    args = parser.parse_args()
    selected = sample_golden(load_rows(args.slice), args.seed)
    write_golden(selected, args.output)
    print(f"Wrote {len(selected)} independent annotation rows to {args.output}.")


if __name__ == "__main__":
    main()
