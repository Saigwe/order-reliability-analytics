select customer_id, customer_name, region, site_id, channel from {{ source('raw', 'customers') }}
