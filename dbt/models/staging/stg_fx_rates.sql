select rate_date::date as rate_date, currency, usd_per_unit::double as usd_per_unit from {{ source('raw', 'fx_rates') }}
