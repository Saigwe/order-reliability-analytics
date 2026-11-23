-- Grain: one invoice line, priced per each in USD.
-- PPV = (actual unit price in USD - standard unit cost) x quantity; positive is unfavourable (demo convention).
-- Split into a price effect (at the standard FX rate) and an FX effect (actual rate minus standard). They sum to PPV.
-- Credit notes are quantity corrections, not price: excluded from PPV and counted separately.
with i as (
    select i.*, p.supplier_id, p.site_id, p.item, p.standard_unit_cost_usd, r.received_date,
           date_trunc('month', r.received_date)::date as receipt_month,
           i.invoice_qty * i.units_per_uom as qty_each,
           i.unit_price_local / i.units_per_uom as price_local_each,
           fx.usd_per_unit as fx_actual, s.std_usd_per_unit as fx_standard
    from {{ ref('stg_invoices') }} i
    join {{ ref('stg_purchase_orders') }} p using (po_line_id)
    join {{ ref('stg_receipts') }} r using (receipt_id)
    join {{ ref('stg_fx_rates') }} fx on fx.currency = i.currency and fx.rate_date = i.invoice_date
    join {{ ref('stg_standard_fx') }} s on s.currency = i.currency
)
select invoice_line_id, po_line_id, receipt_id, supplier_id, site_id, item, currency, uom, invoice_date, received_date, receipt_month,
       is_credit_note, invoice_date > last_day(received_date) as is_late_invoice,
       qty_each, price_local_each, fx_actual, fx_standard, standard_unit_cost_usd,
       price_local_each * fx_actual as actual_unit_usd,
       qty_each * standard_unit_cost_usd as standard_spend_usd,
       qty_each * price_local_each * fx_actual as actual_spend_usd,
       case when is_credit_note then 0 else qty_each * (price_local_each * fx_actual - standard_unit_cost_usd) end as ppv_usd,
       case when is_credit_note then 0 else qty_each * (price_local_each * fx_standard - standard_unit_cost_usd) end as price_effect_usd,
       case when is_credit_note then 0 else qty_each * price_local_each * (fx_actual - fx_standard) end as fx_effect_usd
from i
