-- Grain: one customer order line. Eligible = positive quantity left after cancellations and a promise date on or before
-- the extract date. Quantities delivered are cumulative across split shipments.
--   on time  : the first delivery arrived on or before the promise date
--   in full  : everything eligible has been delivered (by the extract date)
--   OTIF     : the cumulative quantity delivered on or before the promise date covers the eligible quantity
-- Both promise policies are computed: against the original promise, and against the latest (re-promised) date.
with ref_as_of as (select max(ingested_at)::date as as_of_date from {{ ref('stg_order_events') }}),
ev as (select * from {{ ref('stg_order_events') }} where has_order_line),
cancel as (select order_line_id, sum(quantity) as cancelled_qty from ev where event_type = 'line_cancelled' group by 1),
promise as (select order_line_id, arg_max(promise_date, event_ts_utc) as latest_promise_date, count(*) as promise_changes
            from ev where event_type = 'promise_changed' group by 1),
lines as (
    select l.*, coalesce(c.cancelled_qty, 0) as cancelled_qty,
           greatest(l.ordered_qty - coalesce(c.cancelled_qty, 0), 0) as eligible_qty,
           coalesce(p.latest_promise_date, l.original_promise_date) as latest_promise_date,
           coalesce(p.promise_changes, 0) as promise_changes
    from {{ ref('stg_order_lines') }} l
    left join cancel c using (order_line_id)
    left join promise p using (order_line_id)
    where l.is_valid
),
d as (
    select l.order_line_id,
           sum(d.delivered_qty) as delivered_qty,
           sum(case when d.delivered_date <= l.original_promise_date then d.delivered_qty else 0 end) as delivered_by_original,
           sum(case when d.delivered_date <= l.latest_promise_date then d.delivered_qty else 0 end) as delivered_by_latest,
           min(d.delivered_date) as first_delivery_date, max(d.delivered_date) as last_delivery_date,
           count(distinct d.shipment_id) as shipments
    from lines l join {{ ref('int_deliveries') }} d using (order_line_id)
    group by l.order_line_id
),
disp as (
    select order_line_id, min(dispatch_date) as first_dispatch_date, any_value(carrier) as carrier,
           any_value(standard_transit_days) as standard_transit_days
    from {{ ref('int_dispatch') }} group by order_line_id
),
f as (
    select l.order_line_id, l.order_id, l.customer_id, cu.region, l.sku, k.family, l.site_id, disp.carrier,
           l.order_date, l.original_promise_date, l.latest_promise_date, l.promise_changes,
           date_trunc('month', l.original_promise_date)::date as promise_month,
           l.ordered_qty, l.cancelled_qty, l.eligible_qty,
           l.eligible_qty * k.unit_value_usd as eligible_value_usd,
           coalesce(d.delivered_qty, 0) as delivered_qty,
           coalesce(d.delivered_by_original, 0) as delivered_by_original,
           coalesce(d.delivered_by_latest, 0) as delivered_by_latest,
           d.first_delivery_date, d.last_delivery_date, coalesce(d.shipments, 0) as shipments,
           disp.first_dispatch_date, disp.standard_transit_days,
           d.first_delivery_date - disp.first_dispatch_date as first_transit_days,
           l.eligible_qty > 0 and l.original_promise_date <= ref_as_of.as_of_date as is_eligible
    from lines l
    cross join ref_as_of
    join {{ ref('stg_customers') }} cu using (customer_id)
    join {{ ref('stg_skus') }} k using (sku)
    left join d using (order_line_id)
    left join disp using (order_line_id)
)
select *,
       coalesce(first_delivery_date <= original_promise_date, false) as is_on_time,
       delivered_qty >= eligible_qty as is_in_full,
       delivered_by_original >= eligible_qty as is_otif_original,
       coalesce(first_delivery_date <= latest_promise_date, false) as is_on_time_latest,
       delivered_by_latest >= eligible_qty as is_otif_latest,
       {% if var('otif_promise_policy') == 'latest' %} delivered_by_latest {% else %} delivered_by_original {% endif %} >= eligible_qty as is_otif,
       case when delivered_by_original >= eligible_qty then null
            when shipments > 1 or (delivered_qty > 0 and delivered_qty < eligible_qty) then 'Short shipment (stock)'
            when first_dispatch_date > original_promise_date - cast(standard_transit_days as integer) then 'Late dispatch (warehouse)'
            when first_transit_days > standard_transit_days + {{ var('carrier_grace_days') }} then 'Carrier transit delay'
            when delivered_qty = 0 then 'Not delivered yet'
            else 'Other late delivery' end as failure_reason
from f
