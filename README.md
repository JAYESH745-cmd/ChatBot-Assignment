# Apple Support Twitter Agent

A compact, reproducible support-routing prototype built from direct customer →
`@AppleSupport` conversations in the **Customer Support on Twitter** corpus.
It classifies a message, retrieves a similar historical Apple resolution to
ground a draft, and defaults to a human when account, billing, order, repair,
privacy, ambiguity, or insufficient-evidence risk is present.

> Status: the runnable slice and **200-row author-reviewed, AI-assisted**
> annotation set are included. Its provenance is recorded in every row and it
> supports a preliminary held-out evaluation. It is not independent human gold;
> an external reviewer must still complete the final blind review and judge
> calibration before submission.

## Reproduce in under 15 minutes

Requires Python 3.9+; no package installation is required.

```bash
git clone <YOUR-REPO-URL>
cd hiver-apple-support-agent
make test

# Run the preliminary held-out evaluation.
python3 -m src.evaluate \
  --slice data/apple_support_slice.csv \
  --golden data/golden_eval.csv \
  --out reports/results.json
```

That command writes `reports/results.json` and `reports/predictions.csv`.
It holds all 200 golden tweet IDs out of training and records label provenance.
For a code-only smoke test based on the original weak proposals, use:

```bash
python3 -m src.evaluate --allow-provisional --out reports/provisional_results.json
```

Do **not** report that smoke test: its labels come from visible weak rules.
Likewise, results marked `author_reviewed_ai_assisted_not_independent_human_gold`
are preliminary and cannot substitute for independently annotated human gold.

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
synthetic prompts). The seed-fixed sample is stratified to cover all eight
intents: 25 each for account/billing/order/repair, 30 each for device/how-to,
and 20 each for feedback/other. The visible `proposed_*` columns are used only
to make coverage reproducible. The initial label pass is explicitly marked
`author_reviewed_ai_assisted`; hide proposal columns from the independent human
review required before submission. Labeling protocol and the recommended 20%
adjudication pass are in the annotation guide.

The author-review ledger is versioned separately in
`data/author_annotations.csv` and can be re-applied deterministically:

```bash
python3 -m src.apply_annotations
```

## Reply-quality LLM judge and human calibration

The core metrics do not require an API. For qualitative reply evaluation, the
opt-in judge scores groundedness, helpfulness, safety, and tone on a 1–5
rubric. It receives the customer message, decision, draft, and retrieved
historical evidence; it must return JSON.

```bash
export OPENAI_API_KEY=...  # key is never read from a file or logged
python3 -m src.judge --predictions reports/predictions.csv --limit 50 \
  --out reports/llm_judgements.csv --model gpt-4.1-mini
```

Have a human independently score the same 50 records using the same rubric,
then create a calibration CSV with `human_groundedness`,
`judge_groundedness`, `human_helpfulness`, `judge_helpfulness`,
`human_safety`, `judge_safety`, `human_tone`, and `judge_tone` (all 1–5). The
harness reports per-dimension and mean quadratic-weighted Cohen’s kappa:

```bash
python3 -m src.judge --calibration data/judge_calibration.csv
```

This deliberately supplies evidence of judge–human agreement instead of
assuming an LLM judge is correct. Do not use the same rater who authored a
draft as the sole human calibrator.

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
