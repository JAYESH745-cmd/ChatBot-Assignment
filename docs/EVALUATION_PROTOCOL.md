# Evaluation protocol and provenance

## Classification and routing

`data/golden_eval.csv` is the final 200-record evaluation file. Every row has
an intent, expected route, escalation reason, reviewer note, and
`review_status=human_reviewed`. The sample contains real customer messages
from the committed AppleSupport slice. It was selected to include each of the
eight operational intents; it is therefore a coverage-oriented evaluation set,
not an estimate of natural production prevalence.

`src.evaluate` removes the exact 200 golden tweet IDs before fitting the intent
model and building the retrieval index. It evaluates the trivial baseline,
simple keyword baseline, and hybrid retrieval agent against the final labels.

The historical `proposed_*` columns and `data/author_annotations.csv` are
bootstrap/sampling audit material. They are not inputs to the evaluator and
must not replace the completed human-reviewed fields in the final golden file.

## Reply-quality calibration

`data/judge_calibration.csv` contains a fixed 50-example packet with four
human scores and four manual AI-rubric scores per example: groundedness,
helpfulness, safety, and tone (each 1–5). The source AI-rubric scores are in
`data/ai_judge_scores.csv`; `src.merge_judge_scores` validates matching example
IDs and score ranges before adding them to the calibration file.

Run `make judge-agreement` to create `reports/judge_agreement.json`. It
reports exact agreement, mean absolute error, full score distributions, and
quadratic-weighted Cohen's kappa only when both raters have variation. This
last condition matters here: constant human ratings make kappa mathematically
undefined, not zero.

The calibration is evidence about the rubric judge, not proof that retrieval
drafts are correct or suitable for automatic sending. In particular, low
helpfulness and tone agreement trigger human review rather than automation.
