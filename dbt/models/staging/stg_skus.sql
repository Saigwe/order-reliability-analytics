select s.sku, s.sku_name, s.family, s.unit_value_usd::double as unit_value_usd, s.standard_cost_usd::double as standard_cost_usd,
       src.supplier_id as main_supplier_id
from {{ source('raw', 'skus') }} s
left join {{ source('raw', 'sku_sources') }} src using (sku)
