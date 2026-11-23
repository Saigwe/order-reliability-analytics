-- Grain: one customer order. An order is OTIF only when every eligible line on it is OTIF.
select order_id, any_value(customer_id) as customer_id, any_value(region) as region, any_value(site_id) as site_id,
       max(promise_month) as promise_month, count(*) as eligible_lines,
       bool_and(is_otif_original) as is_otif_original, bool_and(is_otif_latest) as is_otif_latest
from {{ ref('fct_order_line') }}
where is_eligible
group by order_id
