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

## Results
_Fill in from `evals/reports/latest.json` and `baseline.json` after running the benchmark._

## What failed and what I changed
_Record real failures here as they happen: SQL errors the validator caught, wrong periods, ranking mistakes, rate limits._

## Next steps
RAG over release notes and incident logs, automatic anomaly detection, more domain packs, a React UI, and Docker plus deployment.
