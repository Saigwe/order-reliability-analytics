# Order reliability analytics

[![ci](https://github.com/Saigwe/order-reliability-analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Saigwe/order-reliability-analytics/actions/workflows/ci.yml)
[![dashboards](https://github.com/Saigwe/order-reliability-analytics/actions/workflows/pages.yml/badge.svg?branch=main)](https://saigwe.github.io/order-reliability-analytics/)

**Live dashboards: [saigwe.github.io/order-reliability-analytics](https://saigwe.github.io/order-reliability-analytics/)**

Overall service levels can hide a small cluster of suppliers, warehouses or SKUs causing most failures. This project
traces a customer OTIF breach to the accountable team and to the order lines behind it, and puts returns processing and
purchase price variance next to it so operations and finance can decide which losses to tackle first.

It is built end to end: a seeded synthetic data generator, a dbt warehouse on DuckDB (immutable event tables,
deduplication, an incremental model with a backfill test), six web dashboards, a DAX measure spec and a decision memo.
The scenario is modelled on customer OTIF, supplier OTIF, reverse-logistics and PPV reporting at a global
consumer-electronics company.

**Everything here is invented.** Orrin Electronics, its customers, suppliers, carriers, SKUs and every number come from
`generator/simulate.py`. The results below are demo results on synthetic data, not any company's figures.

## The business

Orrin Electronics ships 60 SKUs from three distribution centres (DC-US Memphis, DC-EU Venlo, DC-AP Singapore) to
customers in five regions, through six carriers, and buys from eight suppliers in USD, EUR, CNY and JPY. November 2025
to October 2026, extracted on 3 November 2026.

## Grains

Customer, supplier and returns facts are kept apart: they have different grains, due dates and denominators.

| Fact | Grain | Due date | Eligible when |
|---|---|---|---|
| `fct_order_line` | customer order line | original promise (latest kept alongside) | quantity left after cancellations > 0 and promise date passed |
| `fct_order` | customer order | every eligible line | at least one eligible line |
| `fct_po_line` | supplier purchase-order line | supplier's promised date | promised date passed |
| `fct_return` | return (RMA) | none: turnaround is measured | received at the warehouse |
| `fct_ppv` | supplier invoice line, priced per each in USD | receipt month | not a credit note |

Shared dimensions: `dim_date`, `dim_sku` (with configurable ABC bands), `dim_site`, `dim_customer` (region),
`dim_supplier`.

## What the reports find

The generator plants known problems; `tests/test_planted_answers.py` checks the marts find each one with the reports'
own logic. From the current build ([analysis/results.md](analysis/results.md) is regenerated on every build):

| Finding | Where |
|---|---|
| Customer OTIF is 81.6% over 12 months against the original promise; order OTIF (every line OTIF) is 66.4% | Executive |
| A chip shortage at Meridian Semis (supplier OTIF 86.6% to 61.5%) took DC-EU OTIF on the SKUs built on its chips to 35.4% in Jul to Sep, against 83.6% for other SKUs; split shipments arrived short at the promise date | Customer OTIF, Supplier OTIF |
| DC-US re-promises lines it is about to miss: 97.2% OTIF against the latest promise, 83.0% against the original | Customer OTIF |
| Late warehouse dispatch is the most common failure (59.5% of failed lines in the last three months) | Customer OTIF |
| Rapidline's February delay took DC-AP lines it carried to 49.5% OTIF | Customer OTIF |
| PPV is $984k unfavourable: $1.14M of it is the CNY move since April (FX effect); Kestrel Passives' 9% price rise adds $78k (price effect) | PPV |
| An inspection backlog took refurbish turnaround from 5 to 36 days; 210 returns are open, 86 of them over 30 days | Returns |

The demo story compares the two losses: the returns backlog holds about $36k of recoverable value, the CNY exposure
over $1M. Clear the refurbish queue because it is cheap, but the money is in currency.

## How it fits together

```
generator/simulate.py  ->  data/raw/*.parquet (16 tables + answer key)
dbt/ (DuckDB)          ->  silver: staging (dedup, local dates) + int_deliveries (incremental) + int_dispatch
                       ->  gold:   dims, 5 facts, 9 report marts                       (63 models and tests)
dashboards/            ->  export.py -> data.json -> build.py -> 6 static pages (ECharts), GitHub Pages
analysis/              ->  report.py -> results.md; decision_memo.md
bi/                    ->  DAX measures and report spec for a Power BI build on the same marts
docs/                  ->  metric dictionary, design decisions and lineage, demo script
tests/                 ->  planted answers, reconciliation, dashboards, generator
```

## What is tested

- **Deduplication.** Retried events (same `event_id`) are kept once at first arrival; scanner double-fires are dropped;
  duplicate RMA events are dropped. Counts appear on the Data quality page.
- **Backfills and reruns.** `make rerun` builds the warehouse from events ingested up to a cut-off, then runs the
  incremental delivery model again; late-arriving and retried events land correctly and the totals equal a full build.
- **Time zones.** Delivery and dispatch dates are local to the shipping site (a 23:30 delivery in Memphis is that day).
- **Split deliveries, cancellations, changed promises, early arrivals.** OTIF counts the cumulative quantity delivered by
  the promise date against the quantity left after cancellations; both promise policies are stored.
- **Reconciliation.** The executive scorecard equals the line fact month by month; on time, in full and OTIF share one
  eligible denominator; order OTIF requires every eligible line; price effect + FX effect = PPV on every invoice line;
  C100 invoices are priced per each.
- **Quarantine.** Zero-quantity lines and deliveries for unknown order lines are kept out of every KPI with a reason code.

## Run it

```bash
pip install -r requirements.txt
make all        # generate, dbt build, dashboards, results (about a minute)
make rerun      # backfill from a cut-off, then incremental: totals must not move
make test       # pytest against the built warehouse
make serve      # dashboards on http://localhost:8000
```

On Windows without `make`, run the commands in the `Makefile` in order. Demo assumptions (promise policy, ABC cut-offs,
lookback window, carrier grace days, recovery rates, handling costs) are dbt vars in `dbt/dbt_project.yml`.

## Limits

- Synthetic data with planted patterns: the findings show the method works, not that any real operation behaves this way.
- Failure reasons are assigned by a fixed rule order (short shipment, late dispatch, carrier transit). A real line can
  fail for more than one reason; this build reports the first.
- Recovery rates and handling costs per return are assumptions, so recoverable value is an estimate.
- No Power BI file is included: `bi/` holds the DAX measures and report spec. The web dashboards show each page.

## Built by

[Stanley Igwe](https://saigwe.github.io). MIT licence.
