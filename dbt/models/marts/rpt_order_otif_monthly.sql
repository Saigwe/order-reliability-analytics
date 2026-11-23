select promise_month, region, site_id, count(*) as orders,
       sum(case when is_otif_original then 1 else 0 end) as otif_orders_original,
       sum(case when is_otif_latest then 1 else 0 end) as otif_orders_latest
from {{ ref('fct_order') }}
group by all
