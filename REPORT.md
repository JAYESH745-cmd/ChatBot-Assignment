# Apple Support Twitter Agent — report

## Problem framing

“Good” is not a fluent answer in isolation. For this setting, it is a correct
operational intent, a draft whose next step is supported by a comparable
historical AppleSupport resolution, and an escalation decision that avoids
making account, financial, repair, or privacy-sensitive decisions in public.
The chosen scope is public Twitter-style first messages, not authenticated
support. I did not build account lookups, refunds, repair booking, policy
verification, multi-turn state, private-message handling, or live knowledge.

The agent supports eight operational intents: account/access/security,
billing/subscription, order/delivery, repair/service, device technical issue,
how-to, feedback/complaint, and other. It only auto-handles the latter two
product-help categories when both intent confidence and historical evidence are
strong; all other classes default to a person for an explicit reason.

## Data and evaluation design

The primary source is the Customer Support on Twitter corpus. I used a
seed-fixed 3,200-pair Apple slice, keeping inbound tweets with an explicit
`@AppleSupport` mention and a direct AppleSupport reply. The explicit mention
filter avoids cross-brand/thread-linking artefacts found when using response
edges alone. The raw corpus is not committed; the compact derived slice is.

The intended golden set is 200 held-out real messages, stratified across the
eight classes (25/25/25/25/30/30/20/20). Annotators see the message but not the
historical reply or proposal columns. A second reviewer adjudicates a random
40-row subset. Exact golden tweet IDs are removed before both model fitting and
retrieval, preventing direct answer leakage.

**Integrity status.** The repository currently contains the independently
sampled worksheet and labeling protocol, but its human label fields are blank.
Therefore no headline metric below is claimed. The harness deliberately stops
unless all 200 rows are marked `human_reviewed`. A `--allow-provisional` mode
exists solely to smoke-test code; it must never be reported because its labels
come from the same transparent weak-label rules used for training. This is the
most important limitation to clear before submitting.

## Method and baselines

The trivial baseline predicts `other` and always escalates. The simple baseline
is the visible phrase-to-intent rule set. The full system uses those rules only
for high-precision signals, otherwise a multinomial Naive Bayes text model;
it retrieves the closest same-intent historical customer message by TF-IDF
cosine similarity and uses its Apple reply as the draft’s evidence. The router
escalates PII-like text, confidence below 0.62, account/billing/order/repair,
feedback, or retrieval similarity below 0.13.

When human labels are complete, run `python3 -m src.evaluate ...` and replace
the table below with `reports/results.json` values. Report intent macro F1 and
accuracy, plus auto coverage, precision among auto-handled cases, and
escalation recall. Do not select the threshold using this same test set.

| System | Intent macro F1 | Intent accuracy | Auto coverage | Auto precision | Escalation recall |
|---|---:|---:|---:|---:|---:|
| Trivial: always escalate | pending human gold | pending | 0.00 | n/a | pending |
| Simple: keyword rules | pending human gold | pending | pending | pending | pending |
| Full: hybrid + retrieval gate | pending human gold | pending | pending | pending | pending |

For reply quality, an LLM-as-judge receives message, predicted decision, draft,
and retrieved evidence and scores groundedness, helpfulness, safety, and tone
from 1–5. A human independently scores the same 50 examples. The included
harness reports per-dimension and mean quadratic-weighted Cohen’s kappa. The
report should include the 50-row sample method, model/version/date, prompt
version, cost, score distribution, and kappa before treating judge scores as
evidence. API access is intentionally not assumed, and no synthetic agreement
number is reported.

## Failure analysis: hypotheses to validate on the completed gold set

1. **Context-only follow-ups are under-specified.** `G006` (“Messages from
   other people”) is a continuation without the prior turn. A first-turn agent
   should escalate for missing context rather than force an intent. Hypothesis:
   threaded context will improve intent accuracy but must be split by thread to
   avoid leakage.
2. **One message can contain two valid intents.** `G005` says a paid Apple
   Music subscription “still … doesn’t work.” Billing language may hide a
   service malfunction. Hypothesis: a primary intent plus issue attributes, or
   multilabel evaluation, will reduce these boundary errors.
3. **Screenshot/URL dependence hides the issue.** `G001` and `G004` rely on
   linked details. Text-only retrieval can ground a safe handoff but cannot
   diagnose the artifact. Hypothesis: image/OCR evidence and a separate
   “needs attachment review” gate would improve resolution quality.
4. **Historical drafts can be stale or too generic.** `G002` asks about a
   same-day shipment; a retrieved sales URL may be historically faithful but
   not enough to resolve a current order. Hypothesis: retrieve a response
   strategy, then verify policy/links against a current source before sending.
5. **Lexical rules miss symptom wording.** `G003` describes a speaker/case
   interaction but lacks the initial device keywords and is proposed as
   `other`. Hypothesis: character n-grams or a small pretrained encoder trained
   on independently labeled data will help noisy, abbreviated tweets.

## What is misleading about my headline number?

Even after labels are complete, a macro F1 on a deliberately balanced 200-row
set is not the deployed distribution, and it says nothing directly about a
historically plausible reply being correct today. The slice includes only
messages that did get an Apple reply, so it excludes silent/abandoned cases.
The test holdout is by tweet, not customer or time; repeat authors and
temporally similar incidents may make it easier. The full model also benefits
from explicit rules; a strong rule baseline is more diagnostic than a single
headline. Finally, safe automation is a selective prediction problem: coverage
and error severity matter more than raw accuracy. I would publish class-level
support, confidence/coverage curves, false-auto examples, source dates, and
human/LLM judge agreement next to—not behind—the headline.

## One more week

First, complete double annotation and resolve disagreements, then hold out by
conversation/customer and time. Replace weak-label training with 1–2k
human-labeled examples and compare calibrated linear/encoder models. Add a
time-aware retrieval index with response-strategy de-duplication and a current
approved-knowledge checker. Run a 100-case blinded human evaluation against
the historical reply and tune routing thresholds on a separate validation set
for a pre-declared false-auto budget. Finally, instrument feedback and drift
monitoring before allowing any automatic send.
