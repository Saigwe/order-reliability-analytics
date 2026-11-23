select currency, usd_per_unit::double as std_usd_per_unit from {{ source('raw', 'standard_fx') }}
