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
