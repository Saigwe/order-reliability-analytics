select q.record_id from {{ ref('rpt_quarantine') }} q
join {{ ref('fct_order_line') }} f on f.order_line_id = q.record_id
