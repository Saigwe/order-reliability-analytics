# Design decisions and lineage

## Lineage

```
raw (Parquet, as delivered)            silver                                   gold
order_lines ─────────────────────────> stg_order_lines (local order date) ─┐
order_events (immutable, retries) ──> stg_order_events (dedup, local date) ─┼─> int_deliveries (incremental) ─┐
shipments + warehouse_scans ────────> stg_shipments, stg_warehouse_scans ──> int_dispatch ───────────────────┼─> fct_order_line ─> fct_order
customers, sites, carriers, skus ───> stg_* ─────────────────────────────────────────────────────────────────┘        │
purchase_orders + receipts ─────────> stg_purchase_orders, stg_receipts ─────────> fct_po_line                        ├─> rpt_customer_otif_monthly
invoices + fx_rates + standard_fx ──> stg_invoices (C100), stg_fx_rates ────────> fct_ppv                             ├─> rpt_otif_failures (Pareto)
return_events ──────────────────────> stg_return_events (dedup) ────────────────> fct_return                         └─> rpt_exec_scorecard
```

## Decisions

1. **Events are immutable and deduplicated in staging.** A retried event keeps its `event_id`; staging keeps the first
   arrival. Downstream models never see a duplicate, and the count dropped is reported.
2. **Incremental on ingestion time, not event time.** `int_deliveries` reprocesses everything ingested in the last
   `incremental_lookback_days`. A proof of delivery that arrives a week late still has a recent `ingested_at`, so it
   lands; filtering on event time would have lost it. `make rerun` proves a cut-off build plus an incremental run
   equals a full build.
3. **Local dates.** Promise dates are local calendar dates at the shipping site, so delivery timestamps (UTC) are
   converted with the site's offset before comparing. Fixed offsets are a simplification: a production build would use
   IANA zones for daylight saving.
4. **Both promise dates are kept.** The headline uses the original promise because re-promising a line you are about to
   miss should not count as service. The latest-promise rate is shown next to it so the gap is visible.
5. **One denominator per fact.** On time, in full and OTIF all divide by eligible lines. Order OTIF is a separate fact,
   never an average of line rates.
6. **Customer, supplier and returns facts are not joined.** They share dimensions only. Supplier OTIF uses the
   supplier's promised date, not the customer's.
7. **PPV per each, in USD, with a two-part bridge.** Converting unit of measure first stops C100 lines from looking 100
   times dearer. Splitting at the standard FX rate separates what suppliers charged from what currency did.
8. **Quarantine, not delete.** Zero-quantity lines and deliveries for unknown order lines go to `rpt_quarantine` with a
   reason code, and a test asserts none reaches a KPI.
9. **Complete months only on the scorecard.** The extract date falls on 3 November, so November is left out rather than
   shown as a collapse.
