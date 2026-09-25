# 01 Intended use and classification: RootCause in a GxP setting

**Question this package answers:** could a pharma quality team use an AI analyst on GxP data, and under what
controls? RootCause was built on e-commerce data; this package assesses it as if a QA team wanted to use it to
investigate trends in quality data (deviation rates, batch yield, OOS results). It is a paper exercise on a portfolio
system, following GAMP 5 (2nd edition) and FDA CSA thinking, not a claim that RootCause is validated.

## 1. Proposed intended use
| | |
|---|---|
| Users | QA analysts and quality managers |
| Use | Find *candidate* explanations for a change in a quality metric (e.g. "why did the deviation rate rise in June?") and show the SQL evidence for each number |
| Decision it supports | Where to look first in an investigation |
| Decision it must **not** make | Batch disposition, deviation classification, CAPA closure, or any GxP record entry. A person makes and signs those in the QMS |
| Data | Read-only copies of quality data (never the system of record) |

Keeping RootCause as **decision support with a human in the loop** is the single most important control: it keeps the
tool out of direct product-quality decisions, which lowers the risk class and therefore the validation effort (CSA).

## 2. GAMP 5 classification
| Component | Category | Reason |
|---|---|---|
| RootCause application (agent, validators, scoring) | **5: custom** | Written for this purpose |
| LLM (Gemini via API) | Treated as a **configured external service with an AI model** (GAMP 5 2nd ed., Appendix D11: AI/ML) | Behaviour is not fully specified and can change when the provider updates the model; controlled by pinning the model version and a regression benchmark (see 04) |
| PostgreSQL / DuckDB | 1: infrastructure | Standard software, qualified at installation |

## 3. Is it a Part 11 system?
| Part 11 question | Answer for the intended use | Consequence |
|---|---|---|
| Does it create electronic records required by a predicate rule? | Only if its answers are kept as evidence in an investigation | Treat stored runs as records: attributable, time-stamped, tamper-evident (implemented in v1.2) |
| Does it apply electronic signatures? | No | Out of scope; signatures happen in the QMS |
| Does it change GxP data? | No: read-only database role + SQL validator | Verified by `tests/test_sql_validator.py` and the read-only role write test |

## 4. What changes in v1.2 because of this assessment
1. **Tamper-evident audit log:** every saved answer is hash-chained with its SQL and the model that produced it
   (`backend/db/app_store.py`, `GET /audit/verify`).
2. **Model version recorded per answer**, so an answer can be traced to the model that produced it.
3. **Model change control:** a model change is only accepted after the 50-question benchmark passes (see 04).
