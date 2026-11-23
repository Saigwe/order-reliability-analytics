select receipt_month, supplier_id, currency,
       sum(case when not is_credit_note then qty_each else 0 end) as qty_each,
       sum(case when not is_credit_note then standard_spend_usd else 0 end) as standard_spend_usd,
       sum(case when not is_credit_note then actual_spend_usd else 0 end) as actual_spend_usd,
       sum(ppv_usd) as ppv_usd, sum(price_effect_usd) as price_effect_usd, sum(fx_effect_usd) as fx_effect_usd,
       sum(case when is_credit_note then actual_spend_usd else 0 end) as credit_notes_usd,
       sum(case when is_late_invoice then 1 else 0 end) as late_invoices
from {{ ref('fct_ppv') }}
group by all
