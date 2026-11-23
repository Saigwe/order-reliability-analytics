-- Invoice lines in the supplier's currency and unit of measure. C100 = price and quantity per hundred units.
select invoice_line_id, po_line_id, receipt_id, invoice_date::date as invoice_date, currency, uom,
       invoice_qty::double as invoice_qty, unit_price_local::double as unit_price_local,
       case uom when 'C100' then 100 else 1 end as units_per_uom,
       invoice_qty < 0 as is_credit_note
from {{ source('raw', 'invoices') }}
