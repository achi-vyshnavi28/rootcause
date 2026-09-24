# RootCause

**An AI analyst agent that finds *why* a business metric changed, and proves every number with the SQL behind it.**

> "Why did orders drop in April 2018?" → RootCause plans the investigation, writes and safety-checks SQL, breaks the change down by every segment, looks inside the top suspect, checks for data bugs, and writes a report where each claim cites the query that produced it.

![CI](../../actions/workflows/ci.yml/badge.svg)

## Why it's different
- **Investigates, doesn't just answer.** A LangGraph agent: route → define metric → measure → drill down → data-quality check → report.
- **The LLM plans, code proves.** The LLM decides *what* to measure; deterministic SQL builders and pandas maths compute *why*. No LLM arithmetic.
- **Abnormal change, not size.** A state with 40% of orders "explains" 40% of any drop. RootCause ranks segments by change *beyond* their normal share (and splits ratio metrics into mix vs rate effects).
- **Data bugs are caught.** Duplicate-row checks flag ETL problems before blaming the business.
- **Safe by design.** Two layers: an `sqlglot` validator (SELECT only, no dangerous functions, allowed schemas, row caps) and a read-only database role with a query timeout.
- **Audited and measured.** Every query is logged. A hallucination check flags any number in the report that isn't in the evidence. A 50-question benchmark measures accuracy.
- **Provider-agnostic.** Gemini (free tier) by default; Groq, Ollama, Claude or OpenAI via one setting (LiteLLM).

## Architecture
```
Streamlit UI / FastAPI ──► LangGraph agent ──► LLM (via LiteLLM)
                               │
            ┌──────────────────┼──────────────────────┐
     sqlglot validator   semantic layer (YAML)   pandas root-cause maths
            │             + SQL builders          (contribution, mix/rate)
            ▼
   PostgreSQL (read-only role) ── olist / olist_lab
   PostgreSQL (app schema) ── runs, audit trail, feedback
```

## Benchmark
50 questions with known answers (`evals/questions.yaml`):

| Category | Count | Metric |
|---|---|---|
| Text-to-SQL | 30 | Execution accuracy vs gold SQL |
| Root cause on 5 planted anomalies (`olist_lab`) | 15 | Hit@1 / Hit@3 |
| Unanswerable questions | 5 | Correct refusal |

Results (Gemini free tier, `gemini-3.6-flash`, 2026-09-24; full report in `evals/reports/latest.json`):

| Metric | Result |
|---|---|
| SQL execution accuracy | **100%** (30/30) |
| Root-cause Hit@1 / Hit@3 | **93.3% / 100%** (the one miss ranked the true cause 2nd) |
| Correct refusals | **100%** (5/5) |
| Answers with unsupported (invented) numbers | **0%** |
| Median / average time per question | 22 s / 50 s |
| LLM cost per question | ~$0.004 at list price ($0 on the free tier) |

How these numbers were reached, including the first run (80% SQL), the scoring fixes and the outage re-runs, is recorded in [docs/decision_log.md](docs/decision_log.md) (entry 13).

## Other results on real data
| Module | Result |
|---|---|
| Anomaly scanner (STL + robust z) | Finds Black Friday 2017 and the planted August 2018 cancellations |
| Order forecast (28 days, 4-fold backtest) | Holt-Winters MAPE 23.6% vs seasonal-naive 29.6% |
| Late-delivery risk at purchase time | ROC-AUC 0.72; top-decile late rate 2x average |
| Portuguese review sentiment | F1 0.83 (TF-IDF + logistic regression) |
| Turbofan remaining useful life (NASA CMAPSS FD001) | RMSE 15.5 cycles vs 41.9 baseline |
| Surface-defect detection (KolektorSDD) | PatchCore ROC-AUC 0.87 ± 0.02 (CPU, ResNet-18) |
| Route optimisation (46 real Sao Paulo stops) | 72% shorter than naive routing |

## Quickstart (Windows, local PostgreSQL)
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in passwords and GEMINI_API_KEY
```
Download the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) into `data/raw/`, then:
```bash
python -m data.load_olist            # 9 tables into schema olist
python -m data.setup_readonly_role   # read-only user for the agent (proves DELETE is refused)
python -m data.inject_anomalies      # olist_lab with 5 planted root causes
streamlit run frontend/app.py        # UI
uvicorn backend.api.main:app         # API (docs at /docs)
python -m evals.run_evals            # benchmark
python -m pytest                     # tests (no DB or API key needed)
```

## Project layout
```
backend/agent/       LangGraph graph, prompts, semantic layer, analysis, grounding check
backend/guardrails/  SQL validator
backend/tools/       root-cause statistics
backend/db/          read-only executor, audit-trail store
backend/api/         FastAPI
frontend/            Streamlit UI
data/                loaders, read-only role, planted anomalies
evals/               benchmark questions, scoring, runner
tests/               unit + end-to-end tests (DuckDB + scripted LLM)
docs/                decision log, case study
```

## Limitations
- Root-cause analysis is order-centric (every metric is measured per order); other data models need a new semantic layer.
- Segments that overlap (an order with two sellers) are counted in each, so shares are approximate for those dimensions.
- One level of drill-down.
