-- Grain: one supplier purchase-order line. Eligible once its promised date has passed.
with r as (
    select p.po_line_id, sum(r.received_qty) as received_qty,
           sum(case when r.received_date <= p.promised_date then r.received_qty else 0 end) as received_by_promise,
           min(r.received_date) as first_receipt_date, max(r.received_date) as last_receipt_date, count(*) as receipts
    from {{ ref('stg_purchase_orders') }} p join {{ ref('stg_receipts') }} r using (po_line_id)
    group by p.po_line_id
),
ref_as_of as (select max(received_date) as as_of_date from {{ ref('stg_receipts') }})
select p.*, date_trunc('month', p.promised_date)::date as promise_month,
       coalesce(r.received_qty, 0) as received_qty, coalesce(r.received_by_promise, 0) as received_by_promise,
       r.first_receipt_date, r.last_receipt_date, coalesce(r.receipts, 0) as receipts,
       coalesce(r.first_receipt_date <= p.promised_date, false) as is_on_time,
       coalesce(r.received_qty, 0) >= p.ordered_qty as is_in_full,
       coalesce(r.received_by_promise, 0) >= p.ordered_qty as is_otif,
       greatest(coalesce(r.last_receipt_date, ref_as_of.as_of_date) - p.promised_date, 0) as days_late,
       p.promised_date <= ref_as_of.as_of_date as is_eligible
from {{ ref('stg_purchase_orders') }} p cross join ref_as_of left join r using (po_line_id)
