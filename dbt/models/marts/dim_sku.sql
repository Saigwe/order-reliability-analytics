-- SKUs with an ABC band on 12 months of ordered value (configurable cut-offs).
with v as (
    select l.sku, sum(l.ordered_qty * k.unit_value_usd) as order_value_usd
    from {{ ref('stg_order_lines') }} l join {{ ref('stg_skus') }} k using (sku)
    where l.is_valid
    group by l.sku
),
r as (
    select k.*, coalesce(v.order_value_usd, 0) as order_value_usd,
           coalesce(v.order_value_usd, 0) / sum(coalesce(v.order_value_usd, 0)) over () as value_share,
           sum(coalesce(v.order_value_usd, 0)) over (order by coalesce(v.order_value_usd, 0) desc, k.sku rows unbounded preceding)
             / sum(coalesce(v.order_value_usd, 0)) over () as cumulative_share
    from {{ ref('stg_skus') }} k left join v using (sku)
)
select *, case when cumulative_share - value_share < {{ var('abc_a_share') }} then 'A'
               when cumulative_share - value_share < {{ var('abc_b_share') }} then 'B' else 'C' end as abc_band
from r
