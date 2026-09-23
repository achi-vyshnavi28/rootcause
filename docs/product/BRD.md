# BRD: Automated root-cause analysis for operations metrics

## 1. Business objective
Cut the time from "a metric moved" to "we know why and what to do" from **1-3 analyst days to under 1 hour**, and stop decisions being made on data bugs.

## 2. Scope
**In:** order, delivery, cancellation, review and revenue metrics on the order data warehouse; comparison of two periods; explanation by customer region, seller, category and payment type; documented events (release notes, incidents).
**Out:** changing any data; marketing attribution; real-time streaming (daily granularity is enough).

## 3. Stakeholders
| Stakeholder | Interest | Involvement |
|---|---|---|
| Head of Operations (sponsor) | Faster incident response | Approves scope, signs off UAT |
| Data / analytics team | Fewer repetitive requests; trusted answers | Maintains semantic layer and benchmark |
| Category and ops managers | Self-serve answers | Primary users, UAT testers |
| Engineering / platform | Security, cost | Reviews DB access and deployment |
| Finance | GMV correctness | Consumer of data-quality alerts |

## 4. Current state (as-is)
See `process_maps.md` (as-is). Ops notices a drop in a dashboard → ticket to the data team → analyst queues it (0.5-2 days) → writes 10-20 queries → finds a cause or not → Slack thread → decision. Data bugs are often found only after a wrong decision.

## 5. Future state (to-be)
See `process_maps.md` (to-be). The anomaly scanner or a user asks RootCause → an automated investigation in minutes with an audit trail → the user reviews the evidence and acts, escalating to an analyst only when confidence is low.

## 6. Business requirements
| ID | Requirement | Rationale | Acceptance |
|---|---|---|---|
| BR1 | Explain a metric change by segment with quantified contribution | Core value | Hit@1 ≥ 80% on the benchmark |
| BR2 | Every figure traceable to its source query | Trust, auditability | 100% of report numbers cite a query or are flagged |
| BR3 | Detect data-quality issues before business explanations | Avoid wrong decisions | All planted data-bug scenarios reported as data quality |
| BR4 | No write access to business data | Security | Write test refused (`setup_readonly_role`) |
| BR5 | Answer in under 3 minutes on the free tier | Usability | Median latency in benchmark report |
| BR6 | Say "not enough evidence" instead of guessing | Trust | Refusal accuracy ≥ 90% |

## 7. Non-functional requirements
Security (read-only role, validator, secrets in `.env`), privacy (PII masking in logs), cost (free-tier LLM by default, cost per run tracked), reliability (retries, provider fallback), maintainability (tests in CI, decision log).

## 8. Business case
Assumptions (edit in `analytics/output/marketplace_financial_model.xlsx` style):
| Item | Value |
|---|---|
| "Why" investigations per month | 40 |
| Analyst hours per investigation today | 4 |
| Loaded analyst cost per hour (INR) | 900 |
| Share handled by RootCause without an analyst | 60% |
| Monthly analyst time saved | 40 × 4 × 60% = **96 hours ≈ ₹86,400** |
| Running cost (free LLM tier + small server) | ≈ ₹1,500 / month |
| One avoided wrong decision per quarter from a data bug | not quantified (upside) |

Payback: build effort is recovered in under 2 months at these assumptions.

## 9. Assumptions and constraints
The order warehouse is the source of truth; daily freshness is enough; the LLM free tier rate limits apply; no Docker on the development machine.

## 10. Sign-off
Sponsor, Data lead, Engineering lead. See `user_stories.md` for acceptance criteria and `../quality/test_cases.md` for the UAT script.
