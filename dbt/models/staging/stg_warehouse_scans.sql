-- Scanners fire twice now and then; the first scan of each type per shipment is the real one.
select shipment_id, scan_type, min(scanned_at_utc::timestamp) as scanned_at_utc, count(*) - 1 as duplicate_scans
from {{ source('raw', 'warehouse_scans') }}
group by shipment_id, scan_type
