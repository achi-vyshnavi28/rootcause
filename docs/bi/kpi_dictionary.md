# KPI dictionary

One definition per metric, used identically by RootCause (`backend/agent/semantic_layer.yaml`), the SQL in
`analytics/product_analytics.py`, and the Power BI measures in `dax_measures.md`.

| KPI | Definition | Formula (star schema `olist_mart`) | Grain | Owner | Notes |
|---|---|---|---|---|---|
| Orders | Orders placed | `COUNT(DISTINCT fact_order_items.order_id)` | order | Growth | Date = purchase date |
| GMV | Total paid by customers | `SUM(fact_payments.payment_value)` | payment | Finance | Check for duplicate payment rows before trusting jumps |
| Item revenue | Value of items sold | `SUM(fact_order_items.price)` | item | Finance | Excludes freight |
| AOV | Average order value | `(items + freight) / orders` | order | Growth | Excludes canceled/unavailable |
| Freight share | Freight as % of order value | `SUM(freight) / SUM(price + freight)` | item | Ops | High values hurt conversion |
| Late delivery rate | Delivered orders that arrived after the promised date | `AVG(is_late)` over delivered orders | order | Ops | `is_late` is NULL for undelivered orders |
| Delivery days | Purchase → customer delivery | `AVG(delivery_days)` | order | Ops | Delivered orders only |
| Cancellation rate | Orders canceled | `canceled orders / all orders` | order | Ops | |
| Avg review score | Customer rating 1–5 | `AVG(review_score)` | order | CX | Reviews averaged per order first |
| Month-1 retention | Customers of cohort M who buy again in M+1 | cohort matrix column 1 | person | Growth | Uses `customer_unique_id`, not `customer_id` |
| Quick ratio | Growth efficiency | `(new + resurrected) / churned` | person-month | Growth | > 1 means the active base grows |
