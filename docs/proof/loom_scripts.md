# Loom scripts

Record in the live app (rootcause-demo.streamlit.app). Speak slowly. Screen: app on the left, nothing else open.
Before recording, run the question once so the free model is warm, then record a second run (or cut the waiting part).

## Master demo (90 seconds)

| Time | Show | Say |
|---|---|---|
| 0:00-0:10 | The app home page | "When a business metric drops, analysts spend hours slicing data to find out why. I built RootCause, an AI analyst that does that investigation and shows its proof." |
| 0:10-0:25 | Click the example "Why did revenue jump in October 2017 compared to September 2017?" (Olist lab dataset) | "This is real Olist e-commerce data. I planted five problems whose causes I know, so I can test whether the agent finds them." |
| 0:25-0:50 | The result: +50% headline, red data-quality banner, summary with [Q14] and [D2] | "Revenue jumped 50%. Instead of celebrating, RootCause checked the data first: payment rows were duplicated, 0% to 29%. It also found the incident report about the payments pipeline, on its own." |
| 0:50-1:05 | Expand the audit trail, click one query | "Every number links to the SQL that produced it. The SQL is checked before it runs, and the database user can only read, so the AI can't change data." |
| 1:05-1:20 | Evals tab | "On a 50-question benchmark: 100% of SQL answers correct, the true root cause ranked first 93% of the time and in the top 3 every time, and 0 invented numbers." |
| 1:20-1:30 | Back to the report | "The hardest lesson: the biggest region always looks like the cause. I rank by abnormal change instead. Happy to walk through how it would work on your data." |

## 60-second versions (swap the middle section)

| For | Question to run | Emphasise |
|---|---|---|
| AI engineer / forward-deployed | "Why did the late delivery rate increase in June 2018 compared to May 2018?" | LangGraph workflow, retries, validator, grounding check, provider-agnostic LLM |
| Product / analyst roles | "Why did the number of orders drop in April 2018 compared to March 2018?" | Abnormal-change ranking, drill-down, next checks and suggested experiment |
| Backend / production support | Revenue question + show the runbook and webhook tests on GitHub | Data-quality detection, idempotency, dead-letter replay, 14 failure-scenario tests |
| ML / vision roles | Screen-share `ml/reports/*.json` and the decision log | PatchCore on KolektorSDD, NASA RUL model, honest negative results |

## Closing line for a specific company
"I'd love to try this on [company]'s [metric, e.g. conversion / delivery SLA]. The semantic layer is one YAML file, so pointing it at new data is a small job."
