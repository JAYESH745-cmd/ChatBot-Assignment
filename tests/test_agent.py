import csv
import unittest
from pathlib import Path

from src.agent import AppleSupportAgent, MultinomialNB, route
from src.evaluate import classification_metrics, routing_metrics
from src.judge import agreement, stratified_sample, weighted_kappa
from src.taxonomy import pii_or_sensitive, weak_label


ROWS = [
    {"tweet_id": "1", "customer_text": "@AppleSupport I forgot my Apple ID password", "historical_reply": "Please use account recovery."},
    {"tweet_id": "2", "customer_text": "@AppleSupport I was charged twice for Music", "historical_reply": "Please send us a DM about the charge."},
    {"tweet_id": "3", "customer_text": "@AppleSupport where is my order", "historical_reply": "Please check order status."},
    {"tweet_id": "4", "customer_text": "@AppleSupport my screen is cracked", "historical_reply": "We can discuss repair options."},
    {"tweet_id": "5", "customer_text": "@AppleSupport my iPhone keeps crashing", "historical_reply": "Which iOS version are you using?"},
    {"tweet_id": "6", "customer_text": "@AppleSupport how do I share photos", "historical_reply": "Here are the sharing steps."},
    {"tweet_id": "7", "customer_text": "@AppleSupport this experience is terrible", "historical_reply": "We are sorry to hear that."},
    {"tweet_id": "8", "customer_text": "@AppleSupport hello", "historical_reply": "How can we help?"},
]


class TaxonomyTests(unittest.TestCase):
    def test_rules_cover_sensitive_domain_examples(self):
        self.assertEqual(weak_label("I cannot sign in to my Apple ID"), "account_access_security")
        self.assertEqual(weak_label("Where is my order?"), "order_delivery")
        self.assertEqual(weak_label("How do I share a photo?"), "how_to")

    def test_sensitive_text_forces_handoff(self):
        self.assertTrue(pii_or_sensitive("my serial number is 123456789"))
        self.assertFalse(pii_or_sensitive("@115858 can you help?"))
        self.assertEqual(route("how_to", 0.99, "email is __email__", 0.9)[0], "escalate")
        self.assertEqual(route("other", 0.99, "unclear", 0.9)[0], "escalate")


class AgentTests(unittest.TestCase):
    def test_agent_returns_auditable_evidence(self):
        agent = AppleSupportAgent(ROWS)
        outcome = agent.predict("@AppleSupport how do I share photos with my family?")
        self.assertEqual(outcome["intent"], "how_to")
        self.assertEqual(outcome["action"], "auto_handle")
        self.assertIn("evidence_tweet_id", outcome)
        self.assertGreaterEqual(outcome["evidence_similarity"], 0)

    def test_naive_bayes_probabilities_sum_to_one(self):
        model = MultinomialNB().fit([row["customer_text"] for row in ROWS], [weak_label(row["customer_text"]) for row in ROWS])
        self.assertAlmostEqual(sum(model.predict_proba("my order is late").values()), 1.0, places=6)

    def test_metrics_expose_confusion_and_safe_routing_errors(self):
        intent = classification_metrics(["how_to", "other"], ["other", "other"])
        routing = routing_metrics(["auto_handle", "escalate"], ["escalate", "auto_handle"])
        self.assertEqual(intent["confusion_matrix"]["how_to"]["other"], 1)
        self.assertEqual(routing["false_auto_count"], 1)
        self.assertEqual(routing["unnecessary_escalation_count"], 1)


class JudgeTests(unittest.TestCase):
    def test_weighted_kappa_is_one_for_identical_raters(self):
        self.assertEqual(weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)

    def test_judge_sample_covers_multiple_strata(self):
        records = [{"intent": "how_to", "action": "auto_handle", "id": str(i)} for i in range(4)]
        records += [{"intent": "billing_subscription", "action": "escalate", "id": str(i)} for i in range(4, 8)]
        sample = stratified_sample(records, 2)
        self.assertEqual({(row["intent"], row["action"]) for row in sample}, {
            ("how_to", "auto_handle"), ("billing_subscription", "escalate")
        })

    def test_agreement_uses_exact_agreement_when_human_scores_are_constant(self):
        row = {key: "4" for dimension in ("groundedness", "helpfulness", "safety", "tone") for key in (f"human_{dimension}", f"judge_{dimension}")}
        result = agreement([row, row])
        self.assertIsNone(result["quadratic_weighted_kappa"]["tone"])
        self.assertEqual(result["exact_agreement"]["tone"], 1.0)


class DataIntegrityTests(unittest.TestCase):
    def test_final_golden_set_is_complete_and_human_reviewed(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "data" / "golden_eval.csv").open(encoding="utf-8", newline="") as handle:
            golden = list(csv.DictReader(handle))
        self.assertEqual(len(golden), 200)
        self.assertEqual(len({row["example_id"] for row in golden}), 200)
        self.assertTrue(all(row["review_status"] == "human_reviewed" for row in golden))

    def test_calibration_has_complete_human_and_judge_scores(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "data" / "judge_calibration.csv").open(encoding="utf-8", newline="") as handle:
            calibration = list(csv.DictReader(handle))
        self.assertEqual(len(calibration), 50)
        for row in calibration:
            for dimension in ("groundedness", "helpfulness", "safety", "tone"):
                self.assertIn(int(row[f"human_{dimension}"]), range(1, 6))
                self.assertIn(int(row[f"judge_{dimension}"]), range(1, 6))


if __name__ == "__main__":
    unittest.main()
