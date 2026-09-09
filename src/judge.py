"""Opt-in LLM-as-judge for reply quality and human-agreement analysis.

The main evaluation never fabricates a judge result. This module calls the
OpenAI Responses API only when `OPENAI_API_KEY` is explicitly available.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


RUBRIC = """You are auditing a customer-support draft. Score each dimension 1-5.
Groundedness: the draft is supported by the supplied historical AppleSupport resolution, without inventing policy or facts.
Helpfulness: it gives a concrete next step appropriate to the customer message.
Safety: it does not request sensitive information publicly and it respects the proposed escalation decision.
Tone: concise, empathetic, and professional.
"""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "groundedness": {"type": "integer", "minimum": 1, "maximum": 5},
        "helpfulness": {"type": "integer", "minimum": 1, "maximum": 5},
        "safety": {"type": "integer", "minimum": 1, "maximum": 5},
        "tone": {"type": "integer", "minimum": 1, "maximum": 5},
        "overall_pass": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": ["groundedness", "helpfulness", "safety", "tone", "overall_pass", "rationale"],
    "additionalProperties": False,
}


def call_openai(record: Mapping[str, str], model: str) -> Dict[str, object]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for --judge openai")
    prompt = f"""{RUBRIC}
Customer message: {record['customer_text']}
Predicted intent: {record['intent']}
Proposed action: {record['action']} ({record['escalation_reason']})
Draft reply: {record['draft_reply']}
Historical resolution evidence: {record['evidence_historical_reply']}
"""
    payload = {
        "model": model,
        "store": False,
        "input": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "reply_quality_judgement",
                "strict": True,
                "schema": JUDGE_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode("utf-8", errors="replace")) from error
    output_text = data.get("output_text")
    if not output_text:
        raise RuntimeError(f"No output_text from Responses API: {data}")
    return json.loads(output_text)


def read_csv(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def stratified_sample(records: List[dict], limit: int, seed: int = 20260911) -> List[dict]:
    """Sample intent × routing strata so judging is not dominated by one class."""
    if limit >= len(records):
        return records
    buckets: Dict[tuple, List[dict]] = {}
    for record in records:
        buckets.setdefault((record.get("intent", "other"), record.get("action", "escalate")), []).append(record)
    rng = random.Random(seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    groups = sorted(buckets)
    selected: List[dict] = []
    # Round-robin makes every non-empty stratum represented before filling.
    while len(selected) < limit and any(buckets[group] for group in groups):
        for group in groups:
            if buckets[group] and len(selected) < limit:
                selected.append(buckets[group].pop())
    return selected


def write_csv(rows: Iterable[Mapping[str, object]], output: Path) -> None:
    rows = list(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_kappa(left: List[int], right: List[int], levels: int = 5) -> float:
    """Quadratic-weighted Cohen's kappa for ordinal 1-5 ratings."""
    if len(left) != len(right) or not left:
        return 0.0
    observed = [[0] * levels for _ in range(levels)]
    for a, b in zip(left, right):
        observed[a - 1][b - 1] += 1
    n = len(left)
    row_totals = [sum(row) for row in observed]
    col_totals = [sum(observed[i][j] for i in range(levels)) for j in range(levels)]
    numerator = denominator = 0.0
    for i in range(levels):
        for j in range(levels):
            weight = ((i - j) ** 2) / ((levels - 1) ** 2)
            numerator += weight * observed[i][j] / n
            denominator += weight * (row_totals[i] * col_totals[j]) / (n * n)
    return round(1 - numerator / denominator, 4) if denominator else 0.0


def agreement(calibration: List[Mapping[str, str]]) -> Dict[str, object]:
    dimensions = ("groundedness", "helpfulness", "safety", "tone")
    output: Dict[str, object] = {"n": len(calibration), "quadratic_weighted_kappa": {}}
    for dimension in dimensions:
        human = [int(row[f"human_{dimension}"]) for row in calibration]
        judge = [int(row[f"judge_{dimension}"]) for row in calibration]
        output["quadratic_weighted_kappa"][dimension] = weighted_kappa(human, judge)
    output["mean_kappa"] = round(statistics.mean(output["quadratic_weighted_kappa"].values()), 4)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("reports/predictions.csv"))
    parser.add_argument("--out", type=Path, default=Path("reports/llm_judgements.csv"))
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--limit", type=int, default=50, help="Judge a stratified 50-row sample by default.")
    parser.add_argument("--calibration", type=Path, help="CSV with human_* and judge_* scores to compute agreement.")
    args = parser.parse_args()
    if args.calibration:
        print(json.dumps(agreement(read_csv(args.calibration)), indent=2))
        return
    predictions = stratified_sample(read_csv(args.predictions), args.limit)
    judged = []
    for record in predictions:
        score = call_openai(record, args.model)
        judged.append({**record, **{f"judge_{key}": value for key, value in score.items()}})
    write_csv(judged, args.out)
    print(f"Wrote {len(judged)} LLM judgements to {args.out}")


if __name__ == "__main__":
    main()
