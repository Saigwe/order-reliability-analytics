-- Delivered quantity on lines equals proof-of-delivery quantity in the deduplicated event log (known lines only).
select abs((select sum(delivered_qty) from {{ ref('fct_order_line') }})
         - (select sum(quantity) from {{ ref('stg_order_events') }}
            where event_type = 'shipment_delivered' and has_order_line
              and order_line_id in (select order_line_id from {{ ref('stg_order_lines') }} where is_valid))) as diff
having diff > 0
