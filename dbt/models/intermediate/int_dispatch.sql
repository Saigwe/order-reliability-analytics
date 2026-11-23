-- One row per shipment: warehouse scan times (deduplicated) and dispatch date at the site.
select sh.shipment_id, sh.order_line_id, sh.site_id, sh.carrier, c.standard_transit_days,
       max(case when sc.scan_type = 'picked' then sc.scanned_at_utc end) as picked_at_utc,
       max(case when sc.scan_type = 'packed' then sc.scanned_at_utc end) as packed_at_utc,
       max(case when sc.scan_type = 'dispatched' then sc.scanned_at_utc end) as dispatched_at_utc,
       {{ local_date("max(case when sc.scan_type = 'dispatched' then sc.scanned_at_utc end)", 'any_value(s.utc_offset_hours)') }} as dispatch_date,
       sum(sc.duplicate_scans) as duplicate_scans
from {{ ref('stg_shipments') }} sh
join {{ ref('stg_carriers') }} c using (carrier, site_id)
join {{ ref('stg_sites') }} s using (site_id)
left join {{ ref('stg_warehouse_scans') }} sc using (shipment_id)
group by sh.shipment_id, sh.order_line_id, sh.site_id, sh.carrier, c.standard_transit_days
