# Hiver take-home handoff

The workspace contains a runnable Apple Support Twitter agent and the material
required for a high-integrity submission:

- `README.md` — reproduce steps, data attribution, pipeline, and judge command
- `data/apple_support_slice.csv` — fixed 3,200-pair real-data slice
- `data/golden_eval.csv` — 200-example stratified evaluation set with
  author-reviewed, AI-assisted labels and row-level provenance
- `reports/results.json` — preliminary held-out baseline and agent metrics
- `data/judge_calibration_template.csv` — frozen, stratified 50-case packet
  for independent human/LLM judge calibration
- `src/` — extraction, classifier/retriever/router, evaluator, and optional LLM judge
- `REPORT.md` — six-page-max report narrative including failure analysis
- `DECISION_LOG.md` — 15 non-obvious implementation choices

Tests pass with `make test`. The evaluator runs on the author-reviewed labels
but marks the result as preliminary rather than independent human gold. Before
submission, an external human must blind-review the 200 labels and complete the
50-case judge-calibration packet using `docs/ANNOTATION_GUIDE.md` and
`docs/JUDGE_RUBRIC.md`. No human-agreement result has been fabricated.
