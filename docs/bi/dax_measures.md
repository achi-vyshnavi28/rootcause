# Power BI setup and DAX measures

## Connect
1. Power BI Desktop → **Get data → PostgreSQL database** → server `127.0.0.1`, database `rootcause`.
2. Sign in with the **read-only** user (`rootcause_reader`). Dashboards never need write access.
3. Load the tables from schema **`olist_mart`**: `fact_order_items`, `fact_payments`, `dim_date`, `dim_customer`, `dim_seller`, `dim_product`.

## Relationships (star schema, single direction, many-to-one)
| From (many) | To (one) |
|---|---|
| fact_order_items[purchase_date_key] | dim_date[date_key] |
| fact_order_items[customer_id] | dim_customer[customer_id] |
| fact_order_items[seller_id] | dim_seller[seller_id] |
| fact_order_items[product_id] | dim_product[product_id] |
| fact_payments[purchase_date_key] | dim_date[date_key] |
| fact_payments[customer_id] | dim_customer[customer_id] |

Mark `dim_date` as the date table.

## Measures
```DAX
Orders = DISTINCTCOUNT ( fact_order_items[order_id] )

GMV = SUM ( fact_payments[payment_value] )

Item Revenue = SUM ( fact_order_items[price] )

AOV = DIVIDE ( SUM ( fact_order_items[item_total] ), [Orders] )

Freight Share = DIVIDE ( SUM ( fact_order_items[freight_value] ), SUM ( fact_order_items[item_total] ) )

Late Delivery Rate =
    DIVIDE (
        CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[is_late] = 1 ),
        CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), NOT ISBLANK ( fact_order_items[is_late] ) )
    )

Avg Review Score = AVERAGE ( fact_order_items[review_score] )

Orders MoM % =
    VAR Prev = CALCULATE ( [Orders], DATEADD ( dim_date[date_key], -1, MONTH ) )
    RETURN DIVIDE ( [Orders] - Prev, Prev )

GMV YTD = TOTALYTD ( [GMV], dim_date[date_key] )

Payment Row Duplicates =
    COUNTROWS ( fact_payments )
        - COUNTROWS ( SUMMARIZE ( fact_payments, fact_payments[order_id], fact_payments[payment_sequential] ) )
```

## Report pages
1. **Executive overview:** KPI cards (Orders, GMV, AOV, Late Delivery Rate, Avg Review Score) plus MoM %, and a monthly trend.
2. **Operations:** late delivery rate by customer state (map) and by seller state; delivery days distribution.
3. **Customers:** cohort retention matrix (import `analytics/output/olist_product_analytics.xlsx` → `cohort_retention`), growth accounting.
4. **Data health:** Payment Row Duplicates by month. It should be 0; a spike means an ETL bug (see RootCause scenario S5).

Save the file as `analytics/powerbi/olist_overview.pbix` and add screenshots to the README.
