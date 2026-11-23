-- Deduplicated event log: a retried event (same event_id) is kept once, at its first arrival.
-- Event dates are converted to the site's local calendar: a delivery at 23:30 in Memphis is that day, not the next UTC day.
with ranked as (
    select *, row_number() over (partition by event_id order by ingested_at) as arrival_rank,
           count(*) over (partition by event_id) as copies
    from {{ source('raw', 'order_events') }}
    where ingested_at <= timestamp '{{ var("ingest_cutoff", "2099-12-31") }}'   -- set by `make rerun` to prove backfills
)
select r.event_id, r.event_type, r.order_line_id, r.event_ts_utc::timestamp as event_ts_utc,
       r.ingested_at::timestamp as ingested_at, r.quantity, r.promise_date::date as promise_date, r.shipment_id,
       {{ local_date('r.event_ts_utc', 's.utc_offset_hours') }} as event_local_date,
       l.order_line_id is not null as has_order_line,
       r.ingested_at::timestamp - r.event_ts_utc::timestamp > interval 2 day as arrived_late,
       r.copies - 1 as duplicate_copies_dropped
from ranked r
left join {{ ref('stg_order_lines') }} l using (order_line_id)
left join {{ ref('stg_sites') }} s on s.site_id = l.site_id
where r.arrival_rank = 1
