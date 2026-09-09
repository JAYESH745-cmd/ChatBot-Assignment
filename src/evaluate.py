"""Evaluate intent, routing, and evidence-grounding without external packages."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from .agent import AppleSupportAgent, majority_baseline, rule_baseline
from .taxonomy import INTENTS


def read_csv(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_divide(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def classification_metrics(actual: Sequence[str], predicted: Sequence[str]) -> Dict[str, object]:
    correct = sum(a == p for a, p in zip(actual, predicted))
    per_intent = {}
    f1s = []
    for intent in INTENTS:
        tp = sum(a == intent and p == intent for a, p in zip(actual, predicted))
        fp = sum(a != intent and p == intent for a, p in zip(actual, predicted))
        fn = sum(a == intent and p != intent for a, p in zip(actual, predicted))
        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        per_intent[intent] = {"support": sum(a == intent for a in actual), "precision": precision, "recall": recall, "f1": f1}
        f1s.append(f1)
    return {
        "accuracy": safe_divide(correct, len(actual)),
        "macro_f1": round(sum(f1s) / len(INTENTS), 4),
        "per_intent": per_intent,
        "confusion_matrix": {
            expected: {predicted_intent: sum(a == expected and p == predicted_intent for a, p in zip(actual, predicted))
                       for predicted_intent in INTENTS}
            for expected in INTENTS
        },
    }


def routing_metrics(expected: Sequence[str], predicted: Sequence[str]) -> Dict[str, float]:
    auto_indices = [i for i, action in enumerate(predicted) if action == "auto_handle"]
    expected_escalate = [i for i, action in enumerate(expected) if action == "escalate"]
    return {
        "auto_coverage": safe_divide(len(auto_indices), len(predicted)),
        "auto_precision": safe_divide(sum(expected[i] == "auto_handle" for i in auto_indices), len(auto_indices)),
        "escalation_recall": safe_divide(sum(predicted[i] == "escalate" for i in expected_escalate), len(expected_escalate)),
        "routing_accuracy": safe_divide(sum(a == p for a, p in zip(expected, predicted)), len(expected)),
        "false_auto_count": sum(a == "escalate" and p == "auto_handle" for a, p in zip(expected, predicted)),
        "unnecessary_escalation_count": sum(a == "auto_handle" and p == "escalate" for a, p in zip(expected, predicted)),
    }


def label_source(rows: Sequence[Mapping[str, str]], allow_provisional: bool) -> str:
    reviewed = [row for row in rows if row.get("review_status") == "human_reviewed"]
    if len(reviewed) == len(rows):
        return "human_reviewed"
    author_reviewed = [row for row in rows if row.get("review_status") == "author_reviewed_ai_assisted"]
    if len(author_reviewed) == len(rows):
        return "author_reviewed_ai_assisted_not_independent_human_gold"
    if allow_provisional:
        return "proposed_labels_for_pipeline_smoke_test_only"
    missing = len(rows) - len(reviewed)
    raise ValueError(
        f"{missing} of {len(rows)} golden rows are not human_reviewed. "
        "Author-reviewed AI-assisted labels can be evaluated as preliminary results, but are never independent human gold."
    )


def gold_label(row: Mapping[str, str], key: str, allow_provisional: bool) -> str:
    value = (row.get(key) or "").strip()
    if value:
        return value
    if allow_provisional:
        return row["proposed_intent"] if key == "intent" else row["proposed_route"]
    raise ValueError(f"Blank {key} on {row.get('example_id')}")


def evaluate(slice_rows: List[dict], golden_rows: List[dict], allow_provisional: bool) -> Dict[str, object]:
    test_ids = {row["tweet_id"] for row in golden_rows}
    training_rows = [row for row in slice_rows if row["tweet_id"] not in test_ids]
    if len(training_rows) < 100:
        raise ValueError("Too few training rows after removing the golden set.")
    agent = AppleSupportAgent(training_rows)

    actual_intents = [gold_label(row, "intent", allow_provisional) for row in golden_rows]
    actual_routes = [gold_label(row, "expected_route", allow_provisional) for row in golden_rows]
    systems: Dict[str, Dict[str, List[str]]] = {
        "trivial_always_escalate": {"intents": [], "routes": []},
        "simple_keyword_rules": {"intents": [], "routes": []},
        "retrieval_agent": {"intents": [], "routes": []},
    }
    prediction_rows = []
    for gold in golden_rows:
        text = gold["customer_text"]
        trivial_intent, trivial_route = majority_baseline(text)
        rule_intent, rule_route = rule_baseline(text)
        output = agent.predict(text)
        systems["trivial_always_escalate"]["intents"].append(trivial_intent)
        systems["trivial_always_escalate"]["routes"].append(trivial_route)
        systems["simple_keyword_rules"]["intents"].append(rule_intent)
        systems["simple_keyword_rules"]["routes"].append(rule_route)
        systems["retrieval_agent"]["intents"].append(str(output["intent"]))
        systems["retrieval_agent"]["routes"].append(str(output["action"]))
        prediction_rows.append({
            "example_id": gold["example_id"],
            "tweet_id": gold["tweet_id"],
            "customer_text": text,
            "gold_intent": actual_intents[len(prediction_rows)],
            "gold_route": actual_routes[len(prediction_rows)],
            **{key: str(value) for key, value in output.items()},
        })

    results = {}
    for name, system in systems.items():
        results[name] = {
            "intent": classification_metrics(actual_intents, system["intents"]),
            "routing": routing_metrics(actual_routes, system["routes"]),
        }
    evidence_scores = [float(row["evidence_similarity"]) for row in prediction_rows]
    results["retrieval_agent"]["evidence"] = {
        "mean_similarity": round(sum(evidence_scores) / len(evidence_scores), 4),
        "share_above_grounding_gate": safe_divide(sum(score >= 0.13 for score in evidence_scores), len(evidence_scores)),
        "note": "Similarity is a retrieval diagnostic, not a substitute for a human or LLM quality judgment.",
    }
    results["retrieval_agent"]["error_examples"] = {
        "intent_errors": [
            {key: row[key] for key in ("example_id", "customer_text", "gold_intent", "intent", "action", "escalation_reason")}
            for row in prediction_rows if row["gold_intent"] != row["intent"]
        ][:5],
        "false_auto": [
            {key: row[key] for key in ("example_id", "customer_text", "gold_intent", "intent", "action", "escalation_reason")}
            for row in prediction_rows if row["gold_route"] == "escalate" and row["action"] == "auto_handle"
        ][:5],
        "unnecessary_escalations": [
            {key: row[key] for key in ("example_id", "customer_text", "gold_intent", "intent", "action", "escalation_reason")}
            for row in prediction_rows if row["gold_route"] == "auto_handle" and row["action"] == "escalate"
        ][:5],
    }
    return {
        "n_golden": len(golden_rows),
        "n_train": len(training_rows),
        "label_source": label_source(golden_rows, allow_provisional),
        "results": results,
        "predictions": prediction_rows,
    }


def write_predictions(rows: Iterable[Mapping[str, str]], path: Path) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        # CSV permits embedded newlines, but flattening them makes the committed
        # audit artifact line-addressable and avoids whitespace-only line noise.
        writer.writerows({key: " ".join(str(value).split()) for key, value in row.items()} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=Path, default=Path("data/apple_support_slice.csv"))
    parser.add_argument("--golden", type=Path, default=Path("data/golden_eval.csv"))
    parser.add_argument("--out", type=Path, default=Path("reports/results.json"))
    parser.add_argument("--allow-provisional", action="store_true")
    args = parser.parse_args()
    try:
        evaluation = evaluate(read_csv(args.slice), read_csv(args.golden), args.allow_provisional)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    predictions = evaluation.pop("predictions")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    write_predictions(predictions, args.out.with_name("predictions.csv"))
    headline = evaluation["results"]["retrieval_agent"]
    print(json.dumps({"label_source": evaluation["label_source"], "intent": headline["intent"], "routing": headline["routing"]}, indent=2))


if __name__ == "__main__":
    main()
