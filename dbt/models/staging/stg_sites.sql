select site_id, site_name, site_region, utc_offset_hours from {{ source('raw', 'sites') }}
