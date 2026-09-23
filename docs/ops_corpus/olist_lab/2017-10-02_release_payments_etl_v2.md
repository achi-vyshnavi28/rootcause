---
title: "Release 2017.10.1: payments ETL migrated to v2 pipeline"
type: release_note
date: 2017-10-02
---
The nightly job that copies payment records from the payment gateway into the order_payments table was migrated from the v1 batch loader to the new v2 incremental pipeline.

Known risk: the v2 pipeline retries failed batches. If a batch partially succeeds, rows may be written twice. Deduplication on (order_id, payment_sequential) is planned for release 2017.11.

Owner: data-platform team.
