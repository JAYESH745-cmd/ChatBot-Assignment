# Apple Support Twitter Agent

A compact, reproducible support-routing prototype built from direct customer →
`@AppleSupport` conversations in the **Customer Support on Twitter** corpus.
It classifies a message, retrieves a similar historical Apple resolution to
ground a draft, and defaults to a human when account, billing, order, repair,
privacy, ambiguity, or insufficient-evidence risk is present.

> Status: the runnable slice, a **200-row human-reviewed** golden set, and a
> frozen 50-row human/AI-rubric calibration set are included. Provenance and
> row-level notes are versioned with the data. The agreement results show that
> the rubric judge is useful for groundedness/safety auditing but is not a
> substitute for human reply evaluation.

## Reproduce in under 15 minutes

Requires Python 3.9+; no package installation is required.

```bash
git clone <YOUR-REPO-URL>
cd hiver-apple-support-agent
make test

# Run the held-out evaluation.
python3 -m src.evaluate \
  --slice data/apple_support_slice.csv \
  --golden data/golden_eval.csv \
  --out reports/results.json
```

That command writes `reports/results.json` and `reports/predictions.csv`.
It holds all 200 golden tweet IDs out of training and records the label
provenance (`human_reviewed`). To reproduce the included judge-agreement
artifact, run:

```bash
python3 -m src.judge --calibration data/judge_calibration.csv \
  > reports/judge_agreement.json
```

`make all` runs the tests and held-out evaluation without network access.

## Agent design

| Component | Implementation | Why it is there |
|---|---|---|
| Intent model | 8-way multinomial Naive Bayes plus high-precision domain rules | Fast, inspectable, and suitable for a small CPU-only slice |
| Reply draft | TF-IDF cosine retrieval of a historical direct AppleSupport response | Every draft contains a traceable source tweet and resolution |
| Routing | Confidence + sensitive-data + intent-risk + evidence-similarity gate | Favors false escalations over unsafe autonomous action |
| Trivial baseline | always `other`, always escalate | Establishes the no-automation floor |
| Simple baseline | visible phrase-to-intent rules | Tests whether learned fallback/retrieval add value over rules |

### Intent taxonomy

`account_access_security`, `billing_subscription`, `order_delivery`,
`repair_service`, `device_technical_issue`, `how_to`, `feedback_complaint`,
and `other`. Definitions and boundary cases are in
[`docs/INTENT_TAXONOMY.md`](docs/INTENT_TAXONOMY.md) and
[`docs/ANNOTATION_GUIDE.md`](docs/ANNOTATION_GUIDE.md).

### Auto-handling policy

Only generic `how_to` and `device_technical_issue` messages can be
auto-handled, and only when confidence is at least 0.62, the evidence cosine
score is at least 0.13, and there is no sensitive data. Account/security,
billing, order, repair, high-emotion feedback, ambiguous messages, and any
message containing a masked email/phone, long number, serial number, or card
reference go to a human with an explicit reason. This prototype never asks for
private data in a public reply.

## Golden set

`data/golden_eval.csv` has 200 actual AppleSupport customer messages (not
synthetic prompts). It is a seed-fixed sample selected to cover all eight
intents; final intent, route, reason, and reviewer note are recorded on every
row with `review_status=human_reviewed`. The visible `proposed_*` columns are
the original sampling proposals, retained for audit and never used by the
evaluator. The report uses the final human-reviewed labels; the earlier
`data/author_annotations.csv` is retained only as a historical bootstrap
ledger and must not be re-applied to the final golden file.

## Reply-quality LLM judge and human calibration

The core metrics do not require an API. The included frozen 50-case
`data/judge_calibration.csv` pairs human scores with a documented manual
AI-rubric scoring pass for groundedness, helpfulness, safety, and tone (all
1–5). The source
scores are kept in `data/ai_judge_scores.csv`, and
`python3 -m src.merge_judge_scores` performs the deterministic merge. The
agreement artifact is `reports/judge_agreement.json`.

The judge found frequent relevance failures in otherwise grounded historical
replies: exact agreement is 92% for groundedness and 76% for safety, but only
14% for helpfulness and 6% for tone. The human rater used nearly constant
scores for three dimensions, so quadratic kappa is undefined there; the
harness reports exact agreement and MAE instead. This is evidence to keep a
human in the reply-quality loop, not evidence of autonomous reply readiness.

For a fresh, automated API-based judging run, the opt-in judge scores the same
rubric from the customer message, decision, draft, and historical evidence and
returns JSON:

```bash
export OPENAI_API_KEY=...  # key is never read from a file or logged
python3 -m src.judge --predictions reports/predictions.csv --limit 50 \
  --out reports/llm_judgements.csv --model gpt-4.1-mini
```

For another calibration set, have a human independently score the same records
using the rubric, then add `human_*` and `judge_*` score columns (all 1–5). The
harness reports per-dimension quadratic-weighted Cohen’s kappa when defined,
plus exact agreement, MAE, and each rater’s score distribution:

```bash
python3 -m src.judge --calibration data/judge_calibration.csv
```

Do not use the same rater who authored a draft as the sole human calibrator.

Create the frozen, stratified 50-row calibration packet before asking the
human rater and judge to score it:

```bash
make judge-packet
```

## Recreate the compact slice (optional)

The committed 3,200-pair slice is enough for the headline run. To recreate it
from the primary corpus, download `twcs.csv` yourself under its CC BY-NC-SA
4.0 terms, then run:

```bash
python3 -m src.prepare_data --input data/raw/twcs.csv --output data/apple_support_slice.csv
python3 -m src.make_golden --slice data/apple_support_slice.csv --output data/golden_eval.csv
```

`prepare_data` makes two streaming passes and preserves only direct replies
from `AppleSupport` to inbound tweets that explicitly mention `@AppleSupport`.
The exact seed and source filtering are in code, and raw data are excluded via
`.gitignore`.

## Scope and non-goals

This is not a production Apple agent. It does not authenticate users, take
account actions, make order/refund decisions, access private messages, use
live Apple policies, or guarantee the retrieved historical wording remains
current. It generates a public-facing draft for a reviewed workflow, not an
unbounded chatbot.

## Attribution and license

Primary data: Stuart Axelbrooke / Thought Vector, [Customer Support on
Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter),
CC BY-NC-SA 4.0. The included slice is a derived non-commercial research
artifact and retains the source’s anonymized identifiers. See the dataset page
for current license terms. The optional LLM judge uses the OpenAI Responses API
and is not required for the local pipeline.

See [`REPORT.md`](REPORT.md) and [`DECISION_LOG.md`](DECISION_LOG.md) for the
submission narrative and non-obvious choices.
