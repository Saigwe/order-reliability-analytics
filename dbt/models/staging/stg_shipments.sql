select shipment_id, order_line_id, site_id, carrier from {{ source('raw', 'shipments') }}
