-- Grain: one return (RMA), its lifecycle flattened from the event history.
with e as (select * from {{ ref('stg_return_events') }}),
ref_as_of as (select max(event_ts_utc) as as_of from e),
r as (
    select rma_id, any_value(order_line_id) as order_line_id, any_value(sku) as sku, any_value(site_id) as site_id,
           max(quantity) as quantity,
           min(event_ts_utc) filter (where event_type = 'authorised') as authorised_at,
           min(event_ts_utc) filter (where event_type = 'received') as received_at,
           min(event_ts_utc) filter (where event_type = 'inspected') as inspected_at,
           min(event_ts_utc) filter (where event_type like 'disposition_%') as disposition_at,
           any_value(event_type) filter (where event_type like 'disposition_%') as disposition_event,
           sum(refund_usd) as refund_usd,
           sum(duplicates_dropped) as duplicates_dropped
    from e group by rma_id
)
select r.*, k.family, k.standard_cost_usd, k.unit_value_usd,
       date_trunc('month', r.received_at)::date as received_month,
       case r.disposition_event when 'disposition_restock' then 'Restock' when 'disposition_refurbish' then 'Refurbish'
            when 'disposition_recycle' then 'Recycle' when 'disposition_return_to_vendor' then 'Return to vendor' end as disposition,
       case when r.received_at is null then 'Awaiting receipt'
            when r.inspected_at is null then 'Awaiting inspection'
            when r.disposition_at is null then 'Inspected, no disposition'
            else 'Closed' end as stage,
       date_diff('hour', r.received_at, r.disposition_at) / 24.0 as turnaround_days,
       case when r.disposition_at is null and r.received_at is not null
            then date_diff('hour', r.received_at, ref_as_of.as_of) / 24.0 end as open_age_days,
       r.quantity * k.standard_cost_usd * case r.disposition_event
            when 'disposition_restock' then {{ var('recovery_restock') }} when 'disposition_refurbish' then {{ var('recovery_refurbish') }}
            when 'disposition_return_to_vendor' then {{ var('recovery_return_to_vendor') }} when 'disposition_recycle' then {{ var('recovery_recycle') }}
            else 0 end as recovery_value_usd,
       -- expected value still recoverable from an open return, at the restock/refurbish average
       case when r.disposition_at is null and r.received_at is not null
            then r.quantity * k.standard_cost_usd * ({{ var('recovery_restock') }} + {{ var('recovery_refurbish') }}) / 2 else 0 end as open_recoverable_usd,
       (case when r.received_at is not null then {{ var('cost_receive') }} else 0 end
        + case when r.inspected_at is not null then {{ var('cost_inspect') }} else 0 end
        + case r.disposition_event when 'disposition_refurbish' then {{ var('cost_refurbish') }}
               when 'disposition_recycle' then {{ var('cost_recycle') }} else 0 end) as handling_cost_usd
from r cross join ref_as_of
join {{ ref('stg_skus') }} k using (sku)
