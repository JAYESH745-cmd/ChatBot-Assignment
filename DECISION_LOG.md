# Decision log

1. **Chose Apple Support.** It has a large enough response volume in the primary corpus to support a fixed, small slice and a historical-resolution retriever.
2. **Used only explicit `@AppleSupport` mentions.** Direct reply edges alone included occasional cross-brand/thread-linking artefacts; an explicit mention is a higher-integrity brand boundary.
3. **Kept direct customer → Apple replies only.** It gives each retrieval item an unambiguous historical resolution without trying to reconstruct noisy multi-branch threads.
4. **Committed a 3,200-pair slice, not the source corpus.** It keeps reproduction fast and avoids asking reviewers to download 516 MB for a take-home result.
5. **Created eight operational intents.** They are small enough for reliable annotation and route to materially different operational outcomes.
6. **Separated weak labels from gold labels.** Transparent rules bootstrap the local model; the completed golden CSV carries human-reviewed final labels and preserves the original proposals separately for audit.
7. **Stratified the 200-row gold set.** A pure random sample would underrepresent repair/order cases and make macro F1 volatile.
8. **Held out exact golden tweet IDs before training and retrieval.** This blocks the clearest retrieval leakage path; author-level overlap remains a reported limitation.
9. **Used a standard-library Naive Bayes model.** It is runnable in a blank Python 3.9 environment and easy to explain or change live.
10. **Retained a keyword baseline.** It exposes how much headline intent accuracy could come from obvious lexical triggers rather than generalized understanding.
11. **Grounded drafts in historical replies rather than free generation.** Each prediction records the evidence tweet, customer text, response, and similarity score for audit.
12. **Escalated account, billing, order, and repair by policy.** Correct intent is not authorization to take a case-specific customer action.
13. **Made low confidence and low retrieval similarity escalation triggers.** Coverage is deliberately traded for safer automation.
14. **Made LLM judging optional for fresh runs.** No API key is needed to reproduce classification/routing metrics or the supplied frozen rubric-calibration analysis.
15. **Measured human–judge calibration.** The 50-case packet reports exact agreement, MAE, score distributions, and weighted kappa where variation makes kappa defined.
