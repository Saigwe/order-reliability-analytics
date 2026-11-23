-- Price effect + FX effect = PPV on every invoice line.
select invoice_line_id from {{ ref('fct_ppv') }} where abs(price_effect_usd + fx_effect_usd - ppv_usd) > 0.01
