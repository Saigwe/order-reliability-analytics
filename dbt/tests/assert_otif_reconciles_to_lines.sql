-- The monthly report must hold exactly the eligible lines and quantity in the line fact.
select 'lines' as what, (select sum(eligible_lines) from {{ ref('rpt_customer_otif_monthly') }}) as report,
       (select count(*) from {{ ref('fct_order_line') }} where is_eligible) as fact
union all
select 'qty', (select sum(eligible_qty) from {{ ref('rpt_customer_otif_monthly') }}),
       (select sum(eligible_qty) from {{ ref('fct_order_line') }} where is_eligible)
except
select what, fact, fact from (select 'lines' as what, (select count(*) from {{ ref('fct_order_line') }} where is_eligible) as fact
                              union all select 'qty', (select sum(eligible_qty) from {{ ref('fct_order_line') }} where is_eligible))
