# RootCause — Project Specification

> An AI operations analyst platform. It ingests a business's data, documents, images, sensor streams and events; detects what changed; finds **why**; predicts what's next; recommends and simulates fixes; and proves every claim with a traceable audit trail.

**User flow:** Connect data → ask *"Why did X drop?"* (or get an automatic anomaly alert) → the agent investigates (SQL, statistics, documents, logs, images, sensors) → report with evidence, forecast, recommended fix and experiment → act through integrations (CRM, Slack, WhatsApp, email) → measure impact.

**Build rule:** One platform, 11 modules. Build the core first (Modules 1, 2, 9, 10, 11), deploy, start applying, then add the other modules one at a time. Each module must work on its own and be demoable separately.

**Working rule:** Built together with Claude Code. For every phase, the developer runs the code, reads it, and answers 2–3 interview questions about it. Every decision is recorded in `docs/decision_log.md`.

---

## 1. Modules

### Module 1 — Data engine (pipelines + warehouse)
- Python collectors (APIs, web, files), scheduled with shell/cron; large files processed with Unix tools (awk, sed, xargs, GNU parallel). **This module is written by hand, without AI tools**, and the README says so.
- PostgreSQL (main analytics DB), BigQuery adapter (event data), MongoDB (raw app logs).
- Star schema (fact + dimension tables), KPI dictionary, data-quality checks.
- Advanced SQL: CTEs, window functions, self-joins, lift/PMI, reconciliation queries, indexing, partitioning, EXPLAIN ANALYZE.
- Explicit data structures: heap for top-k, graph/union-find for clustering.

### Module 2 — AI analyst agent (core)
- LangGraph flow: Understand → Retrieve schema → Plan → Generate SQL → Validate → Execute → Verify → Drill down → Context (RAG) → Hypothesize → Report → Log.
- Text-to-SQL with a self-correction loop (max 3 retries).
- sqlglot guardrails: read-only DB role, SELECT-only allowlist, auto-LIMIT, statement timeout, EXPLAIN cost check, prompt-injection defence.
- Root-cause statistics: period A vs B comparison, segment contribution ranking, mix vs rate decomposition.
- "Insufficient evidence" refusal when no segment explains enough of the change.
- Report: summary, root cause, evidence table, charts, confidence, next checks, suggested experiment. **Every number references a query ID** (enforced by output schema).

### Module 3 — Document intelligence (RAG)
- LlamaIndex ingestion of PDFs and tables (financial filings, contracts, SOPs, release notes, incident logs).
- Hybrid retrieval: BM25 + embeddings + reranker; pgvector (Qdrant as an alternative); compare 2 embedding models.
- LangChain extraction chains → structured JSON with schema validation.
- Contradiction and red-flag detection across documents, with page-level citations.
- Rule monitoring: extract thresholds/obligations from documents and check them against live data (early-warning alerts).

### Module 4 — Integrations and reliability service (Django)
- Django + DRF, Celery + Redis workers, Celery Beat scheduled jobs.
- Webhook ingestion (payments + logistics sandboxes): signature verification, idempotency keys, dead-letter queue, replay, missing-event detection.
- OAuth token refresh; 4xx/5xx/429 handling with retries and exponential backoff.
- Nightly reconciliation against provider APIs (data-sync issues).
- Integrations: CRM (HubSpot), Slack, email, WhatsApp; n8n + Zapier flows.
- Sentry error tracking, structured logs (readable by the agent), PII masking.
- Support CLI tools (`lookup_order`, `replay_event`), a runbook per incident type, escalation template.
- 10 injected failure scenarios, each with root-cause write-up and regression test.

### Module 5 — ML engine
- scikit-learn baselines → PyTorch / Hugging Face fine-tuned text classifier (DistilBERT), TensorFlow/Keras comparison.
- Cost-aware model routing: small model for easy cases, LLM for hard ones.
- Lead/risk scoring, learning-to-rank recommendations, LLM-structured features from free text (behavioural/psychometric signals).
- Forecasting (LightGBM/Prophet with backtesting), anomaly detection (STL + robust z-score), survival analysis / remaining useful life.
- MLflow tracking, model card, model published on Hugging Face Hub.

### Module 6 — Vision, audio and IoT
- OpenCV classical methods (background subtraction, optical flow, morphology) + fine-tuned YOLO/RT-DETR detector (large model, GPU-trained).
- OCR fine-tuning, video tracking (ByteTrack), dwell/zone analytics, privacy blurring.
- PatchCore anomaly detection implemented from the paper.
- Audio event detection (CNN on spectrograms).
- IoT: simulated MQTT sensor stream, Kalman filter from scratch, simulated reject signal to an actuator/PLC.
- Linear algebra from scratch: homography rectification.
- C extension for NMS/preprocessing with Python bindings, benchmarked vs Python.
- ONNX / TFLite export; FPS benchmarks CPU vs GPU.
- Synthetic data generation for messy / low-label data.

### Module 7 — Optimization and simulation
- OR-Tools: scheduling, resource allocation (machines/shifts/staff), vehicle routing.
- SimPy discrete-event simulation to test a proposed fix before rollout.
- What-if panel: change inputs → forecast and cost impact.

### Module 8 — Analytics, BI and business layer
- Product analytics: funnels, cohorts, retention curves, growth accounting (new / retained / resurrected / churned).
- Experimentation: power calculation, SRM check, CUPED, A/B readouts.
- Unit economics (LTV, CAC, payback) + 3-scenario financial model with runway.
- Power BI (DAX) or Tableau executive dashboard; Looker Studio on BigQuery; same analysis in Excel (Power Query, pivots, XLOOKUP, what-if).
- Review/text mining (including Hinglish/multilingual) → themes → churn drivers.
- Competitor teardown and market analysis.

### Module 9 — Quality, testing and compliance
- pytest (unit + integration), Playwright (UI), Postman collection (API).
- Eval harness in CI — build fails if accuracy regresses.
- Test-case library (preconditions, steps, expected result), versioned in Git.
- LLM feature: PRDs/user stories → test cases; flags untestable requirements.
- Bug reports in Jira (repro, expected vs actual, environment, severity), regression sweeps, UAT plan + sign-off.
- Compliance-grade features: role-based permissions, e-signatures, immutable audit trail, ALCOA+ data-integrity checks.
- Validation pack: URS, FRS, traceability matrix, IQ/OQ/PQ protocols with executed evidence, deviation log, GAMP 5 category note, risk-based CSA note.

### Module 10 — Frontend and product surface
- React + Tailwind app, Node/Express gateway (MERN with MongoDB), D3/Plotly charts. Streamlit allowed for internal tools.
- Pages: Ask · Report · Audit trail · Anomalies · Forecast & what-if · Vision · Experiments · Evals scoreboard · Internal ops console (with explanations).
- Figma wireframes → quick v0/Lovable prototype → production React build.
- In-app feedback → improvement log; PostHog analytics on the app itself.

### Module 11 — DevOps, MLOps and observability
- Docker, Docker Compose, GitHub Actions (tests + evals + lint), Linux servers.
- AWS (EC2 GPU, S3) + GCP (Cloud Run); managed Postgres (Neon/Supabase); Vercel front end.
- Langfuse tracing, token/cost + latency tracking, Sentry, health checks, versioned releases.

---

## 2. Architecture

```
[React UI] ── [Node/Express gateway] ── [FastAPI backend] ── [LangGraph agent]
                                              │                    │
                                      [Postgres: app DB]   ┌───────┼──────────┬───────────┐
                                      (runs, audit trail,  │       │          │           │
                                       evals, feedback)  [SQL]   [RAG]     [Stats/ML]  [Vision]
                                                           │       │          │           │
                                            [Postgres/BigQuery] [pgvector] [pandas/scipy/ [OpenCV/
                                             read-only analytics]          sklearn/torch]  YOLO]
                                                           │
                                         [LLMs: Claude API (+ OpenAI baseline)]
                                                           │
                                     [Langfuse traces · cost · latency · Sentry]

[Django integrations service] ── Celery/Redis ── webhooks · CRM · Slack · WhatsApp · email
```

## 3. Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3.11+, SQL, C, JavaScript/Node, Bash |
| API | FastAPI, Pydantic; Django + DRF (integrations service) |
| Agents / LLM | LangGraph, LangChain, LlamaIndex, Claude API (strong model for reasoning, cheap model for simple steps), OpenAI (baseline) |
| Databases | PostgreSQL, BigQuery, MongoDB, pgvector (Qdrant alt) |
| SQL safety | sqlglot, read-only role |
| Stats / ML | pandas, NumPy, SciPy, statsmodels, scikit-learn, PyTorch, TensorFlow/Keras, Hugging Face, LightGBM, Prophet, MLflow |
| Vision / IoT | OpenCV, Ultralytics YOLO / RT-DETR, OCR, ByteTrack, ONNX, TFLite, MQTT |
| Optimization | OR-Tools, SimPy |
| Queues | Celery, Redis |
| Frontend | React, Tailwind, Node/Express, D3/Plotly, Streamlit |
| BI | Power BI (DAX) or Tableau, Looker Studio, Excel |
| Testing | pytest, Playwright, Postman, eval harness |
| DevOps | Docker, Docker Compose, GitHub Actions, AWS, GCP, Vercel, Neon/Supabase |
| Observability | Langfuse, Sentry |
| Product tools | Figma, v0, Lovable, n8n, Zapier, Jira/Linear, Notion, draw.io (BPMN) |

## 4. Data

### Primary dataset
**Olist Brazilian E-commerce** (Kaggle, public): 9 related tables, ~100k orders, 2016–2018.

### Planted anomalies (ground truth for evals) — `data/inject_anomalies.py`
1. Delivery delays for 3 sellers in one state during one month.
2. Payment failures for one payment type after a date.
3. Review-score drop in one product category.
4. Mix shift: traffic moves to a low-converting region.
5. Data bug: duplicate rows from a bad join (agent must flag data quality, not a business cause).

### Domain packs (one engine, many datasets — switch with one command)

| Pack | Dataset | Demo question |
|---|---|---|
| E-commerce | Olist + webhook logs | "Why are orders stuck or dropping?" |
| Product / app | GA4 BigQuery public sample | "What's driving day-7 retention down?" |
| Edtech | OULAD | "Why do learners drop in week 3?" |
| Finance | Public company filings + financials | "Why did margin fall? Any red flags?" |
| Manufacturing | Bosch / SECOM + defect images | "Which station causes the defect spike?" |
| IoT | NASA CMAPSS | "Which machines fail next, and why?" |
| Social / brands | Reddit / social engagement | "Which brands share audiences? Why did engagement spike?" |
| People / matching | Speed Dating (Columbia) | "Which signals actually predict a match?" |
| Regulated ops | Synthetic batch/deviation records | "Which step causes most deviations?" |

## 5. Evaluation

### Eval set (start with 50, grow later) — `evals/questions.yaml`
| Type | Count | Metric |
|---|---|---|
| Text-to-SQL | 30 | Execution accuracy (result matches gold query) |
| Root cause on planted anomalies | 15 | Hit@1 / Hit@3 |
| Unanswerable / trick | 5 | Correct refusal rate |

### Metrics to publish
- SQL execution accuracy, root-cause Hit@1/Hit@3, hallucination rate (numbers not backed by a query), correct-refusal rate
- RAG citation accuracy, extraction F1
- ML: F1/AUC, NDCG, forecast MAPE, RUL RMSE
- Vision: mAP, OCR accuracy, FPS, C vs Python speed-up
- Cost (₹/$) and latency per investigation; retry/self-correction rate
- Baseline (single-prompt LLM) vs agent v1 vs agent v2 table — **fill with real numbers only**
- Real usage: number of users, feedback score, one measured impact

## 6. API endpoints (core)
- `POST /ask` — question → run ID
- `GET /runs/{id}` — report, status, trace
- `GET /runs/{id}/audit` — all queries with results
- `POST /runs/{id}/feedback` — rating + comment
- `GET /anomalies` — detected anomalies
- `GET /evals/latest` — eval scores
- `POST /datasets/switch` — change domain pack

## 7. Repo structure

```
rootcause/
├── backend/
│   ├── api/            # FastAPI routes
│   ├── agent/          # LangGraph graph, nodes, prompts
│   ├── tools/          # sql_tool, rag_tool, stats_tool, ml_tool, vision_tool
│   ├── guardrails/     # sqlglot validator, read-only checks
│   ├── adapters/       # domain packs
│   ├── observability/  # tracing, cost tracking
│   └── db/             # models, migrations
├── integrations/       # Django + DRF + Celery service
├── ml/                 # training, MLflow, model cards
├── vision/             # OpenCV/YOLO, C extension, edge export
├── optimization/       # OR-Tools, SimPy
├── pipelines/          # hand-written collectors, shell scripts, cron
├── analytics/          # SQL notebooks, BI files, Excel, financial model
├── evals/
│   ├── questions.yaml
│   ├── run_evals.py
│   └── reports/
├── data/
│   ├── load_olist.py
│   └── inject_anomalies.py
├── frontend/           # React app + Node gateway
├── tests/              # pytest, Playwright, Postman
├── docs/
│   ├── case_study.md
│   ├── decision_log.md
│   ├── killed_ideas.md
│   ├── architecture.png
│   ├── product/        # PRD, BRD, BPMN, user stories, interviews
│   ├── quality/        # test-case library, bug log, UAT, runbooks
│   └── validation/     # URS, FRS, RTM, IQ/OQ/PQ, deviations
├── docker-compose.yml
├── .github/workflows/ci.yml
├── PROJECT_SPEC.md
└── README.md
```

## 8. Build phases

| Phase | Modules | Time (with Claude Code) |
|---|---|---|
| **1. Core — start applying after this** | 1, 2, 9 (evals/tests), 10 (basic UI), 11 (deploy) | ~2 weeks |
| 2. Documents + integrations | 3, 4 | ~2 weeks |
| 3. ML + analytics/BI | 5, 8 | ~2 weeks |
| 4. Vision/IoT + optimization | 6, 7 | ~2–3 weeks |
| 5. Product/compliance docs + domain packs + proof | rest of 9, product docs, packs | ~1–2 weeks |

### Phase 1 breakdown
| Days | Deliverable |
|---|---|
| 1–2 | Repo, Docker Compose Postgres, Olist loaded, read-only role, schema + glossary, anomaly-injection script |
| 3–4 | FastAPI + text-to-SQL agent with validator and retry loop |
| 5–7 | First 30 eval questions + baseline scores |
| 8–9 | Stats tool: period comparison, segment contribution, mix/rate decomposition |
| 10–11 | Full LangGraph investigation flow + report with query references + audit trail |
| 12–13 | Root-cause + refusal evals, v1 vs v2 comparison, pytest + GitHub Actions |
| 14 | Basic UI (Ask, Report, Audit, Evals) + deploy → live link |

## 9. Prerequisites (developer does these)
- Install: Python 3.11+, Docker Desktop, Git, Node.js
- Accounts: Anthropic API (OpenAI optional), GitHub, Kaggle, deploy host (Render/Fly/AWS), Neon or Supabase
- Set API keys yourself as environment variables (never commit them; use `.env` in `.gitignore`)
- Download the Olist dataset from Kaggle

## 10. Proof of work (exact deliverables)
1. Live platform link with a public evals scoreboard
2. GitHub repo: clean modules, CI badge, `docker compose up` quickstart
3. README: one-liner, GIF, architecture diagram, results table, limitations, roadmap
4. Case study: problem → approach → decisions → results → what failed → next
5. Decision log + killed-ideas log
6. 90-second master Loom + 60-second Loom per domain pack
7. Docs pack: PRD, BRD, BPMN maps, user stories, test-case library, runbooks, validation pack, KPI dictionary, release notes, user guide
8. Benchmark report (agent + ML + vision)
9. Power BI/Tableau dashboard + Excel model + financial model
10. Technical blog post + LinkedIn/X build log
11. Separate from the platform: 2–3 merged open-source PRs (Django e-commerce project) + DSA/SQL practice profiles

### Loom script (90 seconds)
1. 0–10s — "When a metric drops, teams spend days finding out why. RootCause does it in seconds, with proof."
2. 10–50s — Ask a live question; agent steps stream; report + contribution chart.
3. 50–65s — Click a claim → its SQL in the audit trail. "Every number is traceable."
4. 65–80s — Evals scoreboard: accuracy vs plain LLM, cost, latency.
5. 80–90s — One hard lesson learned + how it applies to the viewer's business.

### Resume bullets (fill with real numbers)
- Built **RootCause**, an AI analyst agent (LangGraph, Claude API, FastAPI, PostgreSQL) that diagnoses why business metrics change — **X% SQL execution accuracy**, **Y% root-cause Hit@1** on a 50-question benchmark.
- Designed an eval harness with planted-anomaly ground truth; cut hallucinated numbers from **A% to B%** via query-grounded reporting and verification.
- Built SQL guardrails (sqlglot, read-only roles, cost limits) and CI regression evals; deployed with Docker on AWS at **₹N per investigation, M s average latency**.

## 11. Skills covered (summary)
**Programming:** Python · SQL · C · JavaScript/Node · Bash · data structures
**Backend:** FastAPI · Django · DRF · REST · webhooks · OAuth · Celery · Redis · integrations
**Data:** PostgreSQL · BigQuery · MongoDB · pgvector · star schema · advanced SQL · ETL · large data · Unix tools
**AI/GenAI:** Claude/OpenAI APIs · prompt engineering · structured outputs · LangGraph · LangChain · LlamaIndex · agents · RAG · embeddings · reranking · guardrails · evals · model routing
**ML:** scikit-learn · PyTorch · TensorFlow · Hugging Face · NLP · ranking · forecasting · anomaly detection · survival analysis · MLflow
**Vision/audio/IoT:** OpenCV · YOLO/RT-DETR · OCR · tracking · audio CNN · ONNX/TFLite · MQTT · Kalman · homography
**Math/OR:** linear algebra · statistics · A/B testing · decomposition · OR-Tools · simulation
**Analytics/BI:** funnels · cohorts · retention · unit economics · financial modelling · Power BI/Tableau · Looker Studio · Excel
**Product/BA:** interviews · PRD · BRD · BPMN · user stories · Figma · prototyping · n8n/Zapier · UX heuristics · teardowns · roadmap · business case
**Quality/compliance:** pytest · Playwright · Postman · test cases · bug reports · UAT · traceability · audit trail · e-signatures · validation docs
**DevOps/MLOps:** Git · Docker · GitHub Actions · Linux · AWS · GCP · Sentry · Langfuse
**Frontend:** React · Tailwind · D3/Plotly · Streamlit
