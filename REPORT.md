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
edges alone. Apple was selected because this filter still yielded 136,059
eligible direct pairs in the source: enough historical coverage for retrieval
without needing the full corpus. The raw corpus is not committed; the compact
derived slice is. Preparation makes two streaming passes, reconstructs a
customer-to-direct-response edge rather than a brittle full tree, strips URLs
and handles for modeling, and retains the original text for audit.

The intended golden set is 200 held-out real messages, stratified across the
eight classes (25/25/25/25/30/30/20/20). Annotators see the message but not the
historical reply or proposal columns. A second reviewer adjudicates a random
40-row subset. Exact golden tweet IDs are removed before both model fitting and
retrieval, preventing direct answer leakage.

**Integrity status.** The repository contains an author-reviewed,
AI-assisted 200-row label pass, marked as such in every CSV row. The results
below are therefore preliminary—not independent human-gold results—and must
not be presented as final validation. A blind external human relabel and a
second-reviewer adjudication pass remain required before submission. This is a
deliberate provenance safeguard, rather than a fabricated claim of human
agreement.

## Method and baselines

The trivial baseline predicts `other` and always escalates. The simple baseline
is the visible phrase-to-intent rule set. The full system uses those rules only
for high-precision signals, otherwise a multinomial Naive Bayes text model;
it retrieves the closest same-intent historical customer message by TF-IDF
cosine similarity and uses its Apple reply as the draft’s evidence. The router
escalates PII-like text, confidence below 0.62, account/billing/order/repair,
feedback, or retrieval similarity below 0.13.

The preliminary author-reviewed run is stored in `reports/results.json`.
Report intent macro F1 and accuracy, plus auto coverage, precision among
auto-handled cases, and escalation recall. Do not select the threshold using
this same test set.

| System | Intent macro F1 | Intent accuracy | Auto coverage | Auto precision | Escalation recall |
|---|---:|---:|---:|---:|---:|
| Trivial: always escalate | 0.0185 | 0.0800 | 0.0000 | n/a | 1.0000 |
| Simple: keyword rules | 0.6143 | 0.5900 | 0.3000 | 0.8833 | 0.9286 |
| Full: hybrid + retrieval gate | 0.5763 | 0.5800 | 0.3250 | 0.8462 | 0.8980 |

These values are from `reports/results.json`, whose label source is explicitly
`author_reviewed_ai_assisted_not_independent_human_gold`. They are useful
diagnostics, not final claims. The full agent does not beat the keyword
baseline on this preliminary intent set; this is an important negative result,
not something to obscure. It offers slightly higher automation coverage (32.5%
vs. 30.0%) but with lower safe-auto precision (84.6% vs. 88.3%). The evidence
gate's mean retrieval cosine is 0.2855 and passes 90.5% of cases; similarity is
a retrieval diagnostic rather than reply-quality proof.

The complete per-intent precision/recall/F1 and 8×8 confusion matrices are in
`reports/results.json`. Device technical issues are the largest error source:
only 28/81 were correctly predicted, with 10 mistaken for billing and 21 for
how-to. This is consistent with short tweets mixing symptoms, subscriptions,
and questions. The router made **10 false auto-handles** (dangerous errors) and
**47 unnecessary escalations** (safe but costly errors); it is not ready for
autonomous release. Representative error rows are machine-exported under
`retrieval_agent.error_examples` in the same artifact.

For reply quality, an LLM-as-judge receives message, predicted decision, draft,
and retrieved evidence and scores groundedness, helpfulness, safety, and tone
from 1–5. A human independently scores the same 50 examples. The included
harness reports per-dimension and mean quadratic-weighted Cohen’s kappa. The
judge rubric and calibration CSV template are included, but no API key or human
rater was available in this environment, so no LLM score or synthetic
agreement number is reported. Before submission, retain the model/version/date,
prompt version, cost, score distribution, and kappa from a frozen 50-row sample.

## Failure analysis: top five failure modes

1. **Context-only follow-ups.** `G006`, “Messages from other people,” should
   be `other → escalate`; the agent predicted `device_technical_issue →
   escalate`. It selected the safe action but invented a task. Hypothesis:
   prior turns carry the missing referent. Fix: thread-aware context with a
   conversation-level split to avoid leakage.
2. **Subscription language masks a technical failure.** `G005`, an Apple
   Music subscriber whose service “doesn’t work,” was labelled
   `device_technical_issue → escalate` but predicted
   `billing_subscription → escalate`. The route was safe but the intent was
   wrong. Fix: model a primary technical intent plus a billing-entitlement
   attribute, or evaluate multilabel alternatives.
3. **Ambiguity can produce a dangerous false auto.** `G026` mentions
   “employment details” but gives no product context. Expected `other →
   escalate`; the agent emitted `how_to → auto_handle`. Fix: require explicit
   Apple product/service evidence before permitting auto-handling.
4. **Lexical triggers cause unnecessary escalations.** `G007` reports Face ID
   stopped working after unboxing. Expected `device_technical_issue →
   auto_handle`; “unboxing” steered the agent to `repair_service → escalate`.
   Fix: prioritize the reported symptom over generic hardware terms and tune
   the repair gate on a validation set.
5. **Historical grounding does not guarantee a current resolution.** `G002`
   asks about a same-day shipment; the agent correctly escalates, but the
   retrieved historical sales-team direction cannot check current order status.
   Fix: retrieve a response strategy, then verify links/policy against a
   current approved knowledge source before any send.

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
