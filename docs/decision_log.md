# Decision log

Each entry: the decision, the alternatives rejected, and why.

## 1. LLM plans, code computes
- **Decision:** The LLM outputs a structured `MetricSpec` (what to measure, which periods). Deterministic builders generate the root-cause SQL; pandas computes contributions.
- **Rejected:** Letting the LLM write every analysis query and do the arithmetic.
- **Why:** Reproducible rankings (needed for Hit@k evals), fewer SQL errors, and no arithmetic hallucinations. The LLM still writes free-form SQL for plain data questions.

## 2. Rank by abnormal change, not raw contribution
- **Decision:** For totals, segment score = actual change − change expected from its baseline share. For ratios, rate effect + interaction from a mix/rate decomposition.
- **Rejected:** Ranking by raw share of the change.
- **Why:** The largest segment always "explains" the most in raw terms, which makes it a size effect rather than a cause.

## 3. Two safety layers for SQL
- **Decision:** `sqlglot` AST validation (single SELECT, no DML/DDL anywhere including CTEs, blocked functions, schema allow-list, LIMIT cap) plus a read-only role with `default_transaction_read_only` and `statement_timeout`.
- **Rejected:** Regex keyword blocking; relying on prompt instructions.
- **Why:** Regex misses `WITH d AS (DELETE ...)`; prompts are not a security boundary. Defence in depth.

## 4. LangGraph over a single prompt or a free-form ReAct agent
- **Decision:** An explicit state graph with retry edges.
- **Rejected:** One big prompt; an open-ended tool-calling loop.
- **Why:** Predictable cost and latency, testable nodes, bounded retries, and a clear audit trail.

## 5. Provider-agnostic LLM via LiteLLM, Gemini free tier by default
- **Decision:** One `complete_json` interface; model chosen by `LLM_MODEL`, with fallbacks.
- **Rejected:** Coupling to one vendor SDK.
- **Why:** Zero budget during development; being able to compare models on the same benchmark.

## 6. Planted-anomaly lab for ground truth
- **Decision:** `olist_lab` = real data + 5 deterministic, documented anomalies in separate months.
- **Rejected:** Judging root-cause answers by reading them.
- **Why:** Hit@k needs known answers; real data has no labelled causes.

## 7. Tests on DuckDB with a scripted LLM
- **Decision:** End-to-end agent tests run the real graph and real SQL on a synthetic Olist-shaped DuckDB database.
- **Rejected:** Mocking the database; tests needing PostgreSQL and an API key.
- **Why:** Free, fast CI that still exercises the SQL builders and the validator.

## 8. Native PostgreSQL instead of Docker (for now)
- **Decision:** Local PostgreSQL 16 on Windows.
- **Why:** CPU virtualization is disabled on the development laptop. Docker can be added later and built in CI.

## 9. Vision: an oriented crack filter beat a from-scratch PatchCore (negative result kept)
- **Result (KolektorSDD, test = every 3rd product folder):** the first classical filter reached ROC-AUC 0.56. After looking at the images (grainy texture, thin horizontal cracks, bright edge strips), a vertical-kernel black-hat plus horizontal averaging plus edge masking reached **0.89 AUC / 82% localisation**. Its 3 parameters were tuned on training products only.
- **Negative result:** a PatchCore-style memory bank with handcrafted HOG features stayed at 0.54. Handcrafted descriptors don't separate cracks from stochastic grain; the paper's pretrained CNN features are what make it work.
- **Next:** `notebooks/ksdd_patchcore_yolo_colab.ipynb` runs anomalib PatchCore (WideResNet-50) and YOLO segmentation on a free GPU with the same split.

## 10. scikit-learn, statsmodels and xxhash pinned below latest
- scikit-learn 1.9's compiled `_loss` module was blocked by Windows Application Control on the development laptop; 1.8 loads. The same happened later to statsmodels 0.15 (`_kalman_smoother`, pinned 0.14.5), xxhash 4.0 (imported by LangGraph's tracing library, pinned 3.6.0) and tiktoken 0.14 (imported by LiteLLM, pinned 0.9.0). The security policy was left untouched; CI on Linux runs the same pins.

## 11. Anomaly threshold |robust z| >= 6
- At 4, the STL detector flagged ordinary noise on a synthetic series; every real event found in Olist (Black Friday, New Year, the planted cancellations) scored above 11.

## 12. PatchCore with pretrained CNN features on CPU
- **Result (KolektorSDD, 5 random part-level splits, trained on good images only):** `vision/patchcore.py` (ResNet-18 layer2+3, greedy coreset of 4,000 patches) reached **ROC-AUC 0.872 ± 0.017**, AP 0.658, and caught 61.5% of defects at a 5% false-reject rate. The black-hat baseline on the same protocol scored 0.858 ± 0.063.
- **Takeaway:** pretrained features fixed the 0.54 of the handcrafted-feature memory bank (entry 9). Averages are similar to the classical filter, but results are 4× more stable across splits. Published numbers (> 0.95) need larger backbones and resolution: see the GPU notebook.

## 13. Benchmark scoring fixes, applied to all questions and disclosed
- **First full run (2026-09-24):** SQL 80%, root-cause Hit@1 86.7%, Hit@3 93.3%, refusals 100%, unsupported numbers 0%.
- **Failure review, question by question:**
  - sql12, sql24: correct months written `2017-11`; the answer key had `2017-11-01`. sql30: correct values labelled `Late`/`On Time` vs `late`/`on_time`. The scorer now treats `YYYY-MM` as the first of that month and compares text labels ignoring case and separators (`evals/scoring.py`, tests added).
  - sql09: correct counts with English category names; the question does not specify a language, so the English-name query was added as an accepted answer (`alt_gold`).
  - sql14, sql15, rc07: never reached the agent's reasoning (network `getaddrinfo` failure overnight; Gemini 503 "high demand"). Re-run with `--ids`.
- **Rule:** scorer changes apply to every question and are re-applied to the saved answers with `evals/rescore.py` (no LLM calls, so no chance to "retry until right"). Nothing was changed in the agent between the run and the rescore.
- **Latency:** the reported average was dominated by one 11.7-hour hang during the network outage; the report now also gives the median.

## 14. The LLM is a supplier that can change under you
- **What happened:** during development the Gemini model the agent was first configured with was retired by the provider. Nothing in our code changed, but every call started failing. The fix was to move to `gemini-3.6-flash` with a fallback model list.
- **Lesson:** a hosted model is an external dependency whose behaviour can change without a release on our side. Since then the model id is pinned in config, recorded in every benchmark report (`evals/reports/latest.json`) and, from v1.2, on every stored answer. `docs/gxp/04_validation_approach_and_traceability.md` turns this into a change-control rule: a new model is accepted only after the benchmark passes.

## 15. Tamper-evident audit log instead of trusting the database (v1.2)
- **Why:** the GxP assessment (`docs/gxp/`) showed that stored answers are records an investigator may rely on, so a later edit must be detectable (21 CFR Part 11 §11.10(e), ALCOA+ *Original*).
- **How:** each saved run appends an `audit_log` entry with a SHA-256 digest of the run as stored (question, answer, executed SQL, row counts, model) and the previous entry's hash. `GET /audit/verify` recomputes the chain **and** re-reads every run, so edits made directly in the database, deleted runs, removed log entries and runs inserted outside the app are all reported (`tests/test_audit_log.py`).
- **Legacy runs:** the 64 runs saved before v1.2 were baselined once at go-live (event `run_baselined`) and are protected from then on.
- **Known limits:** the sequence number is assigned by the application and the database user can still write to `audit_log`. A hash chain makes tampering *visible*, not impossible; production would add database-level append-only permissions (gap G2).
