# Case study: RootCause

## Problem
When a key metric moves, analysts spend hours slicing data by region, product, seller and payment method to find out why. Generic "chat with your data" tools answer *what* happened, not *why*, and often invent numbers.

## Approach
1. **Route** the question: a root-cause question, a plain data question, or unanswerable.
2. **Define the metric** as structured output (per-order value, periods, filters). Code builds the SQL.
3. **Measure** the overall change and the change in every segment of 6 dimensions.
4. **Rank** segments by *abnormal* change (beyond their normal size); ratios get a mix/rate decomposition.
5. **Drill down** inside the top suspect.
6. **Check data quality** (duplicate rows) so ETL bugs aren't blamed on the business.
7. **Report** with cited query ids; a grounding check flags numbers not in the evidence.

## Results (50-question benchmark)
SQL execution accuracy **100%**, root-cause Hit@1 **93.3%** / Hit@3 **100%**, correct refusals **100%**, invented numbers **0%**, median 22 s per question on the free Gemini tier.

In the live UI, "Why did revenue jump in October 2017?" was correctly diagnosed as a **data bug** (duplicate payment rows 0% → 28.6%), and the matching incident report was found and cited without being asked.

## What failed and what I changed
- **Size mistaken for cause.** Raw "share of the change" always blames the biggest segment (Sao Paulo). I switched to *abnormal* change: actual change minus the change its normal size predicts.
- **Model retired mid-project.** The default Gemini model was withdrawn; I made the LLM layer provider-agnostic (LiteLLM) with a fallback model, so switching is one setting.
- **Invented arithmetic.** The report once quoted "552" (879 − 327), computed by the model rather than the code. The grounding check caught it; I added each segment's change to the evidence.
- **Benchmark honesty.** The first full run scored 80% on SQL. Four "wrong" answers were right but formatted differently (months as `2017-11`, labels as `On Time`, English category names); three failures were outages. I fixed the scorer for all questions, re-scored the saved answers without calling the LLM, and re-ran only the outage failures (decision log #13).
- **Free-tier limits.** Latency and 503 errors come from the free tier, not the agent; the median is 22 s.

## Next steps
Slack alert when the anomaly scanner fires, with an automatic investigation attached; a second domain (edtech); a semantic-layer editor so a new dataset can be connected without code.
