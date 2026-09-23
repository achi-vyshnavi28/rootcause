# PRD: RootCause, the "why did this metric change?" analyst

| | |
|---|---|
| Status | v1 built (phases 1-4); this PRD describes what exists and what is next |
| Owner | Vyshnavi Achi |
| Last updated | 2026-09-23 |

## 1. Problem
When a core metric moves (orders, cancellations, late deliveries, revenue), someone has to find out why. Today that means an analyst writing 10-20 SQL queries, slicing by region, seller, category and payment method, and checking whether the data itself is broken. It takes hours to days. Meanwhile teams guess, or react to the wrong cause.

Existing "chat with your data" tools answer *what* (a number), not *why*. They also invent numbers without warning, and nobody can check how they got there.

## 2. Users and jobs to be done
| User | Job | Pain today |
|---|---|---|
| Ops / category manager | "Orders in MG fell 20%. Is it us, a seller, or a carrier?" | Waits on the data team; decides on gut feel |
| Data analyst | Answer ad-hoc "why" questions fast and defensibly | Repetitive slicing; hard to show the work |
| Founder / exec | Trust the answer enough to act | Can't tell a real change from a data bug |

## 3. Goals and success metrics
| Goal | Metric | Target v1 | Measured by |
|---|---|---|---|
| Find the true cause | Root-cause Hit@1 on planted anomalies | ≥ 80% | `evals/run_evals.py` |
| Answer data questions correctly | SQL execution accuracy | ≥ 80% | benchmark |
| Never invent numbers | Answers with unsupported numbers | ≤ 5% | grounding check |
| Know when to say no | Correct refusals on unanswerable questions | ≥ 90% | benchmark |
| Be fast enough to use | Median time per investigation | < 3 min (free tier), < 30 s (paid tier) | run logs |
| Be trusted | 👍 share of rated runs | ≥ 70% | feedback table |

**Non-goals (v1):** changing data, forecasting as the main product, dashboards (BI tools already do that), multi-tenant SaaS.

## 4. Requirements
| ID | Requirement | Priority | Status |
|---|---|---|---|
| F1 | Ask in plain English; route to root-cause, data question, or refusal | Must | Done |
| F2 | Compare two periods and break the change down by every dimension | Must | Done |
| F3 | Rank segments by *abnormal* change (not size); mix vs rate for ratios | Must | Done |
| F4 | Drill down inside the top segment | Should | Done |
| F5 | Detect data-quality problems (duplicate rows) before blaming the business | Must | Done |
| F6 | Cite every number with the query that produced it (audit trail) | Must | Done |
| F7 | Flag numbers in the answer that are not in the evidence | Must | Done |
| F8 | Only read data; block unsafe SQL | Must | Done (validator + read-only role) |
| F9 | Pull related release notes / incident logs into the report | Should | Done (hybrid RAG) |
| F10 | Suggest next checks and an experiment | Should | Done |
| F11 | Proactively flag unusual days | Could | Done (`/anomalies`) |
| F12 | Simulate a fix before rollout | Could | Done (optimization/, offline) |
| F13 | Slack / email alerts | Could | Next |
| F14 | Connect a new dataset without code (semantic layer editor) | Should | Next |

## 5. User experience
Ask → progress while investigating → report: headline change, confidence, summary with citations [Q#]/[D#], contribution chart, drill-down, next checks, suggested experiment → expandable audit trail with every SQL query → 👍/👎.

## 6. Risks and mitigations
| Risk | Mitigation |
|---|---|
| LLM writes harmful SQL | AST validator + read-only role + statement timeout (two independent layers) |
| LLM invents numbers | Maths done in code; grounding check flags unsupported numbers |
| Size mistaken for cause | Abnormal-change ranking (decision log #2) |
| Data bug blamed on business | Duplicate-row checks outrank business causes |
| Free-tier latency / limits | Provider-agnostic (LiteLLM), fallback model, retries |
| Wrong answer trusted blindly | Confidence levels; "insufficient evidence" status |

## 7. Release plan
| Release | Scope | Exit criteria |
|---|---|---|
| v1 (built) | F1-F12 on Olist | Benchmark targets met; live link |
| v1.1 | Slack alert on anomaly → auto-investigation (F11+F13) | 1 week of daily alerts without false positives |
| v2 | Semantic-layer editor + second domain (edtech) | A new dataset connected in under 1 hour |
