{{ config(materialized='incremental', unique_key='event_id', on_schema_change='append_new_columns') }}
-- Proof-of-delivery events, built incrementally. Each run reprocesses everything ingested in the last few days, so a
-- late-arriving or retried event lands in the right place and a rerun leaves totals unchanged.
select event_id, order_line_id, shipment_id, quantity as delivered_qty, event_ts_utc, event_local_date as delivered_date,
       ingested_at
from {{ ref('stg_order_events') }}
where event_type = 'shipment_delivered' and has_order_line
{% if is_incremental() %}
  and ingested_at > (select max(ingested_at) - interval {{ var('incremental_lookback_days') }} day from {{ this }})
{% endif %}
