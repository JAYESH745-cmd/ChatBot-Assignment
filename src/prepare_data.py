"""Create a small, deterministic Apple Support conversation slice from twcs.csv.

This script purposely performs two streaming passes over the source CSV, so it
does not need pandas or a multi-gigabyte in-memory dataframe. Rows are only
included when a customer inbound tweet received a direct AppleSupport reply.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import Dict, Iterable, List


def rows(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        yield from csv.DictReader(handle)


def reservoir_add(sample: List[dict], item: dict, seen: int, size: int, rng: random.Random) -> None:
    if len(sample) < size:
        sample.append(item)
        return
    replacement = rng.randrange(seen)
    if replacement < size:
        sample[replacement] = item


def build_slice(input_path: Path, output_path: Path, sample_size: int, seed: int) -> int:
    apple_replies: Dict[str, str] = {}
    for row in rows(input_path):
        parent = (row.get("in_response_to_tweet_id") or "").strip()
        if row.get("author_id") == "AppleSupport" and row.get("inbound") == "False" and parent:
            # Retain the earliest direct Apple answer if duplicate edges occur.
            apple_replies.setdefault(parent, (row.get("text") or "").strip())

    rng = random.Random(seed)
    sample: List[dict] = []
    seen = 0
    for row in rows(input_path):
        tweet_id = (row.get("tweet_id") or "").strip()
        customer_text = (row.get("text") or "").strip()
        reply = apple_replies.get(tweet_id)
        # Requiring an explicit @AppleSupport mention prevents occasional
        # cross-brand/thread-linking artefacts in the source corpus from being
        # attributed to Apple simply because an ID edge is malformed.
        mentions_apple = "@applesupport" in customer_text.lower()
        if row.get("inbound") != "True" or not reply or not customer_text or not mentions_apple:
            continue
        seen += 1
        reservoir_add(
            sample,
            {
                "tweet_id": tweet_id,
                "customer_id": row.get("author_id", ""),
                "created_at": row.get("created_at", ""),
                "customer_text": customer_text,
                "historical_reply": reply,
            },
            seen,
            sample_size,
            rng,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample.sort(key=lambda item: int(item["tweet_id"]))
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("tweet_id", "customer_id", "created_at", "customer_text", "historical_reply"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(sample)
    return seen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Path to original twcs.csv")
    parser.add_argument("--output", type=Path, default=Path("data/apple_support_slice.csv"))
    parser.add_argument("--sample-size", type=int, default=3200)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()
    if not args.input.exists():
        raise SystemExit(f"Missing {args.input}. Download it from the source listed in README.md.")
    eligible = build_slice(args.input, args.output, args.sample_size, args.seed)
    print(f"Wrote {args.output} from {eligible:,} eligible direct AppleSupport pairs.")


if __name__ == "__main__":
    main()
