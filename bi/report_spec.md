# Report specification

A Power BI report on the gold marts. The web dashboards implement each page; this spec is what a Power BI build would
follow. Measures are in [measures.dax](measures.dax).

## Model

- Facts: `fct_order_line`, `fct_order`, `fct_po_line`, `fct_ppv`, `fct_return`. Facts never join to each other.
- Dimensions: `dim_date` (marked date table; customer facts join on `original_promise_date`, supplier on
  `promised_date`, PPV on `received_date`, returns on `received_at` date), `dim_sku`, `dim_site`, `dim_customer`,
  `dim_supplier`. Single-direction filters from dimensions to facts.
- Row-level security (optional): one role per site, filtering `dim_site`.

## Pages

| Page | Visuals | Drill-through |
|---|---|---|
| Executive | KPI cards (OTIF %, OTIF % latest promise, Order OTIF %, Supplier OTIF %, PPV $, Open Returns); OTIF by month; decision list | to Customer OTIF by month or region |
| Customer OTIF | region x month matrix (OTIF %); failed lines by reason; Pareto (Failed Lines, Failed Lines Cumulative %); promise-policy comparison | to Order detail |
| Order detail | table of eligible lines: promise dates, eligible qty, delivered by promise, shipments, reason | from any customer visual |
| Supplier OTIF | supplier x month matrix; escalation queue by Units Late At Promise | to PO-line detail |
| Returns | median and P90 turnaround by disposition; open returns by stage and age; recoverable value by family | |
| PPV | price and FX effect by month and supplier; PPV % | |

## Acceptance checks

- Executive OTIF % equals the Customer OTIF page under every filter, and equals `rpt_exec_scorecard` for a month.
- The Order detail row count equals `Failed Lines` for the same filter.
- `PPV Bridge Check` is 0 under any filter.
