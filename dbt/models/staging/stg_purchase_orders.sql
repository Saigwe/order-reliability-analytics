select po_line_id, supplier_id, site_id, item, order_date::date as order_date, promised_date::date as promised_date,
       ordered_qty, standard_unit_cost_usd::double as standard_unit_cost_usd
from {{ source('raw', 'purchase_orders') }}
