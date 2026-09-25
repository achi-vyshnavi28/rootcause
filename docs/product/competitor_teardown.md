# Competitor teardown: AI analytics assistants

> Based on public product pages and documentation as of 2026-09. Feature details are vendor claims to confirm in a
> demo; nothing here is from private sources.

## Landscape
| Type | Examples | What they do well | Where they fall short for "why did this change?" |
|---|---|---|---|
| Copilots inside BI tools | Power BI Copilot, Tableau Pulse / Tableau AI, Looker with Gemini | Live where the dashboards already are; governed data models | Mostly describe *what* changed on one chart; root-cause search across every dimension is limited or needs a prepared model |
| Search / chat-first analytics | ThoughtSpot (Spotter), Databricks AI/BI Genie, Snowflake Cortex Analyst | Natural-language questions over a curated semantic layer | Answer the question asked; they don't rank candidate causes or check whether the data itself is broken |
| General AI data assistants | ChatGPT data analysis, Julius | Fast, flexible, work on uploaded files | No connection to the governed warehouse; numbers are hard to audit; can invent values |
| Paper process | An analyst writing 10–20 SQL queries | Trusted, flexible | Hours to days per question |

## Where the buying decision is made
1. **Can I trust the number?** Every figure traceable to the query that produced it.
2. **Does it find the cause, or just restate the change?**
3. **Will it tell me when the data is wrong?** A duplicated-rows bug that looks like growth is the costly case.
4. **In regulated teams: can an auditor check it later?** Who asked, which model answered, proof nothing changed.

## How RootCause is positioned
| Buyer concern | RootCause answer | Evidence |
|---|---|---|
| Trust in numbers | Grounding check: numbers without evidence are flagged; each cites a query | 0% unsupported numbers on the 50-question benchmark |
| Finding the cause | Ranks segments by *abnormal* change, with mix-vs-rate for ratios | Root-cause Hit@1 93.3%, Hit@3 100% |
| Broken data | Data-quality checks run before blaming the business | Planted duplicate-payment bug found first (rc13–rc15) |
| Auditability (GxP) | Hash-chained answer log, model per answer, change-control gate | `docs/gxp/`, v1.2 |

## Honest gaps versus the leaders
- No dashboards or visual exploration (deliberate non-goal; RootCause complements a BI tool).
- One database and one semantic layer; the big vendors connect to many sources with managed governance.
- No user management yet (v1.3).

## Open questions to research next
How the BI copilots record the model version behind an answer; whether any vendor publishes an accuracy benchmark;
pricing per user vs per query for AI features.
