# Resume bullets and LinkedIn post (real numbers only)

## Resume: project entry
**RootCause: AI analyst agent that explains why business metrics change** · Live: rootcause-demo.streamlit.app · GitHub
*Python, LangGraph, LiteLLM (Gemini), PostgreSQL, DuckDB, FastAPI, Streamlit, sqlglot, pandas, pytest, GitHub Actions*

- Built a LangGraph agent that plans an investigation, generates validated read-only SQL and ranks the segments behind a metric change by abnormal contribution (mix/rate decomposition), on 100k real Olist orders.
- Reached **100% SQL execution accuracy**, **93% root-cause Hit@1 (100% Hit@3)** and **0% invented numbers** on a 50-question benchmark built with 5 planted anomalies of known cause.
- Prevented hallucinated figures with a grounding check (every number must trace to query evidence) and blocked unsafe SQL with two layers: an AST validator and a read-only database role.
- Detected data-quality bugs before business causes (duplicate payment rows 0% → 29%) and retrieved the matching incident report with hybrid BM25 + embedding search.
- Deployed a public demo (DuckDB + SQLite, no DB server) on Streamlit Cloud; 88 automated tests in CI.

Pick 3-4 of these per application. Add one line from the modules below when the role asks for it:
- **Backend / support:** Django + DRF + Celery webhook service with idempotency, dead-letter replay, reconciliation and OAuth refresh; 14 failure-scenario regression tests and a support runbook.
- **ML:** PatchCore surface-defect detection on KolektorSDD (ROC-AUC 0.87); NASA CMAPSS remaining-useful-life model (RMSE 15.5 vs 41.9 baseline); order forecasting (MAPE 23.6% vs 29.6% naive).
- **Optimisation:** OR-Tools routing on real São Paulo addresses (72% shorter than naive); SimPy what-if simulation of carrier capacity loss.
- **Product / analyst:** PRD, BRD, process maps and user stories traced to tests; cohort, funnel and growth-accounting analysis; A/B toolkit with CUPED; 3-scenario Excel financial model.

## Interview honesty notes
- Be ready to explain *why* each design choice was made; the answers are in `docs/decision_log.md`.
- If asked about the first benchmark run: it scored 80% on SQL; 4 answers were correct but formatted differently, 3 failed due to outages; the scorer was fixed for all questions (decision log #13).
- Latency on the free tier is 20 s to 3 min; say so rather than hiding it.

## LinkedIn post (draft)
> When a business metric drops, someone has to find out **why**. That usually means hours of slicing data by region, seller, product and payment method.
>
> I built **RootCause**, an AI analyst agent that does that investigation and shows its proof.
>
> Ask "Why did revenue jump 50% in October?" and it:
> 🔹 plans the investigation and writes SQL that is validated before it runs (read-only, so it can't change data)
> 🔹 breaks the change down by every segment, and ranks *abnormal* change, not just the biggest region
> 🔹 checks the data first: here it found duplicated payment rows (0% → 29%), meaning the "growth" was a bug
> 🔹 pulls the matching incident report and cites every number with the query behind it
>
> On a 50-question benchmark with planted problems of known cause: **100% correct SQL, the true cause ranked #1 in 93% of cases, 0 invented numbers.**
>
> Biggest lesson: the largest segment always *looks* like the cause. Measuring change beyond normal size fixed that.
>
> 🔗 Live demo: rootcause-demo.streamlit.app
> Built with Python, LangGraph, PostgreSQL/DuckDB, Gemini, Streamlit. Feedback very welcome!
>
> #AI #DataAnalytics #LLM #Python #BuildInPublic
