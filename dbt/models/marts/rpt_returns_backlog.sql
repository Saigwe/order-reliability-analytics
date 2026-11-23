-- Open returns at the extract date, by stage and age band.
select stage, site_id, family,
       case when open_age_days < 7 then '0-6 days' when open_age_days < 14 then '7-13 days'
            when open_age_days < 30 then '14-29 days' else '30+ days' end as age_band,
       count(*) as open_returns, sum(quantity) as units, sum(open_recoverable_usd) as open_recoverable_usd
from {{ ref('fct_return') }}
where stage in ('Awaiting inspection', 'Inspected, no disposition')
group by all
