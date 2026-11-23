-- Failed eligible lines (original promise) by month, region, site, SKU and reason: the Pareto and drill-down source.
select f.promise_month, f.region, f.site_id, f.sku, k.sku_name, k.family, k.abc_band, f.failure_reason,
       count(*) as failed_lines, sum(f.eligible_qty - f.delivered_by_original) as qty_short_at_promise
from {{ ref('fct_order_line') }} f
join {{ ref('dim_sku') }} k using (sku)
where f.is_eligible and not f.is_otif_original
group by all
