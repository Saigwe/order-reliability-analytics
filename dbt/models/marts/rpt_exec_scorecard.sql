-- Executive scorecard: one row per month.
with c as (select promise_month as month, sum(eligible_lines) as eligible_lines, sum(otif_lines_original) as otif_o,
                  sum(otif_lines_latest) as otif_l, sum(on_time_lines) as on_time, sum(in_full_lines) as in_full
           from {{ ref('rpt_customer_otif_monthly') }} group by 1),
o as (select promise_month as month, sum(orders) as orders, sum(otif_orders_original) as otif_orders from {{ ref('rpt_order_otif_monthly') }} group by 1),
s as (select promise_month as month, sum(po_lines) as po_lines, sum(otif_lines) as sup_otif from {{ ref('rpt_supplier_otif_monthly') }} group by 1),
p as (select receipt_month as month, sum(ppv_usd) as ppv_usd, sum(standard_spend_usd) as std_spend from {{ ref('rpt_ppv_monthly') }} group by 1),
r as (select received_month as month, median(turnaround_days) as median_tat, quantile_cont(turnaround_days, 0.9) as p90_tat,
             sum(recovery_value_usd) as recovery_usd, count(*) as returns
      from {{ ref('fct_return') }} where received_at is not null group by 1)
select c.month, c.eligible_lines,
       c.otif_o::double / c.eligible_lines as customer_otif, c.otif_l::double / c.eligible_lines as customer_otif_latest_promise,
       c.on_time::double / c.eligible_lines as on_time_rate, c.in_full::double / c.eligible_lines as in_full_rate,
       o.otif_orders::double / o.orders as order_otif,
       s.sup_otif::double / s.po_lines as supplier_otif,
       p.ppv_usd, p.ppv_usd / nullif(p.std_spend, 0) as ppv_pct,
       r.returns, r.median_tat as median_return_turnaround_days, r.p90_tat as p90_return_turnaround_days, r.recovery_usd
from c left join o using (month) left join s using (month) left join p using (month) left join r using (month)
where c.month >= date '2025-11-01'
  and c.month < (select date_trunc('month', max(ingested_at)) from {{ ref('stg_order_events') }})  -- complete months only
