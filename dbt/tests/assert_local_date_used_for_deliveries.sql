-- Deliveries are dated in the site's local calendar: no delivery date may equal the UTC date when the two differ.
select d.event_id from {{ ref('int_deliveries') }} d
join {{ ref('stg_order_lines') }} l using (order_line_id)
join {{ ref('stg_sites') }} s using (site_id)
where d.delivered_date <> cast(d.event_ts_utc + to_hours(s.utc_offset_hours) as date)
