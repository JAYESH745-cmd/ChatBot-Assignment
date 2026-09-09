# Hiver take-home handoff

The workspace contains a runnable Apple Support Twitter agent and the material
required for a high-integrity submission:

- `README.md` — reproduce steps, data attribution, pipeline, and judge command
- `data/apple_support_slice.csv` — fixed 3,200-pair real-data slice
- `data/golden_eval.csv` — 200-example independent, stratified annotation worksheet
- `src/` — extraction, classifier/retriever/router, evaluator, and optional LLM judge
- `REPORT.md` — six-page-max report narrative including failure analysis
- `DECISION_LOG.md` — 15 non-obvious implementation choices

Tests pass with `make test`. The classifier/routing evaluator intentionally
will not publish headline metrics until a human completes the 200 gold labels.
This is a correctness guard, not a missing implementation. Follow
`docs/ANNOTATION_GUIDE.md`, then run the command in `README.md`; use
`docs/JUDGE_RUBRIC.md` to produce the required judge–human agreement evidence.
