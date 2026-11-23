-- Records kept out of every KPI, with a reason code.
select 'zero_quantity' as reason, order_line_id as record_id, 'order_lines' as source
from {{ ref('stg_order_lines') }} where not is_valid
union all
select 'unknown_order_line', event_id, 'order_events' from {{ ref('stg_order_events') }} where not has_order_line
