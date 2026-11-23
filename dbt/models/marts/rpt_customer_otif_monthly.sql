-- Line-level OTIF by promise month, region, site, carrier and family. Every rate shares one denominator: eligible lines.
select promise_month, region, site_id, carrier, family,
       count(*) as eligible_lines,
       sum(eligible_qty) as eligible_qty,
       sum(case when is_on_time then 1 else 0 end) as on_time_lines,
       sum(case when is_in_full then 1 else 0 end) as in_full_lines,
       sum(case when is_otif_original then 1 else 0 end) as otif_lines_original,
       sum(case when is_otif_latest then 1 else 0 end) as otif_lines_latest,
       sum(case when promise_changes > 0 then 1 else 0 end) as repromised_lines
from {{ ref('fct_order_line') }}
where is_eligible
group by all
