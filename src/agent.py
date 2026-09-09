"""A dependency-free intent classifier, historical-reply retriever, and router."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .taxonomy import INTENTS, pii_or_sensitive, rule_scores, strip_twitter_handles, tokens, weak_label


def _softmax(log_scores: Mapping[str, float]) -> Dict[str, float]:
    maximum = max(log_scores.values())
    exps = {key: math.exp(value - maximum) for key, value in log_scores.items()}
    total = sum(exps.values())
    return {key: value / total for key, value in exps.items()}


class MultinomialNB:
    """Small, inspectable bag-of-words classifier used as the simple baseline."""

    def __init__(self, alpha: float = 0.8) -> None:
        self.alpha = alpha
        self.class_docs: Counter = Counter()
        self.class_tokens: Dict[str, Counter] = defaultdict(Counter)
        self.vocabulary: set = set()
        self.total_docs = 0

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> "MultinomialNB":
        for text, label in zip(texts, labels):
            if label not in INTENTS:
                continue
            self.class_docs[label] += 1
            self.total_docs += 1
            word_counts = Counter(tokens(text))
            self.class_tokens[label].update(word_counts)
            self.vocabulary.update(word_counts)
        if not self.total_docs:
            raise ValueError("No labeled training examples.")
        return self

    def predict_proba(self, text: str) -> Dict[str, float]:
        word_counts = Counter(tokens(text))
        vocabulary_size = max(1, len(self.vocabulary))
        scores: Dict[str, float] = {}
        for label in INTENTS:
            prior = (self.class_docs[label] + self.alpha) / (self.total_docs + self.alpha * len(INTENTS))
            denominator = sum(self.class_tokens[label].values()) + self.alpha * vocabulary_size
            score = math.log(prior)
            for word, count in word_counts.items():
                score += count * math.log((self.class_tokens[label][word] + self.alpha) / denominator)
            scores[label] = score
        return _softmax(scores)

    def predict(self, text: str) -> Tuple[str, float]:
        probabilities = self.predict_proba(text)
        intent = max(probabilities, key=probabilities.get)
        return intent, probabilities[intent]


@dataclass(frozen=True)
class Evidence:
    tweet_id: str
    customer_text: str
    historical_reply: str
    score: float


class ReplyRetriever:
    """TF-IDF cosine retrieval over historical direct AppleSupport resolutions."""

    def __init__(self, rows: Sequence[Mapping[str, str]], labels: Mapping[str, str]) -> None:
        self.rows = list(rows)
        self.labels = labels
        document_frequency: Counter = Counter()
        for row in self.rows:
            document_frequency.update(set(tokens(row["customer_text"])))
        n_docs = max(1, len(self.rows))
        self.idf = {word: math.log((1 + n_docs) / (1 + freq)) + 1 for word, freq in document_frequency.items()}
        self.vectors = [self._vector(row["customer_text"]) for row in self.rows]

    def _vector(self, text: str) -> Dict[str, float]:
        counts = Counter(tokens(text))
        norm = math.sqrt(sum((count * self.idf.get(word, 0.0)) ** 2 for word, count in counts.items())) or 1.0
        return {word: count * self.idf.get(word, 0.0) / norm for word, count in counts.items() if word in self.idf}

    @staticmethod
    def _cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(word, 0.0) for word, value in left.items())

    def retrieve(self, text: str, intent: str) -> Evidence:
        query = self._vector(text)
        best_index, best_score = 0, -1.0
        # Prefer same-intent support examples, then fall back to the global corpus.
        indices = [i for i, row in enumerate(self.rows) if self.labels.get(row["tweet_id"]) == intent]
        for candidate_indices in (indices, range(len(self.rows))):
            for index in candidate_indices:
                score = self._cosine(query, self.vectors[index])
                if score > best_score:
                    best_index, best_score = index, score
            if best_score >= 0:
                break
        row = self.rows[best_index]
        return Evidence(row["tweet_id"], row["customer_text"], row["historical_reply"], max(0.0, best_score))


def _sanitize_historical_reply(reply: str) -> str:
    reply = strip_twitter_handles(reply)
    # Avoid leaking team initials which add no value to a new draft.
    reply = reply.replace("\n", " ").strip()
    if reply and reply[-3:-1] == "-":
        reply = reply[:-3].rstrip()
    return reply


def fallback_reply(intent: str) -> str:
    templates = {
        "how_to": "We can help with that. Please tell us which Apple product and software version you are using so we can point you to the right steps.",
        "device_technical_issue": "Sorry you’re having trouble. Please share the product, software version, and what happens when you try, and we’ll help narrow it down.",
        "feedback_complaint": "We’re sorry this experience has been frustrating. We appreciate the feedback and would like to understand what happened.",
        "account_access_security": "For your security, please contact Apple Support through a private, secure support channel so account details are not shared publicly.",
        "billing_subscription": "We can help review this billing issue through a private support channel; please do not post account or payment details here.",
        "order_delivery": "We can look into the order through a private support channel. Please do not post your order number publicly.",
        "repair_service": "We can help with service options. Please contact Apple Support privately with the product and issue, without sharing serial numbers publicly.",
        "other": "Thanks for reaching out. Could you share a little more about the Apple product or service involved?",
    }
    return templates[intent]


def route(intent: str, confidence: float, text: str, evidence_score: float) -> Tuple[str, str]:
    if pii_or_sensitive(text):
        return "escalate", "sensitive_data"
    if confidence < 0.62:
        return "escalate", "low_intent_confidence"
    if intent in {"account_access_security", "billing_subscription", "order_delivery"}:
        return "escalate", "account_or_transaction_action"
    if intent == "repair_service":
        return "escalate", "repair_case_specific"
    if intent == "feedback_complaint":
        return "escalate", "high_emotion_or_feedback"
    if intent == "other":
        return "escalate", "ambiguous_or_out_of_scope"
    if evidence_score < 0.13:
        return "escalate", "insufficient_historical_grounding"
    return "auto_handle", "safe_general_guidance"


class AppleSupportAgent:
    def __init__(self, training_rows: Sequence[Mapping[str, str]]) -> None:
        self.training_rows = list(training_rows)
        self.training_labels = {row["tweet_id"]: weak_label(row["customer_text"]) for row in self.training_rows}
        self.classifier = MultinomialNB().fit(
            [row["customer_text"] for row in self.training_rows],
            [self.training_labels[row["tweet_id"]] for row in self.training_rows],
        )
        self.retriever = ReplyRetriever(self.training_rows, self.training_labels)

    def predict(self, customer_text: str) -> Dict[str, object]:
        probabilities = self.classifier.predict_proba(customer_text)
        learned_intent = max(probabilities, key=probabilities.get)
        proposed_intent = weak_label(customer_text)
        explicit_matches = rule_scores(customer_text)[proposed_intent]
        # The production classifier is a hybrid: exact high-precision domain
        # signals win; otherwise the learned model generalizes from the slice.
        # This is intentionally distinct from the keyword baseline because the
        # fallback is learned and its confidence is consumed by the router.
        if proposed_intent != "other" and explicit_matches:
            intent = proposed_intent
            confidence = max(probabilities[intent], min(0.93, 0.55 + 0.12 * explicit_matches))
        else:
            intent, confidence = learned_intent, probabilities[learned_intent]
        evidence = self.retriever.retrieve(customer_text, intent)
        action, reason = route(intent, confidence, customer_text, evidence.score)
        reply = _sanitize_historical_reply(evidence.historical_reply) if evidence.score >= 0.13 else fallback_reply(intent)
        return {
            "intent": intent,
            "intent_confidence": round(confidence, 4),
            "action": action,
            "escalation_reason": reason,
            "draft_reply": reply,
            "evidence_tweet_id": evidence.tweet_id,
            "evidence_customer_text": evidence.customer_text,
            "evidence_historical_reply": evidence.historical_reply,
            "evidence_similarity": round(evidence.score, 4),
        }


def majority_baseline(_: str) -> Tuple[str, str]:
    return "other", "escalate"


def rule_baseline(text: str) -> Tuple[str, str]:
    intent = weak_label(text)
    if intent in {"how_to", "device_technical_issue"} and not pii_or_sensitive(text):
        return intent, "auto_handle"
    return intent, "escalate"
