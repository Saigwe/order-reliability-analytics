-- One row per order line as the order system sent it. Zero-quantity lines are kept here and quarantined downstream.
select l.order_line_id, l.order_id, l.customer_id, l.sku, l.site_id, l.ordered_qty,
       l.ordered_at_utc::timestamp as ordered_at_utc,
       {{ local_date('l.ordered_at_utc', 's.utc_offset_hours') }} as order_date,
       l.original_promise_date::date as original_promise_date,
       l.ordered_qty > 0 as is_valid
from {{ source('raw', 'order_lines') }} l
join {{ ref('stg_sites') }} s using (site_id)
