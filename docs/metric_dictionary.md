# Metric dictionary

Every rate has one stated grain, numerator, denominator and due date. Thresholds are demo assumptions.

## Customer service (grain: order line, `fct_order_line`)

| Metric | Numerator | Denominator | Notes |
|---|---|---|---|
| Eligible line | | | `ordered_qty - cancelled_qty > 0` and original promise date on or before the extract date. Zero-quantity lines are quarantined |
| On time | eligible lines whose first delivery is on or before the promise date | eligible lines | local date at the shipping site |
| In full | eligible lines whose delivered quantity (to date) covers the eligible quantity | eligible lines | |
| OTIF | eligible lines whose cumulative quantity delivered on or before the promise date covers the eligible quantity | eligible lines | split shipments count cumulatively; an early delivery counts as on time |
| OTIF, latest promise | as OTIF, against the latest promise date | eligible lines | shown next to the headline to expose re-promising |
| Order OTIF | orders whose every eligible line is OTIF | orders with at least one eligible line | `fct_order` |
| Failure reason | first failing step, in order: short shipment (stock); late dispatch (dispatched later than promise minus standard transit); carrier transit delay (transit longer than standard + `carrier_grace_days`); not delivered yet; other | | |

The headline uses the original promise. Set `otif_promise_policy: latest` in `dbt_project.yml` to switch `is_otif`.

## Supplier service (grain: purchase-order line, `fct_po_line`)

| Metric | Numerator | Denominator | Notes |
|---|---|---|---|
| Eligible PO line | | | promised date on or before the latest receipt date in the extract |
| Supplier OTIF | lines whose quantity received by the promised date covers the quantity ordered | eligible PO lines | |
| Units late at promise | `ordered_qty - received_by_promise`, floored at 0 | | drives the escalation queue |

## Returns (grain: RMA, `fct_return`)

| Metric | Definition |
|---|---|
| Turnaround | days from receipt at the warehouse to the first disposition event. Median and P90 by month received |
| Stage | Awaiting receipt, Awaiting inspection, Inspected no disposition, Closed |
| Open age | days from receipt to the extract, for returns without a disposition |
| Recovery value | quantity x standard cost x recovery rate for the disposition (restock 95%, refurbish 55%, return to vendor 80%, recycle 3%: demo assumptions) |
| Open recoverable value | open returns at the restock and refurbish average rate |
| Handling cost | receive $4 + inspect $6 + refurbish $18 or recycle $2.50 (demo assumptions) |
| Cost per return | handling cost / returns |

## Purchase price variance (grain: invoice line, `fct_ppv`)

| Metric | Definition |
|---|---|
| Quantity, each | invoice quantity x units per unit of measure (C100 = 100) |
| Actual unit price, USD | local price per each x actual FX rate on the invoice date |
| PPV | (actual unit price USD - standard unit cost USD) x quantity. Positive is unfavourable (demo convention) |
| Price effect | (local price per each x standard FX - standard unit cost) x quantity |
| FX effect | local price per each x (actual FX - standard FX) x quantity. Price effect + FX effect = PPV on every line |
| Credit notes | negative invoice quantity: excluded from PPV, counted on the Data quality page |
| Late invoices | invoiced after the receipt month closed: PPV is booked to the receipt month |

## ABC bands (`dim_sku`)

SKUs ranked by 12-month ordered value. A: the SKUs making the first 80% (`abc_a_share`), B: the next 15%
(`abc_b_share`), C: the rest. Both cut-offs are dbt vars.
