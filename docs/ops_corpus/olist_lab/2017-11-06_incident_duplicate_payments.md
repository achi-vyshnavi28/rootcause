---
title: "Incident INC-231: duplicate payment rows in October"
type: incident
date: 2017-11-06
---
Finance reported that October GMV in the dashboard was much higher than the amount settled by the payment gateway.

Investigation found that the v2 payments ETL wrote some payment rows twice during retries. Business activity was normal; the jump in revenue is a reporting artefact.

Action: add a unique constraint on (order_id, payment_sequential) and backfill a deduplicated copy.
