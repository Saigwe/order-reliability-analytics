select month from {{ ref('rpt_exec_scorecard') }}
where customer_otif not between 0 and 1 or supplier_otif not between 0 and 1 or order_otif not between 0 and 1
   or order_otif > customer_otif + 0.0001
