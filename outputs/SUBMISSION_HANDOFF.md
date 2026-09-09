# Hiver take-home handoff

The workspace contains a runnable Apple Support Twitter agent and the material
required for a high-integrity submission:

- `README.md` — reproduce steps, data attribution, pipeline, and judge command
- `data/apple_support_slice.csv` — fixed 3,200-pair real-data slice
- `data/golden_eval.csv` — 200-example human-reviewed evaluation set with
  row-level intent, routing, reason, and review notes
- `reports/results.json` — held-out baseline and agent metrics
- `data/judge_calibration.csv` and `reports/judge_agreement.json` — frozen
  50-case human/AI-rubric calibration data and agreement analysis
- `src/` — extraction, classifier/retriever/router, evaluator, and optional LLM judge
- `REPORT.md` — six-page-max report narrative including failure analysis
- `DECISION_LOG.md` — 15 non-obvious implementation choices

Tests pass with `make test`; `make all` regenerates the held-out result without
network access. The report explicitly shows the weak helpfulness/tone agreement
and the limits of a small coverage-oriented evaluation set; neither the agent
nor its judge is presented as ready for autonomous customer replies.
