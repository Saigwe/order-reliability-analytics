-- What the pipeline found and handled before any KPI. One row per check.
select 'Order events: duplicate retries dropped' as check_name, 'order_events' as source,
       (select sum(duplicate_copies_dropped) from {{ ref('stg_order_events') }}) as records, 'dropped' as action
union all select 'Order events: arrived more than 2 days late', 'order_events',
       (select count(*) from {{ ref('stg_order_events') }} where arrived_late), 'reprocessed by incremental lookback'
union all select 'Deliveries for unknown order lines', 'order_events',
       (select count(*) from {{ ref('stg_order_events') }} where not has_order_line), 'quarantined'
union all select 'Order lines with zero quantity', 'order_lines',
       (select count(*) from {{ ref('stg_order_lines') }} where not is_valid), 'quarantined'
union all select 'Warehouse double scans', 'warehouse_scans',
       (select sum(duplicate_scans) from {{ ref('stg_warehouse_scans') }}), 'dropped'
union all select 'Duplicate RMA events', 'return_events',
       (select sum(duplicates_dropped) from {{ ref('stg_return_events') }}), 'dropped'
union all select 'Returns inspected with no disposition', 'return_events',
       (select count(*) from {{ ref('fct_return') }} where stage = 'Inspected, no disposition'), 'flagged for follow-up'
union all select 'Supplier credit notes', 'invoices',
       (select count(*) from {{ ref('stg_invoices') }} where is_credit_note), 'excluded from PPV'
union all select 'Invoices after the receipt month closed', 'invoices',
       (select count(*) from {{ ref('fct_ppv') }} where is_late_invoice), 'PPV booked to receipt month'
