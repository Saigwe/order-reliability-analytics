-- Returns events. A duplicate RMA creation (same RMA, same event type) is kept once.
select rma_id, order_line_id, sku, site_id, event_type, min(event_ts_utc::timestamp) as event_ts_utc,
       any_value(quantity) as quantity, max(refund_usd) as refund_usd, count(*) - 1 as duplicates_dropped
from {{ source('raw', 'return_events') }}
group by rma_id, order_line_id, sku, site_id, event_type
