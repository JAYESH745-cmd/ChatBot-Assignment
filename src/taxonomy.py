"""Intent taxonomy, weak-labeling rules, and shared text utilities.

Rules are deliberately visible. They are used only to bootstrap the training
slice; the held-out golden file is designed to be reviewed independently.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Tuple

INTENTS = (
    "account_access_security",
    "billing_subscription",
    "order_delivery",
    "repair_service",
    "device_technical_issue",
    "how_to",
    "feedback_complaint",
    "other",
)

INTENT_DESCRIPTIONS = {
    "account_access_security": "Apple Account sign-in, password, verification, lock, or security problem",
    "billing_subscription": "charge, refund, payment, subscription, or purchase-billing problem",
    "order_delivery": "order status, shipment, delivery, stock, or trade-in question",
    "repair_service": "physical damage, repair, appointment, warranty, or service question",
    "device_technical_issue": "device, app, iCloud, or accessory not working as expected",
    "how_to": "request for instructions or product capability guidance",
    "feedback_complaint": "complaint, praise, or general feedback without a concrete support task",
    "other": "ambiguous, unsupported, or out-of-scope request",
}

# Ordered because a security/billing mention should win over broad device words.
RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("account_access_security", (
        "apple id", "appleid", "password", "sign in", "signin", "log in", "login",
        "two factor", "2fa", "verification", "locked", "hack", "hacked", "security code",
        "account disabled", "account locked", "reset my", "forgot my",
    )),
    ("billing_subscription", (
        "charged", "charge", "refund", "billing", "payment", "paid", "purchase",
        "invoice", "receipt", "subscription", "subscribe", "itunes bill", "apple music bill",
        "card declined", "money back", "cancel my plan",
    )),
    ("order_delivery", (
        "order", "delivery", "deliver", "shipping", "shipment", "tracking", "track my",
        "arrive", "arrival", "preorder", "pre-order", "in stock", "out of stock", "trade in",
    )),
    ("repair_service", (
        "repair", "broken screen", "cracked", "damage", "damaged", "battery replacement",
        "genius bar", "appointment", "warranty", "applecare", "service my", "replace my",
    )),
    ("device_technical_issue", (
        "not working", "won't", "wont", "cannot", "can't", "unable", "crash", "crashing",
        "freez", "error", "bug", "issue", "problem", "battery", "iphone", "ipad", "macbook",
        "mac", "airpods", "watch", "icloud", "facetime", "imessage", "siri", "update",
    )),
    ("how_to", (
        "how do i", "how to", "can i", "where can i", "does", "what is", "help me",
        "please explain", "instructions", "tutorial", "feature",
    )),
    ("feedback_complaint", (
        "worst", "terrible", "awful", "disappointed", "frustrated", "hate", "love", "thanks",
        "thank you", "feedback", "useless", "ridiculous", "shame", "angry",
    )),
]

STOPWORDS = frozenset(
    "a an the and or but if then than to of in on at for from with by about into is are was were be been "
    "i me my we our you your it this that these those please hi hello hey apple applesupport".split()
)


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"@[\w_]+", " MENTION ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9']+", normalize(text)) if len(t) > 1 and t not in STOPWORDS]


def weak_label(text: str) -> str:
    """A transparent, conservative source of *training* labels—not gold labels."""
    prepared = normalize(text)
    for intent, phrases in RULES:
        if any(phrase in prepared for phrase in phrases):
            return intent
    return "other"


def rule_scores(text: str) -> Counter:
    prepared = normalize(text)
    scores: Counter = Counter()
    for intent, phrases in RULES:
        scores[intent] = sum(phrase in prepared for phrase in phrases)
    return scores


def pii_or_sensitive(text: str) -> bool:
    prepared = (text or "").lower()
    return bool(
        re.search(r"__email__|__phone_number__|\b\d{6,}\b|\b\d{3}[- ]?\d{3}[- ]?\d{4}\b", prepared)
        or "serial number" in prepared
        or "credit card" in prepared
        or "card number" in prepared
    )


def strip_twitter_handles(text: str) -> str:
    return re.sub(r"@[A-Za-z0-9_]+", "@customer", text or "").strip()
