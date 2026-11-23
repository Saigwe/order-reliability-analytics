select p.promise_month, p.supplier_id, s.supplier_name, p.site_id,
       count(*) as po_lines,
       sum(case when is_on_time then 1 else 0 end) as on_time_lines,
       sum(case when is_in_full then 1 else 0 end) as in_full_lines,
       sum(case when is_otif then 1 else 0 end) as otif_lines,
       sum(ordered_qty) as ordered_qty,
       sum(greatest(ordered_qty - received_by_promise, 0)) as qty_late_at_promise,
       avg(case when not is_otif then days_late end) as avg_days_late_failed
from {{ ref('fct_po_line') }} p
join {{ ref('stg_suppliers') }} s using (supplier_id)
where p.is_eligible
group by all
