select received_month, site_id, family, disposition,
       count(*) as returns, sum(quantity) as units,
       median(turnaround_days) as median_turnaround_days,
       quantile_cont(turnaround_days, 0.9) as p90_turnaround_days,
       sum(refund_usd) as refund_usd, sum(recovery_value_usd) as recovery_value_usd, sum(handling_cost_usd) as handling_cost_usd
from {{ ref('fct_return') }}
where received_at is not null
group by all
